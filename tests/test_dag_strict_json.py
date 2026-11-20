# SPDX-License-Identifier: Apache-2.0
"""Ambiguous provenance exports must fail before digest or edge verification."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

from szl_provctl import ProvenanceDAG, ProvenanceNode, UnifiedReceiptChain


@pytest.mark.parametrize(
    "payload",
    [
        # A second node may replace the first before the DAG sees it.
        '{"run":{"chain_blob":"[]"},"run":{"chain_blob":"[]"}}',
        # Nested receipt metadata may overwrite an earlier conflicting claim.
        '{"run":{"chain_blob":"[]","meta":{"decision":"BLOCKED","decision":"ALLOWED"}}}',
        # Non-standard JSON constants have no portable canonical meaning.
        '{"run":{"chain_blob":"[]","meta":{"score":NaN}}}',
        '{"run":{"chain_blob":"[]","meta":{"score":Infinity}}}',
        '{"run":{"chain_blob":"[]","meta":{"score":-Infinity}}}',
    ],
)
def test_import_rejects_ambiguous_or_nonfinite_dag_json(payload):
    with pytest.raises(ValueError, match="duplicate JSON key|non-finite JSON constant"):
        ProvenanceDAG.from_json(payload)


def test_chain_duplicate_digest_cannot_be_silently_overwritten():
    chain = UnifiedReceiptChain()
    chain.emit("fixture", "record", {"item": "original"})
    canonical = chain.to_json()
    # The second digest remains legitimate; ordinary json.loads would have
    # discarded the contradictory first digest before checking the hash chain.
    conflicted = canonical.replace(
        '"digest":', '"digest":"' + ("0" * 64) + '","digest":', 1
    )
    assert conflicted != canonical

    good = ProvenanceDAG().add_node(ProvenanceNode("run", canonical))
    assert good.verify_dag()["ok"] is True

    bad = ProvenanceDAG().add_node(ProvenanceNode("run", conflicted))
    result = bad.verify_dag()
    assert result["ok"] is False
    assert result["first_break"]["node_id"] == "run"
    assert result["first_break"]["kind"] == "chain_integrity"
    assert result["node_results"]["run"]["head"] is None


def test_chain_nested_duplicate_in_attrs_is_rejected():
    chain = UnifiedReceiptChain()
    chain.emit("fixture", "record", {"state": "ALLOWED"})
    canonical = chain.to_json()
    conflicted = canonical.replace(
        '"state":"ALLOWED"', '"state":"BLOCKED","state":"ALLOWED"', 1
    )
    assert conflicted != canonical
    result = ProvenanceDAG().add_node(
        ProvenanceNode("run", conflicted)
    ).verify_dag()
    assert result["ok"] is False
    assert result["first_break"]["kind"] == "chain_integrity"


def test_canonical_roundtrip_still_verifies():
    chain = UnifiedReceiptChain()
    chain.emit("fixture", "record", {"state": "ALLOWED"})
    dag = ProvenanceDAG().add_node(ProvenanceNode("run", chain.to_json()))
    decoded = ProvenanceDAG.from_json(dag.to_json())
    result = decoded.verify_dag()
    assert result["ok"] is True
    assert result["first_break"] is None
