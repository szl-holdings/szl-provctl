# SPDX-License-Identifier: Apache-2.0
"""A provenance DAG with a missing node fails closed with a structured result.

A node may declare a dependency on a node_id that is not in the DAG (built with
ProvenanceNode + add_node, or loaded with from_json). verify_dag() must then
return ok=False with first_break.kind == "missing_dependency", naming every
missing id and the nodes that declared it. It must not raise, skip the edge, or
report the nodes it could reach as verified. Complete DAGs keep their order,
cycle diagnosis and receipt-chain checks.

Standard library only: runs under plain `pytest` and `python -S`.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

from szl_provctl import ProvenanceDAG, ProvenanceNode, UnifiedReceiptChain
from szl_provctl._dag import MissingDependencyError

CYCLE_DETAIL = "provenance graph is not a DAG (cycle detected)"


def _chain(step: str) -> UnifiedReceiptChain:
    chain = UnifiedReceiptChain()
    chain.emit("governed_norm", "rms_norm", {"step": step})
    return chain


def _node(node_id: str, deps=(), verdict: str = "ALLOWED") -> ProvenanceNode:
    asserted = [(d, "0" * 64) for d in deps]
    return ProvenanceNode(node_id, _chain(node_id).to_json(), deps=asserted, verdict=verdict)


def _pipeline() -> ProvenanceDAG:
    """train -> finetune -> eval (eval honest-BLOCKED), built through add_run."""
    dag = ProvenanceDAG()
    dag.add_run("train", _chain("train"))
    dag.add_run("finetune", _chain("finetune"), deps=["train"])
    dag.add_run("eval", _chain("eval"), deps=["finetune"], verdict="BLOCKED")
    return dag


def _without(dag: ProvenanceDAG, *node_ids: str) -> ProvenanceDAG:
    data = json.loads(dag.to_json())
    for nid in node_ids:
        del data[nid]
    return ProvenanceDAG.from_json(json.dumps(data))


def _assert_fails_closed(res, *, node_count: int, edge_count: int) -> dict:
    assert res["ok"] is False
    assert res["node_count"] == node_count
    assert res["edge_count"] == edge_count
    # nothing is reported as verified when the graph is incomplete
    assert res["order"] == []
    assert res["node_results"] == {}
    brk = res["first_break"]
    assert brk["kind"] == "missing_dependency"
    return brk


def test_missing_leaf_direct_constructor():
    dag = ProvenanceDAG()
    dag.add_node(_node("finetune", deps=["train"]))

    res = dag.verify_dag()  # used to raise KeyError('train')

    brk = _assert_fails_closed(res, node_count=1, edge_count=1)
    assert brk["node_id"] == "finetune"
    assert brk["missing"] == ["train"]
    assert brk["dependents"] == {"train": ["finetune"]}
    assert "'train'" in brk["detail"] and "'finetune'" in brk["detail"]
    assert res["blocked_nodes"] == []


def test_missing_leaf_from_json():
    res = _without(_pipeline(), "train").verify_dag()

    brk = _assert_fails_closed(res, node_count=2, edge_count=2)
    assert brk["node_id"] == "finetune"
    assert brk["missing"] == ["train"]
    assert brk["dependents"] == {"train": ["finetune"]}
    assert res["blocked_nodes"] == ["eval"]  # honest-BLOCKED still surfaced


def test_missing_middle_node():
    dag = _without(_pipeline(), "finetune")

    res = dag.verify_dag()

    # train is present and its chain is intact, but it is not reported as
    # verified: the DAG as a whole cannot be resolved.
    brk = _assert_fails_closed(res, node_count=2, edge_count=1)
    assert brk["node_id"] == "eval"
    assert brk["missing"] == ["finetune"]
    assert brk["dependents"] == {"finetune": ["eval"]}
    assert res["blocked_nodes"] == ["eval"]
    assert dag.missing_dependencies() == {"finetune": ["eval"]}


def test_multiple_missing_nodes():
    dag = ProvenanceDAG()
    dag.add_node(_node("root"))
    dag.add_node(_node("merge", deps=["root", "data-b", "data-a"]))
    dag.add_node(_node("report", deps=["merge", "data-b", "data-b"]))

    res = dag.verify_dag()

    brk = _assert_fails_closed(res, node_count=3, edge_count=6)
    assert brk["node_id"] == "merge"
    assert brk["missing"] == ["data-a", "data-b"]
    assert brk["dependents"] == {"data-a": ["merge"], "data-b": ["merge", "report"]}
    for name in ("'data-a'", "'data-b'", "'merge'", "'report'"):
        assert name in brk["detail"]


def test_topo_order_raises_typed_error_not_key_error():
    dag = ProvenanceDAG()
    dag.add_node(_node("b", deps=["a"]))
    try:
        dag._topo_order()
    except MissingDependencyError as exc:
        assert isinstance(exc, ValueError)
        assert exc.missing == {"a": ["b"]}
    else:  # pragma: no cover - the assertion is the failure message
        raise AssertionError("_topo_order accepted a missing dependency")


def test_cycle_diagnosis_unchanged():
    dag = ProvenanceDAG()
    dag.add_node(_node("a", deps=["b"]))
    dag.add_node(_node("b", deps=["a"]))
    dag.add_node(_node("c"))

    res = dag.verify_dag()

    assert res == {
        "ok": False,
        "node_count": 3,
        "edge_count": 2,
        "order": [],
        "blocked_nodes": [],
        "first_break": {"node_id": None, "kind": "cycle", "detail": CYCLE_DETAIL},
        "node_results": {},
    }


def test_missing_dependency_reported_before_cycle():
    dag = ProvenanceDAG()
    dag.add_node(_node("a", deps=["b"]))
    dag.add_node(_node("b", deps=["a"]))
    dag.add_node(_node("c", deps=["ghost"]))

    brk = _assert_fails_closed(dag.verify_dag(), node_count=3, edge_count=3)
    assert brk["missing"] == ["ghost"]
    assert brk["dependents"] == {"ghost": ["c"]}


def test_valid_dag_unchanged():
    dag = _pipeline()
    # diamond: report depends on two branches of the same root
    dag.add_run("branch", _chain("branch"), deps=["train"])
    dag.add_run("report", _chain("report"), deps=["eval", "branch"])

    for candidate in (dag, ProvenanceDAG.from_json(dag.to_json())):
        res = candidate.verify_dag()
        assert res["ok"] is True
        assert res["first_break"] is None
        assert res["node_count"] == 5
        assert res["edge_count"] == 5
        assert res["order"] == ["train", "branch", "finetune", "eval", "report"]
        assert res["blocked_nodes"] == ["eval"]
        assert sorted(res["node_results"]) == sorted(res["order"])
        for nid, nr in res["node_results"].items():
            node = candidate._nodes[nid]
            assert nr == {
                "chain_ok": True,
                "depth": 1,
                "head": node.head(),
                "verdict": node.verdict,
            }


def test_missing_dependencies_empty_for_complete_graphs():
    dag = _pipeline()
    assert dag.missing_dependencies() == {}
    assert ProvenanceDAG.from_json(dag.to_json()).missing_dependencies() == {}
    cyclic = ProvenanceDAG()
    cyclic.add_node(_node("a", deps=["b"]))
    cyclic.add_node(_node("b", deps=["a"]))
    assert cyclic.missing_dependencies() == {}  # a cycle is not a missing node


def test_receipt_chain_breaks_unchanged():
    # edge mismatch: a dependency's head no longer matches the asserted head
    data = json.loads(_pipeline().to_json())
    data["finetune"]["deps"] = [["train", "f" * 64]]
    res = ProvenanceDAG.from_json(json.dumps(data)).verify_dag()
    assert res["ok"] is False
    assert res["first_break"]["kind"] == "edge_mismatch"
    assert res["first_break"]["node_id"] == "finetune"
    assert res["order"] == ["train", "finetune", "eval"]

    # chain integrity: a receipt mutated without re-hashing
    data = json.loads(_pipeline().to_json())
    recs = json.loads(data["eval"]["chain_blob"])
    recs[0]["attrs"]["step"] = "tampered"
    data["eval"]["chain_blob"] = json.dumps(recs, sort_keys=True, separators=(",", ":"))
    res = ProvenanceDAG.from_json(json.dumps(data)).verify_dag()
    assert res["ok"] is False
    assert res["first_break"] == {
        "node_id": "eval",
        "kind": "chain_integrity",
        "detail": "internal hash-chain broke at receipt #0",
    }
    assert res["node_results"]["eval"]["chain_ok"] is False


def test_add_run_still_rejects_unknown_dependency():
    dag = ProvenanceDAG()
    try:
        dag.add_run("finetune", _chain("finetune"), deps=["train"])
    except ValueError as exc:
        assert "'train'" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("add_run accepted an unknown dependency")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    print(f"OK: {len(tests)} provenance-DAG missing-dependency tests")
