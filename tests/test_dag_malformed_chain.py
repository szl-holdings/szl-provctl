# SPDX-License-Identifier: Apache-2.0
"""Malformed chain exports must never become verified DAG nodes."""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

from szl_provctl import GENESIS, ProvenanceDAG, ProvenanceNode, UnifiedReceiptChain


@pytest.mark.parametrize(
    "blob",
    ["{}", '""', "null", "false", "0", "[{}]", "[null]", "[1]", "not-json"],
)
def test_malformed_dependency_returns_chain_failure(blob):
    chain = UnifiedReceiptChain()
    chain.emit("test", "run", {})
    dag = ProvenanceDAG()
    dag.add_node(ProvenanceNode("input", blob, verdict="BLOCKED"))
    dag.add_node(
        ProvenanceNode("consumer", chain.to_json(), deps=[("input", GENESIS)])
    )

    # Exercise the retained export path as well as direct construction.
    result = ProvenanceDAG.from_json(dag.to_json()).verify_dag()

    assert result["ok"] is False
    assert result["first_break"] == {
        "node_id": "input",
        "kind": "chain_integrity",
        "detail": "malformed receipt-chain export",
    }
    assert result["blocked_nodes"] == ["input"]
    assert result["node_results"]["input"]["chain_ok"] is False
    assert result["node_results"]["input"]["head"] is None
    assert result["node_results"]["consumer"]["chain_ok"] is True


def test_invalid_receipt_digest_is_not_used_as_dependency_head():
    chain = UnifiedReceiptChain()
    chain.emit("test", "run", {})
    records = json.loads(chain.to_json())
    records[-1]["digest"] = 123
    dag = ProvenanceDAG()
    dag.add_node(ProvenanceNode("input", json.dumps(records)))
    dag.add_node(ProvenanceNode("consumer", chain.to_json(), deps=[("input", GENESIS)]))

    result = dag.verify_dag()

    assert result["ok"] is False
    assert result["first_break"]["kind"] == "chain_integrity"
    assert result["node_results"]["input"]["head"] is None


def test_nonfinite_receipt_body_returns_chain_failure():
    chain = UnifiedReceiptChain()
    chain.emit("test", "run", {})
    records = json.loads(chain.to_json())
    records[0]["attrs"]["score"] = float("nan")
    dag = ProvenanceDAG().add_node(ProvenanceNode("input", json.dumps(records)))

    result = dag.verify_dag()

    assert result["ok"] is False
    assert result["first_break"]["kind"] == "chain_integrity"
    assert result["node_results"]["input"]["head"] is None


def test_valid_empty_array_remains_a_verified_genesis_chain():
    dag = ProvenanceDAG().add_node(ProvenanceNode("empty", "[]"))

    result = dag.verify_dag()

    assert result["ok"] is True
    assert result["first_break"] is None
    assert result["node_results"]["empty"] == {
        "chain_ok": True,
        "depth": 0,
        "head": GENESIS,
        "verdict": "ALLOWED",
    }


def test_excessively_nested_chain_returns_structured_failure():
    blob = "[" * 2000 + "0" + "]" * 2000
    dag = ProvenanceDAG().add_node(ProvenanceNode("input", blob))

    result = dag.verify_dag()

    assert result["ok"] is False
    assert result["first_break"]["kind"] == "chain_integrity"
    assert result["node_results"]["input"]["head"] is None
