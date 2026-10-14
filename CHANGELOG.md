# Changelog

## 2026-10-14

- `ProvenanceDAG.verify_dag()` no longer raises `KeyError` when a node declares a
  dependency that is not in the DAG. Every declared dependency is checked before the
  topological sort. A missing one returns `ok=False` with
  `first_break.kind == "missing_dependency"`, the missing ids (`missing`), the nodes
  that declared each one (`dependents`), an empty `order` and no `node_results`, so no
  node is reported as verified in an incomplete graph. Before this, the documented
  `missing_dependency` result could not be reached. New `missing_dependencies()` lists
  them; `_topo_order()` raises `MissingDependencyError` (a `ValueError`). Valid DAGs,
  cycle diagnosis and receipt-chain checks are unchanged.

## 2026-10-13

- Add the canonical kernel publisher: `.github/workflows/hf-kernel-publish.yml`,
  `scripts/szl_kernel_publish.py` and `.github/hf-kernels.json`. It builds
  `build/torch-cpu` and `build/torch-universal` from `torch-ext/szl_provctl/` at one
  reviewed commit, publishes them to `main` and `v1` of `kernels/SZLHOLDINGS/szl-provctl`
  (fast-forward git only), verifies `get_kernel(..., version=1, trust_remote_code=True)`
  in a fresh runner, then turns the model repo into a pointer card. A weekly job checks
  that the Hub still serves the latest release. The workflow and its script are the
  only `tests/test_hub_single_writer.py` WRITERS.
- Remove the committed `build/torch-universal/` copy. The publisher generates `build/` from
  `torch-ext/` on every publish, so a second copy in Git could only drift.
- Kernel docstring and README: load with `version=1` (the `v1` channel) instead of
  `revision="main"`; production still pins an immutable `v1` kernel-repo commit.

## 2026-09-29

- Retire the one-shot Hub joblib quarantine writer (`hub-joblib-quarantine.yml`,
  `scripts/hub_quarantine_joblib.py`). The live Hub model and kernel repos hold no
  `model.joblib`, and the workflow was an unlocked Hub writer with an
  `HF_TOKEN || HF_ORG_TOKEN` fallback. The source-side refusal of joblib, pickle and
  dill loaders is unchanged. `tests/test_hub_single_writer.py` now fails if any file
  here gains a Hub write path outside a committed mirror.

## 2026-08-28

- Quarantine joblib/pickle: forge no longer dumps `model.joblib`; eval refuses the file; Hub deletion is a dispatched PR with exact parent commit.
Honesty README. No kernel math changed.
