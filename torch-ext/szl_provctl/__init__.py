# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""szl_provctl — the interop + provenance-DAG control layer of the governed-kernel series.

The lane the supply-chain leaders leave open. Sigstore/SLSA/in-toto define the
formats; CodeCarbon measures joules; nobody (verified, 2026) (a) emits a
governed run as a spec-exact in-toto v1 Statement + SLSA provenance, (b) walks
an ML provenance DAG and verifies every edge, or (c) measures energy PER KERNEL
bound to a signed-able provenance chain. szl_provctl does all three.

    from kernels import get_kernel
    pc = get_kernel("SZLHOLDINGS/szl-provctl", revision="main", trust_remote_code=True)

    chain = pc.UnifiedReceiptChain()
    chain.emit("governed_norm", "rms_norm", {"eps": 1e-6})

    # 1) Interop: a governed run as the EXACT payload the ecosystem verifies
    stmt = pc.statement_from_chain(chain, decision="ALLOWED")   # in-toto v1 Statement
    slsa = pc.slsa_statement(chain=chain, resolved_dependencies=[...],
                             invocation_id="run-1", started_on="...", finished_on="...")

    # 2) DAG: verify a multi-run ML provenance graph, edge by edge
    dag = pc.ProvenanceDAG()
    dag.add_run("train", chain_train)
    dag.add_run("finetune", chain_ft, deps=["train"])
    print(pc.verify_dag(dag)["ok"])

    # 3) Energy: real NVML delta around ONE kernel call (None when no GPU)
    r = pc.measure_kernel_energy(chain, my_kernel, kernel="governed_norm", op="rms_norm")

DOCTRINE (binding): proven_trust structurally locked False; Λ = Conjecture 1
(OPEN, advisory only); energy MEASURED-only (never fabricated); honest-BLOCKED
nodes are surfaced in the DAG, never silently dropped. Statement/SLSA field
names are spec-exact (in-toto v1, slsa.dev/provenance/v1).
"""
from typing import Any, Dict

from ._chain import GENESIS, UnifiedReceiptChain, tensor_digest, _CHAIN_SOURCE
from ._dag import ProvenanceDAG, ProvenanceNode
from ._energy import measure_kernel_energy
from ._interop import (
    BUILDER_ID,
    GOVERNANCE_PREDICATE_TYPE,
    GOVERNED_RUN_BUILD_TYPE,
    IN_TOTO_STATEMENT_TYPE,
    SCHEMA_VERSION,
    SLSA_PROVENANCE_TYPE,
    build_governance_predicate,
    build_in_toto_statement,
    build_slsa_provenance,
    canonical_json,
    resource_descriptor,
    slsa_statement,
    statement_from_chain,
)

__version__ = "0.1.0"

DOCTRINE_FOOTER = (
    "SZL Holdings · provenance-DAG + supply-chain interop · in-toto v1 / SLSA v1 · "
    "Λ = Conjecture 1 (advisory) · energy MEASURED-only · honest-BLOCKED surfaced"
)


def verify_dag(dag: "ProvenanceDAG") -> Dict[str, Any]:
    """Convenience: recursively verify a provenance DAG (see ProvenanceDAG.verify_dag)."""
    return dag.verify_dag()


def selfcheck() -> Dict[str, Any]:
    """One-shot, CPU-only, never-raises health check proving every claim.

    Returns {ok, version, checks:{...}, chain_source, error}.
    """
    checks: Dict[str, bool] = {}
    error = None
    try:
        # --- a governed run + spec-exact in-toto v1 Statement ---
        chain = UnifiedReceiptChain()
        chain.emit("governed_norm", "rms_norm", {"in_shape": [4, 64], "eps": 1e-6})
        chain.emit(
            "lambda_gate",
            "lambda_gate",
            {"score": 0.88, "advisory": True, "passed": True},
        )
        chain.emit_energy({"label": "UNAVAILABLE_NO_NVML", "joules": None, "source": "cpu selfcheck"})

        stmt = statement_from_chain(chain, lambda_score=0.88, decision="ALLOWED")
        checks["statement_type"] = stmt["_type"] == IN_TOTO_STATEMENT_TYPE
        checks["statement_subject_is_head"] = (
            stmt["subject"][0]["digest"]["sha3_256"] == chain.head()
        )
        checks["statement_predicate_type"] = (
            stmt["predicateType"] == GOVERNANCE_PREDICATE_TYPE
        )
        checks["proven_trust_locked_false"] = (
            stmt["predicate"]["lambda"]["proven_trust"] is False
        )
        checks["energy_measured_only"] = (
            stmt["predicate"]["energy"]["label"] == "UNAVAILABLE_NO_NVML"
            and stmt["predicate"]["energy"]["joules"] is None
        )

        # energy MEASURED-only is ENFORCED: a fabricated joule is rejected
        rejected = False
        try:
            build_governance_predicate(
                chain_head=chain.head(),
                kernels_touched=chain.kernels_touched(),
                chain_depth=chain.count(),
                energy={"label": "ESTIMATED", "joules": 12.3},
            )
        except ValueError:
            rejected = True
        checks["fabricated_energy_rejected"] = rejected

        # honest-BLOCKED cannot be flipped: blocked must be decision=BLOCKED
        flip_rejected = False
        try:
            build_governance_predicate(
                chain_head=chain.head(),
                kernels_touched=chain.kernels_touched(),
                chain_depth=chain.count(),
                decision="ALLOWED",
                honest_blocked=True,
            )
        except ValueError:
            flip_rejected = True
        checks["honest_blocked_not_flippable"] = flip_rejected

        # --- SLSA v1 provenance, spec-exact field names ---
        deps = [
            resource_descriptor(
                "SZLHOLDINGS/szl-governed-norm", tensor_digest("gn-build")
            ),
            resource_descriptor(
                "SZLHOLDINGS/szl-lambda-gate", tensor_digest("lg-build")
            ),
        ]
        slsa = slsa_statement(
            chain=chain,
            resolved_dependencies=deps,
            invocation_id="selfcheck-run-1",
            started_on="2026-06-24T00:00:00Z",
            finished_on="2026-06-24T00:00:01Z",
        )
        bd = slsa["predicate"]["buildDefinition"]
        rd = slsa["predicate"]["runDetails"]
        checks["slsa_predicate_type"] = slsa["predicateType"] == SLSA_PROVENANCE_TYPE
        checks["slsa_buildType"] = bd["buildType"] == GOVERNED_RUN_BUILD_TYPE
        checks["slsa_resolvedDependencies"] = len(bd["resolvedDependencies"]) == 2
        checks["slsa_builder_id"] = rd["builder"]["id"] == BUILDER_ID
        checks["slsa_metadata_fields"] = all(
            k in rd["metadata"] for k in ("invocationId", "startedOn", "finishedOn")
        )
        checks["slsa_byproducts_head"] = (
            rd["byproducts"][0]["digest"]["sha3_256"] == chain.head()
        )

        # --- provenance DAG: build, verify clean, then tamper an edge ---
        dag = ProvenanceDAG()
        c_train = UnifiedReceiptChain()
        c_train.emit("governed_norm", "rms_norm", {"step": "train"})
        dag.add_run("train", c_train)
        c_ft = UnifiedReceiptChain()
        c_ft.emit("governed_norm", "rms_norm", {"step": "finetune"})
        dag.add_run("finetune", c_ft, deps=["train"])
        c_blk = UnifiedReceiptChain()
        c_blk.emit("governed_gate", "decide", {"verdict": "BLOCK"})
        dag.add_run("eval", c_blk, deps=["finetune"], verdict="BLOCKED")

        res = dag.verify_dag()
        checks["dag_verifies_clean"] = res["ok"] is True
        checks["dag_three_nodes"] = res["node_count"] == 3
        checks["dag_topo_order"] = res["order"] == ["train", "finetune", "eval"]
        checks["dag_blocked_surfaced"] = res["blocked_nodes"] == ["eval"]

        # tamper a node's internal chain -> DAG must catch chain_integrity break
        blob = dag.to_json()
        import json as _json

        data = _json.loads(blob)
        recs = _json.loads(data["train"]["chain_blob"])
        recs[0]["attrs"]["step"] = "tampered"  # mutate without re-hashing
        data["train"]["chain_blob"] = _json.dumps(
            recs, sort_keys=True, separators=(",", ":")
        )
        tampered = ProvenanceDAG.from_json(_json.dumps(data))
        tres = tampered.verify_dag()
        checks["dag_tamper_detected"] = (
            tres["ok"] is False
            and tres["first_break"] is not None
            and tres["first_break"]["kind"] in ("chain_integrity", "edge_mismatch")
        )

        # round-trip: DAG serializes + reloads identically (clean)
        rt = ProvenanceDAG.from_json(dag.to_json()).verify_dag()
        checks["dag_roundtrip_ok"] = rt["ok"] is True

        # --- per-kernel energy: MEASURED-only, None on CPU, names the kernel ---
        er = measure_kernel_energy(
            chain, lambda x: x * 2, kernel="governed_norm", op="rms_norm", args=(21,)
        )
        checks["energy_kernel_ran"] = er["output"] == 42
        checks["energy_named_kernel"] = (
            er["receipt"]["attrs"]["measured_kernel"] == "governed_norm"
        )
        checks["energy_cpu_unavailable_not_fabricated"] = (
            er["receipt"]["attrs"]["label"] in ("UNAVAILABLE_NO_NVML", "UNAVAILABLE", "MEASURED")
            and (
                er["receipt"]["attrs"]["joules"] is None
                or isinstance(er["receipt"]["attrs"]["joules"], float)
            )
        )

        # the whole chain still verifies as one tamper-evident sequence
        ok, depth, brk = chain.verify()
        checks["chain_still_verifies"] = bool(ok and brk == -1)

    except Exception as exc:  # never raise from a health probe
        error = f"{type(exc).__name__}: {exc}"

    ok = bool(checks) and all(checks.values()) and error is None
    return {
        "ok": ok,
        "version": __version__,
        "checks": checks,
        "chain_source": _CHAIN_SOURCE,
        "error": error,
    }


__all__ = [
    "UnifiedReceiptChain",
    "tensor_digest",
    "GENESIS",
    "ProvenanceDAG",
    "ProvenanceNode",
    "verify_dag",
    "measure_kernel_energy",
    "statement_from_chain",
    "slsa_statement",
    "build_governance_predicate",
    "build_in_toto_statement",
    "build_slsa_provenance",
    "resource_descriptor",
    "canonical_json",
    "IN_TOTO_STATEMENT_TYPE",
    "SLSA_PROVENANCE_TYPE",
    "GOVERNANCE_PREDICATE_TYPE",
    "GOVERNED_RUN_BUILD_TYPE",
    "BUILDER_ID",
    "SCHEMA_VERSION",
    "DOCTRINE_FOOTER",
    "selfcheck",
    "__version__",
]
