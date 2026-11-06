# Changelog

## 2026-11-06

- Packaging: `pyproject.toml` now declares a setuptools build that installs
  `torch-ext/szl_provctl` as `szl_provctl`, a `test` extra, project URLs and an SPDX
  license. Before, `pip install -e '.[test]'` installed an empty distribution (no
  importable module, no `test` extra). Still `Private :: Do Not Upload`.
- CI supply chain: pytest (CPU contract) and the `kernels` loader (hf-kernel-publish
  build and verify jobs) install from hash-locked `requirements/ci/*.txt` with
  `--require-hashes`; `scripts/ci_assert_kernels_version.py` fails a job whose lock and
  `KERNELS_VERSION` disagree. The chain drift guard runs `szl-evidence-core` from a
  commit-pinned checkout instead of `pip install git+...`. Dependabot watches
  `/requirements/ci`, and a pull request that changes the kernels lock or its guard runs
  the hf-kernel-publish build check. torch from the PyTorch CPU index is still unhashed
  (follow-up).
- `tests/test_energy_interval.py` imports the kernel source on its own, so it passes
  when run alone; `tests/test_ci_requirements.py` keeps the CI locks hashed and in step
  with the workflow pins.
- The pickle/joblib scanners (`scripts/eval.py`, `tests/test_no_unsafe_serialization.py`)
  read repository source (tracked plus untracked, not git-ignored) instead of every
  `*.py` under the checkout. With a local `.venv/` they used to fail on third-party
  site-packages text; untracked source files are still scanned.
- `scripts/forge.py` imports `torch-ext/` (the `build/` copy it read was removed on
  2026-10-13), records the measured platform instead of a hard-coded host, and stops on
  a `first_break.kind` outside its class map instead of relabelling it.
- Docs: the deleted hologram Space link is replaced by its archived source; the README
  gains install/verify commands, the proof boundary and the Hub publication status; the
  kernel docstrings drop unverified "no other tool does this" claims and state that the
  NVML energy delta is device-wide (GPU 0). `SECURITY.md` scopes the single-writer rule
  to what this repository controls: the kernel repo, and only the pointer card and pruned
  paths of the model repo, which other accounts also commit to. No kernel behaviour changed.

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
