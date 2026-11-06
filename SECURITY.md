# Security

Report vulnerabilities privately: use GitHub private vulnerability reporting
("Security" tab -> "Report a vulnerability") or email stephen@szlholdings.com.
Please do not open public issues for security problems. Only the default branch
(`main`) and the kernel build it publishes are supported.

## Serialization

`model.joblib` / pickle / dill are not approved load paths. The kernel source under
`torch-ext/` is. Neither the model repo nor the kernel repo on the Hub lists
`model.joblib` (checked 2026-11-06). If a Hub revision lists it again, treat it as
QUARANTINED executable serialization, do not load it, and report it.

## Hub write path

Within this repository only `.github/workflows/hf-kernel-publish.yml` (with its transport
`scripts/szl_kernel_publish.py`) may write to the Hub; `tests/test_hub_single_writer.py`
fails if any other tracked file calls a Hub write API or binds a Hugging Face secret.
That workflow made every commit on the kernel repo's `main` and `v1` branches since
2026-10-13. In the model repo `SZLHOLDINGS/szl-provctl` it writes only the pointer
`README.md` and removes the paths in `.github/hf-kernels.json` (`model_twin.prune_paths`).
Other accounts also commit to the model repo (for example on 2026-11-04 and 2026-11-06),
so its current contents are not controlled by this repository alone. Make Hub fixes through this
repository's writer, not through an ad-hoc Hub write.
