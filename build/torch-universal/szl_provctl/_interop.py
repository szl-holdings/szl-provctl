# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""Interop bridge: a governed run -> the standard supply-chain world.

Turns a szl_kernels ``UnifiedReceiptChain`` into the EXACT shapes the rest of
the ecosystem already verifies:

  * in-toto v1 Statement   -> ``https://in-toto.io/Statement/v1``
        subject[].digest = the chain head (sha3_256), predicateType = our
        governance predicate. This is the payload a DSSE envelope / Sigstore
        Bundle wraps (cosign v2.6 ``--statement``), so szl-govsign can sign it
        and ANY in-toto verifier can read it.
  * SLSA Provenance v1     -> ``https://slsa.dev/provenance/v1``
        a governed RUN as a first-class build-provenance event:
        buildDefinition.{buildType, externalParameters, resolvedDependencies}
        + runDetails.{builder.id, metadata, byproducts}.

Field names are spec-exact (verified against in-toto/attestation spec v1 and
slsa.dev/spec/v1.0/provenance). Stdlib only.

DOCTRINE (binding, structural):
  * proven_trust is LOCKED False — no code path sets it True. Λ = Conjecture 1
    (OPEN); a recorded gate pass is advisory, never proven trust.
  * energy is MEASURED-only — a non-measured value is rejected at build time;
    None/UNAVAILABLE is honest, never a fabricated joule.
  * an honest-BLOCKED verdict is represented as BLOCKED — never flipped.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

# Spec-exact constants ------------------------------------------------------
IN_TOTO_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
SLSA_PROVENANCE_TYPE = "https://slsa.dev/provenance/v1"
GOVERNANCE_PREDICATE_TYPE = "https://szl.holdings/governance/v1"
GOVERNED_RUN_BUILD_TYPE = "https://szl.holdings/governed-run/v1"
BUILDER_ID = "https://github.com/szl-holdings/szl-kernels"
SCHEMA_VERSION = "szl-provctl/0.1.0"

_ALLOWED_ENERGY_LABELS = {"MEASURED", "UNAVAILABLE_NO_NVML", "UNAVAILABLE"}


def _sha3(s: str) -> str:
    return hashlib.sha3_256(s.encode("utf-8")).hexdigest()


def resource_descriptor(
    name: str,
    digest_hex: str,
    *,
    algorithm: str = "sha3_256",
    uri: Optional[str] = None,
) -> Dict[str, Any]:
    """An in-toto v1 ResourceDescriptor (also reused by SLSA resolvedDependencies).

    Each MUST carry a ``digest``; ``name``/``uri`` are identifiers.
    """
    rd: Dict[str, Any] = {"name": name, "digest": {algorithm: digest_hex}}
    if uri is not None:
        rd["uri"] = uri
    return rd


def _normalize_energy(energy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Enforce MEASURED-only. Reject any non-measured numeric joule value."""
    if energy is None:
        return {"label": "UNAVAILABLE_NO_NVML", "joules": None, "source": "no measurement supplied"}
    label = str(energy.get("label", "UNAVAILABLE"))
    joules = energy.get("joules", None)
    if label not in _ALLOWED_ENERGY_LABELS:
        raise ValueError(
            f"energy label {label!r} not allowed; MEASURED-only "
            f"(one of {sorted(_ALLOWED_ENERGY_LABELS)})"
        )
    if label != "MEASURED" and joules is not None:
        raise ValueError("non-MEASURED energy must report joules=None — never fabricated")
    if label == "MEASURED" and joules is None:
        raise ValueError("MEASURED energy must carry a real joule value")
    return {
        "label": label,
        "joules": (None if joules is None else float(joules)),
        "source": str(energy.get("source", "")),
    }


def build_governance_predicate(
    *,
    chain_head: str,
    kernels_touched: List[str],
    chain_depth: int,
    lambda_score: Optional[float] = None,
    energy: Optional[Dict[str, Any]] = None,
    decision: str = "ALLOWED",
    honest_blocked: bool = False,
) -> Dict[str, Any]:
    """Assemble the ``https://szl.holdings/governance/v1`` predicate body.

    proven_trust is structurally locked False. decision in {ALLOWED, BLOCKED}.
    """
    if decision not in ("ALLOWED", "BLOCKED"):
        raise ValueError("decision must be ALLOWED or BLOCKED")
    if honest_blocked and decision != "BLOCKED":
        raise ValueError("honest_blocked=True requires decision=BLOCKED (never flip a verdict)")
    return {
        "schema": SCHEMA_VERSION,
        "lambda": {
            "score": (None if lambda_score is None else float(lambda_score)),
            "advisory": True,
            "status": "Conjecture 1 (open) — advisory only, NOT proven trust",
            "proven_trust": False,  # LOCKED: no path sets this True
        },
        "energy": _normalize_energy(energy),
        "decision": {"status": decision, "honest_blocked": bool(honest_blocked)},
        "provenance": {
            "chain_head": chain_head,
            "chain_depth": int(chain_depth),
            "kernels_touched": list(kernels_touched),
            "digest_alg": "sha3_256",
            "note": "integrity fingerprint, not a signature",
        },
    }


def build_in_toto_statement(
    *,
    subject_name: str,
    subject_digest_hex: str,
    predicate: Dict[str, Any],
    predicate_type: str = GOVERNANCE_PREDICATE_TYPE,
    subject_digest_alg: str = "sha3_256",
) -> Dict[str, Any]:
    """A spec-exact in-toto v1 Statement (the DSSE/Sigstore payload).

    _type = https://in-toto.io/Statement/v1 ; subject[].digest required.
    """
    return {
        "_type": IN_TOTO_STATEMENT_TYPE,
        "subject": [
            {"name": subject_name, "digest": {subject_digest_alg: subject_digest_hex}}
        ],
        "predicateType": predicate_type,
        "predicate": predicate,
    }


def statement_from_chain(
    chain: Any,
    *,
    subject_name: str = "szl_kernels/UnifiedReceiptChain",
    lambda_score: Optional[float] = None,
    energy: Optional[Dict[str, Any]] = None,
    decision: str = "ALLOWED",
    honest_blocked: bool = False,
) -> Dict[str, Any]:
    """One call: chain -> governance predicate -> in-toto v1 Statement.

    The Statement's subject digest IS the chain head, so signing the Statement
    binds the signature to the exact provenance the chain recorded.
    """
    head = chain.head()
    pred = build_governance_predicate(
        chain_head=head,
        kernels_touched=chain.kernels_touched(),
        chain_depth=chain.count(),
        lambda_score=lambda_score,
        energy=energy,
        decision=decision,
        honest_blocked=honest_blocked,
    )
    return build_in_toto_statement(
        subject_name=subject_name,
        subject_digest_hex=head,
        predicate=pred,
    )


def build_slsa_provenance(
    *,
    chain: Any,
    resolved_dependencies: List[Dict[str, Any]],
    invocation_id: str,
    started_on: str,
    finished_on: str,
    external_parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """A SLSA v1.0 provenance predicate for a governed RUN.

    A governed forward pass becomes a first-class build-provenance event:
    buildType = our governed-run URI; resolvedDependencies = suite members +
    their digests; byproducts include the UnifiedReceiptChain head descriptor.
    """
    head = chain.head()
    chain_blob = chain.to_json()
    chain_blob_digest = _sha3(chain_blob)
    return {
        "buildDefinition": {
            "buildType": GOVERNED_RUN_BUILD_TYPE,
            "externalParameters": dict(external_parameters or {}),
            "internalParameters": {
                "schema": SCHEMA_VERSION,
                "lambda_status": "Conjecture 1 (open) — advisory only",
                "energy_policy": "MEASURED-only",
            },
            "resolvedDependencies": list(resolved_dependencies),
        },
        "runDetails": {
            "builder": {
                "id": BUILDER_ID,
                "version": {"szl_provctl": "0.1.0"},
            },
            "metadata": {
                "invocationId": invocation_id,
                "startedOn": started_on,
                "finishedOn": finished_on,
            },
            "byproducts": [
                resource_descriptor(
                    "szl_kernels/UnifiedReceiptChain.head", head
                ),
                resource_descriptor(
                    "szl_kernels/UnifiedReceiptChain.export", chain_blob_digest
                ),
            ],
        },
    }


def slsa_statement(
    *,
    chain: Any,
    resolved_dependencies: List[Dict[str, Any]],
    invocation_id: str,
    started_on: str,
    finished_on: str,
    external_parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Wrap the SLSA provenance predicate in a spec-exact in-toto v1 Statement."""
    pred = build_slsa_provenance(
        chain=chain,
        resolved_dependencies=resolved_dependencies,
        invocation_id=invocation_id,
        started_on=started_on,
        finished_on=finished_on,
        external_parameters=external_parameters,
    )
    return build_in_toto_statement(
        subject_name="szl_kernels/UnifiedReceiptChain",
        subject_digest_hex=chain.head(),
        predicate=pred,
        predicate_type=SLSA_PROVENANCE_TYPE,
    )


def canonical_json(obj: Dict[str, Any]) -> str:
    """Deterministic JSON for hashing/DSSE PAE (sorted keys, compact)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


__all__ = [
    "IN_TOTO_STATEMENT_TYPE",
    "SLSA_PROVENANCE_TYPE",
    "GOVERNANCE_PREDICATE_TYPE",
    "GOVERNED_RUN_BUILD_TYPE",
    "BUILDER_ID",
    "SCHEMA_VERSION",
    "resource_descriptor",
    "build_governance_predicate",
    "build_in_toto_statement",
    "statement_from_chain",
    "build_slsa_provenance",
    "slsa_statement",
    "canonical_json",
]
