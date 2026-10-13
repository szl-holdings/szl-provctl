# SPDX-License-Identifier: Apache-2.0
"""Smoke hook for hf-kernel-publish (szl-provctl).

`smoke(kernel)` receives the module that the `kernels` loader imported, from a local
build (check-local) or from the Hub (verify). Raise, or return False, to fail the run.
CPU-only, deterministic and fast; mirrors tests/test_smoke.py. The result's repr is
written to the receipt.
"""
from __future__ import annotations

REQUIRED_CHECKS = (
    "proven_trust_locked_false",
    "fabricated_energy_rejected",
    "honest_blocked_not_flippable",
    "dag_tamper_detected",
    "energy_cpu_unavailable_not_fabricated",
)


def smoke(kernel):
    report = kernel.selfcheck()
    if report.get("error") is not None or report.get("ok") is not True:
        raise AssertionError(f"selfcheck failed: {report}")
    checks = report.get("checks") or {}
    failed = [name for name in REQUIRED_CHECKS if checks.get(name) is not True]
    if failed:
        raise AssertionError(f"selfcheck checks not True: {failed}")

    chain = kernel.UnifiedReceiptChain()
    chain.emit("governed_norm", "rms_norm", {"eps": 1e-6})
    stmt = kernel.statement_from_chain(chain, decision="ALLOWED")
    if stmt.get("_type") != kernel.IN_TOTO_STATEMENT_TYPE:
        raise AssertionError("statement_from_chain must emit an in-toto v1 Statement")
    dag = kernel.ProvenanceDAG()
    dag.add_run("run", chain)
    if kernel.verify_dag(dag).get("ok") is not True:
        raise AssertionError("verify_dag rejected a one-run DAG")
    return {"ok": True, "checks": len(checks), "chain_source": report.get("chain_source"),
            "version": report.get("version")}
