# Security

Report vulnerabilities privately: use GitHub private vulnerability reporting
("Security" tab -> "Report a vulnerability") or email stephen@szlholdings.com.
Please do not open public issues for security problems. Only the default branch
(`main`) and the kernel build it publishes are supported.

## Serialization

`model.joblib` / pickle / dill are not approved load paths. The kernel source under
`torch-ext/` is. Neither the model repo nor the kernel repo on the Hub lists
`model.joblib` (checked 2026-11-06). If a Hub revision lists it again, treat it as
QUARANTINED executable serialization, do not load it, and report it. Hub files change
only through this repository's committed writer (`.github/workflows/hf-kernel-publish.yml`,
see `tests/test_hub_single_writer.py`), never through an ad-hoc Hub write.
