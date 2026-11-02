# SPDX-License-Identifier: Apache-2.0
"""Malformed chains produce a failed DAG result, including dependency nodes."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

from szl_provctl import ProvenanceDAG, ProvenanceNode, UnifiedReceiptChain


def test_malformed_chain_fails_closed_and_preserves_blocked_nodes():
    for blob in ("{}", "null", "0", '""', "[{}]", "[null]", "{", "[" * 1100):
        dag = ProvenanceDAG().add_node(ProvenanceNode("bad", blob, verdict="BLOCKED"))
        result = dag.verify_dag()
        assert result["ok"] is False, blob
        assert result["blocked_nodes"] == ["bad"]
        assert result["first_break"]["node_id"] == "bad"
        assert result["first_break"]["kind"] == "chain_integrity"
        assert result["node_results"]["bad"]["chain_ok"] is False
        assert result["node_results"]["bad"]["head"] is None


def test_valid_child_of_malformed_chain_reports_parent_break():
    chain = UnifiedReceiptChain()
    chain.emit("fixture", "step", {})
    dag = ProvenanceDAG().add_node(ProvenanceNode("parent", "[{}]"))
    dag.add_node(ProvenanceNode("child", chain.to_json(),
                               deps=[("parent", "0" * 64)]))
    result = dag.verify_dag()
    assert result["ok"] is False
    assert result["first_break"]["node_id"] == "parent"
    assert result["node_results"]["child"]["chain_ok"] is True
    assert result["order"] == ["parent", "child"]


def test_empty_list_chain_keeps_existing_genesis_contract():
    result = ProvenanceDAG().add_node(ProvenanceNode("empty", "[]")).verify_dag()
    assert result["ok"] is True
    assert result["node_results"]["empty"]["head"] == "0" * 64


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
