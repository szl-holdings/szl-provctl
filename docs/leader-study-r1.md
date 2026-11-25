# szl-provctl domain leader study r1 (propose-only)

Date: 2026-11-25. Method: web-verified leader landscape + owner-direct execution under standing authority GREENLIGHT-RULING-2026-11-24-K1 rank5 OUROBOROS_NEXT_TRANCHE. The Kimi governing seat remains stood down per explicit owner directive (disclosed); owner-direct nonce T18-OWNER-DIRECT-20261125-K1. This card is documentation only; it changes no code, CI, config, or existing PR status. All absorb actions are FUTURE PROPOSALS (non-authorizing); implementation and merges remain separately reviewed and gated. Head SHA at study time: 651b2703f4d7d90ed45199f3a11651b9592991a4.

## Domain: provenance control for SZL receipts (in-toto Statement emission, provenance DAG verification, honest energy observation)

## Leaders studied (web-verified 2026-11-25)

1. in-toto — https://github.com/in-toto/in-toto — the attestation/layout framework whose Statement v1 this package emits; moat is the end-to-end layout-verification discipline. This repo already asserts it is NOT a SLSA level and does NOT sign envelopes; that honesty must be preserved.
2. DSSE — https://github.com/secure-systems-lab/dsse — the envelope spec that wraps statements for signing; moat is unambiguous signature envelope semantics. szl-provctl deliberately stops before signing; szl-govsign owns that step.
3. SLSA — https://github.com/slsa-framework/slsa — the provenance level definitions; moat is level-earned-by-evidence framing. SLSA-shaped JSON does not establish a level; the repo's L1-honest/L2-roadmap labeling stays.

## Absorb actions (FUTURE PROPOSALS, non-authorizing)

1. (in-toto) Propose a documentation map from UnifiedReceiptChain export edges to in-toto Statement subjects, keeping BLOCKED nodes surfaced and fail-closed edge checks unchanged.
2. (DSSE) Propose a clarifying doc table of which DSSE responsibility belongs to downstream signers, with no signing implemented or claimed in this repo.
3. (SLSA) Propose keeping an explicit level-earned matrix (today: no signed build provenance in CI; L2 is roadmap) so no card or doc can imply an earned level.
4. (baseline) Propose preserving the NVML energy-delta caveat (device-wide, GPU 0, not kernel-isolated) with MEASURED-or-UNAVAILABLE labeling; no estimated energy is ever proposed.
5. (baseline) Propose preserving the model.joblib QUARANTINE warning and the Kernel Hub revision-load rules verbatim; trust_remote_code guidance is not relaxed.

## Do not do (owner-direct lane doctrine)

Do not merge, bypass required checks, fabricate signatures, attestations, or signing/provenance claims, or claim implementation beyond this card. Verification status stays verification-unknown unless separately measured. Lambda stays Conjecture 1 (advisory, never a theorem).
