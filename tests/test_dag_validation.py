# SPDX-License-Identifier: Apache-2.0
"""Regression checks for provenance DAG structure and edge verification."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "torch-ext"))

from szl_provctl import ProvenanceDAG, ProvenanceNode, UnifiedReceiptChain


def _chain(label: str) -> UnifiedReceiptChain:
    chain = UnifiedReceiptChain()
    chain.emit("test", label, {})
    return chain


class DAGValidation(unittest.TestCase):
    def test_constructor_node_with_missing_dependency_is_structured_break(self) -> None:
        chain = _chain("orphan")
        dag = ProvenanceDAG().add_node(
            ProvenanceNode("orphan", chain.to_json(), deps=[("missing", chain.head())])
        )

        result = dag.verify_dag()

        self.assertFalse(result["ok"])
        self.assertEqual(result["node_count"], 1)
        self.assertEqual(result["edge_count"], 1)
        self.assertEqual(result["order"], [])
        self.assertEqual(result["first_break"]["node_id"], "orphan")
        self.assertEqual(result["first_break"]["kind"], "missing_dependency")
        self.assertIn("missing", result["first_break"]["detail"])

    def test_from_json_with_missing_dependency_is_structured_break(self) -> None:
        chain = _chain("orphan")
        original = ProvenanceDAG().add_node(
            ProvenanceNode("orphan", chain.to_json(), deps=[("missing", chain.head())])
        )
        restored = ProvenanceDAG.from_json(original.to_json())

        result = restored.verify_dag()

        self.assertFalse(result["ok"])
        self.assertEqual(result["first_break"]["node_id"], "orphan")
        self.assertEqual(result["first_break"]["kind"], "missing_dependency")

    def test_cycle_is_still_reported_as_cycle(self) -> None:
        left, right = _chain("left"), _chain("right")
        dag = ProvenanceDAG()
        dag.add_node(
            ProvenanceNode("left", left.to_json(), deps=[("right", right.head())])
        )
        dag.add_node(
            ProvenanceNode("right", right.to_json(), deps=[("left", left.head())])
        )

        result = dag.verify_dag()

        self.assertFalse(result["ok"])
        self.assertEqual(result["first_break"]["kind"], "cycle")

    def test_valid_dag_keeps_topology_and_verified_edges(self) -> None:
        root, child = _chain("root"), _chain("child")
        dag = ProvenanceDAG().add_run("root", root)
        dag.add_run("child", child, deps=["root"], verdict="BLOCKED")

        result = dag.verify_dag()

        self.assertTrue(result["ok"])
        self.assertEqual(result["order"], ["root", "child"])
        self.assertEqual(result["edge_count"], 1)
        self.assertEqual(result["blocked_nodes"], ["child"])
        self.assertIsNone(result["first_break"])


if __name__ == "__main__":
    unittest.main()
