# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""Provenance-DAG traversal + verification — the open frontier no leader fills.

SLSA/in-toto define ``resolvedDependencies`` but ship NO tool that recursively
walks an ML provenance DAG and verifies every edge. szl_provctl does exactly
that, over linked ``UnifiedReceiptChain`` exports:

  * A node = one chain (a governed run / kernel / gate), identified by its head.
  * An edge = a declared dependency: node B depends on node A, asserting A's head.
  * verify_dag() topologically resolves the DAG, verifies EACH chain's internal
    hash-chain (via the suite's own verify_json), and verifies EACH edge's
    asserted head matches the dependency's actual head. Returns the first break.

HONEST-BLOCKED: a node whose verdict is BLOCKED is NOT dropped — it is surfaced
as a ``blocked`` node in the result, with its edges intact. A blocked run is
auditable, never silently green.

Stdlib only. No fabricated numbers.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from ._chain import UnifiedReceiptChain


class ProvenanceNode:
    """A DAG node wrapping one UnifiedReceiptChain export.

    ``deps`` is a list of (dep_node_id, asserted_head) the node claims it was
    built on. ``verdict`` is ALLOWED/BLOCKED (honest-BLOCKED is preserved).
    """

    __slots__ = ("node_id", "chain_blob", "deps", "verdict", "meta")

    def __init__(
        self,
        node_id: str,
        chain_blob: str,
        *,
        deps: Optional[List[Tuple[str, str]]] = None,
        verdict: str = "ALLOWED",
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if verdict not in ("ALLOWED", "BLOCKED"):
            raise ValueError("verdict must be ALLOWED or BLOCKED")
        self.node_id = str(node_id)
        self.chain_blob = chain_blob
        self.deps = list(deps or [])
        self.verdict = verdict
        self.meta = dict(meta or {})

    def head(self) -> str:
        records = json.loads(self.chain_blob)
        return records[-1]["digest"] if records else ("0" * 64)


class ProvenanceDAG:
    """A directed acyclic graph of provenance nodes with edge-level verification."""

    def __init__(self) -> None:
        self._nodes: Dict[str, ProvenanceNode] = {}

    def add_node(self, node: ProvenanceNode) -> "ProvenanceDAG":
        if node.node_id in self._nodes:
            raise ValueError(f"duplicate node_id {node.node_id!r}")
        self._nodes[node.node_id] = node
        return self

    def add_run(
        self,
        node_id: str,
        chain: Any,
        *,
        deps: Optional[List[str]] = None,
        verdict: str = "ALLOWED",
        meta: Optional[Dict[str, Any]] = None,
    ) -> "ProvenanceDAG":
        """Add a run from a live chain. ``deps`` are node_ids; their CURRENT
        heads are recorded as the asserted edge values (so a later mutation of a
        dependency is detectable)."""
        edges: List[Tuple[str, str]] = []
        for d in deps or []:
            if d not in self._nodes:
                raise ValueError(f"dependency {d!r} not in DAG (add it first)")
            edges.append((d, self._nodes[d].head()))
        self.add_node(
            ProvenanceNode(
                node_id, chain.to_json(), deps=edges, verdict=verdict, meta=meta
            )
        )
        return self

    def _topo_order(self) -> List[str]:
        """Kahn's algorithm; raises on cycle (DAG invariant).

        A node ``depends_on`` each dep, i.e. there is an edge dep -> node, so a
        node's indegree is its number of declared dependencies.
        """
        from collections import deque

        indeg = {nid: 0 for nid in self._nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in self._nodes}
        for n in self._nodes.values():
            indeg[n.node_id] += len(n.deps)
            for dep, _h in n.deps:
                adj[dep].append(n.node_id)
        queue = [nid for nid, d in indeg.items() if d == 0]
        order: List[str] = []
        dq = deque(sorted(queue))
        local_indeg = dict(indeg)
        while dq:
            nid = dq.popleft()
            order.append(nid)
            for nxt in sorted(adj[nid]):
                local_indeg[nxt] -= 1
                if local_indeg[nxt] == 0:
                    dq.append(nxt)
        if len(order) != len(self._nodes):
            raise ValueError("provenance graph is not a DAG (cycle detected)")
        return order

    def verify_dag(self) -> Dict[str, Any]:
        """Recursively verify the whole DAG.

        Returns a structured result:
          {
            ok, node_count, edge_count, order,
            blocked_nodes: [...],          # honest-BLOCKED, surfaced not dropped
            first_break: {node_id, kind, detail} | None,
            node_results: {node_id: {chain_ok, depth, head, verdict}},
          }
        kind ∈ {"chain_integrity", "edge_mismatch", "missing_dependency"}.
        """
        try:
            order = self._topo_order()
        except ValueError as exc:
            return {
                "ok": False,
                "node_count": len(self._nodes),
                "edge_count": sum(len(n.deps) for n in self._nodes.values()),
                "order": [],
                "blocked_nodes": [],
                "first_break": {"node_id": None, "kind": "cycle", "detail": str(exc)},
                "node_results": {},
            }

        node_results: Dict[str, Any] = {}
        blocked_nodes: List[str] = []
        first_break: Optional[Dict[str, Any]] = None

        for nid in order:
            n = self._nodes[nid]
            head = n.head()
            chain_ok, depth, brk = UnifiedReceiptChain.verify_json(n.chain_blob)
            node_results[nid] = {
                "chain_ok": bool(chain_ok),
                "depth": int(depth),
                "head": head,
                "verdict": n.verdict,
            }
            if n.verdict == "BLOCKED":
                blocked_nodes.append(nid)  # surface, do not drop

            if first_break is None and not chain_ok:
                first_break = {
                    "node_id": nid,
                    "kind": "chain_integrity",
                    "detail": f"internal hash-chain broke at receipt #{brk}",
                }
            # verify each declared edge against the dependency's ACTUAL head
            for dep_id, asserted in n.deps:
                if dep_id not in self._nodes:
                    if first_break is None:
                        first_break = {
                            "node_id": nid,
                            "kind": "missing_dependency",
                            "detail": f"declared dependency {dep_id!r} not in DAG",
                        }
                    continue
                actual = self._nodes[dep_id].head()
                if asserted != actual and first_break is None:
                    first_break = {
                        "node_id": nid,
                        "kind": "edge_mismatch",
                        "detail": (
                            f"edge {dep_id}->{nid}: asserted head "
                            f"{asserted[:16]}… != actual {actual[:16]}…"
                        ),
                    }

        ok = first_break is None
        return {
            "ok": ok,
            "node_count": len(self._nodes),
            "edge_count": sum(len(n.deps) for n in self._nodes.values()),
            "order": order,
            "blocked_nodes": blocked_nodes,
            "first_break": first_break,
            "node_results": node_results,
        }

    def to_json(self) -> str:
        return json.dumps(
            {
                nid: {
                    "chain_blob": n.chain_blob,
                    "deps": n.deps,
                    "verdict": n.verdict,
                    "meta": n.meta,
                }
                for nid, n in self._nodes.items()
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(blob: str) -> "ProvenanceDAG":
        data = json.loads(blob)
        dag = ProvenanceDAG()
        for nid, n in data.items():
            dag.add_node(
                ProvenanceNode(
                    nid,
                    n["chain_blob"],
                    deps=[tuple(e) for e in n.get("deps", [])],
                    verdict=n.get("verdict", "ALLOWED"),
                    meta=n.get("meta", {}),
                )
            )
        return dag


__all__ = ["ProvenanceNode", "ProvenanceDAG"]
