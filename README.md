# szl-provctl

**SOFTWARE_LIMITED.** Software kernel slot for provenance control (in-toto / DSSE over SZL receipts). **Not a model. No weights. Not a complete signing product.**

<!-- szl:header v1 -->
<!-- Native identity: szl-brand@4309f6fce89179331b0b3ed8c99494e76c5be256; Orbit v2 icon. -->
<p>
  <a href="https://github.com/szl-holdings">
    <img src="https://raw.githubusercontent.com/szl-holdings/szl-brand/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/logos/orbit-v2/suite/szl-icon-32.svg" alt="SZL Holdings — Orbit v2" width="32" height="32" />
  </a>
</p>

**Control before action. Evidence after.**

[Product](https://a-11-oy.com) · [Proof](https://a11oy.net) · [GitHub organization](https://github.com/szl-holdings)
<!-- /szl:header -->

Hub mirror: [`kernels/SZLHOLDINGS/szl-provctl`](https://huggingface.co/kernels/SZLHOLDINGS/szl-provctl). Model-repo pointer card: [`SZLHOLDINGS/szl-provctl`](https://huggingface.co/SZLHOLDINGS/szl-provctl). The former hologram Space `szl-provctl-live` has been deleted and its source, [`szl-holdings/szl-provctl-live`](https://github.com/szl-holdings/szl-provctl-live), is archived with this repository as its successor; its in-browser DAG verifier page was not ported.

`szl_provctl` turns a SZL `UnifiedReceiptChain` (SHA3-256 hash-chained receipts) into an
in-toto v1 Statement and SLSA provenance v1, verifies a provenance DAG of linked chain
exports edge by edge (missing dependencies, cycles, malformed exports and edge mismatches
fail closed; honest-BLOCKED nodes are surfaced, never dropped), and can record a real NVML
energy delta around one kernel call. Pure Python, standard library only; a CPU is enough.

Public maturity is **SOFTWARE_LIMITED** with no product claim, the resolution recorded in
[szl-hf-frontier#7](https://github.com/szl-holdings/szl-hf-frontier/issues/7) (closed 2026-09-04).
The historical Hub surrogate `model.joblib` is no longer listed in the model or the kernel
repository (checked against the public Hub API on 2026-11-06).

## What this is NOT

- Not a `model.joblib` surrogate. Any copy of that historical file is **QUARANTINED** executable serialization: never `joblib.load` it. GitHub source is the approved path.
- Not trained weights
- Not a complete signing product by itself (see `szl-receipt` + `governed-receipt-spec`). It emits the in-toto v1 Statement that a DSSE envelope wraps; it does not sign it (`szl-govsign` does).
- Not a SLSA level: SLSA-shaped JSON does not establish one, and hash-chain consistency does not authenticate a producer or prove that inputs were truthful or that a graph is complete.
- No MEASURED CUDA benches here. The NVML energy delta is device-wide (GPU index 0), not isolated to the measured kernel.
- Not the pre-action core of a11oy

## Load

Set `SZL_PROVCTL_HF_REVISION` to the immutable **first-class Kernel Hub** commit
from a verified publication of [`kernels/SZLHOLDINGS/szl-provctl`](https://huggingface.co/kernels/SZLHOLDINGS/szl-provctl). Use the `kernels`
client version qualified with that publication. The GitHub source commit,
model-type mirror commit, and Kernel Hub commit are separate identities.
An observed head, a branch name, or a successful import does not qualify a release.

`trust_remote_code=True` permits execution of the selected repository's Python.
Review that exact revision, its provenance and publication evidence before enabling it.
The format check below only rejects missing or mutable revision inputs; it does not
verify hashes, publisher authorization or compatibility. If that evidence is unavailable,
stop the Hub load and use separately reviewed local source for development.

```python
import os
import re

hf_revision = os.environ.get("SZL_PROVCTL_HF_REVISION", "")
if re.fullmatch(r"[0-9a-f]{40}", hf_revision) is None:
    raise ValueError("A verified immutable Kernel Hub revision is required")

from kernels import get_kernel

get_kernel("SZLHOLDINGS/szl-provctl", revision=hf_revision, trust_remote_code=True)
```

A successful load is not a product qualification.

### Where the Kernel Hub revision comes from

`.github/workflows/hf-kernel-publish.yml` in this repository is the only writer of
[`kernels/SZLHOLDINGS/szl-provctl`](https://huggingface.co/kernels/SZLHOLDINGS/szl-provctl).
It builds `build/torch-cpu` and `build/torch-universal` from `torch-ext/szl_provctl/` at one
reviewed GitHub commit, writes the same tree to the kernel repo's `main` and `v1` branches,
and then loads it in a fresh runner with `get_kernel("SZLHOLDINGS/szl-provctl", version=1,
trust_remote_code=True)` and compares every served byte with the GitHub source.
`SZL_KERNEL_SOURCE.json` on the Hub names the GitHub commit each build came from.
The commit of the kernel repo's `v1` branch after a passing `verify` job is the immutable
revision to set in `SZL_PROVCTL_HF_REVISION`. `version=1` alone follows the `v1` channel and
suits development, not a qualified release. The model repo
[`SZLHOLDINGS/szl-provctl`](https://huggingface.co/SZLHOLDINGS/szl-provctl) is a pointer card
only; its commits are not kernel revisions.

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.

### Publication status (checked 2026-11-06)

Both Hub branches (`main` and `v1`) serve the build of GitHub commit
[`1abf90f`](https://github.com/szl-holdings/szl-provctl/tree/1abf90f83873fe832855ef1403ba4977c400db29/torch-ext/szl_provctl)
(2026-10-13), as named by their `SZL_KERNEL_SOURCE.json`. Kernel fixes merged after it
(#18, #21, #22, #23 and #25: structured `missing_dependency` results, malformed-export
rejection, queued CUDA work excluded from per-call energy, invalid MEASURED values
rejected, BLOCKED nodes kept in cycle diagnostics) are on GitHub `main` only until the next
`hf-kernel-publish` run. The weekly drift check compares the Hub with the latest GitHub
release, and this repository has no release yet, so it does not report this gap. Check again:

```bash
curl -sL https://huggingface.co/kernels/SZLHOLDINGS/szl-provctl/resolve/v1/SZL_KERNEL_SOURCE.json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["source_commit"])'
git log --oneline <that commit>..origin/main -- torch-ext
```

## Source-only development

Review `torch-ext/szl_provctl/` at an immutable GitHub commit, separately from any Hub
release: for a Hub build, the `source_commit` its `SZL_KERNEL_SOURCE.json` names (the
`1abf90f` link above for the build served on 2026-11-06).
With the source's dependencies already available, run from the reviewed checkout root:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("torch-ext").resolve()))
import szl_provctl as local_kernel
```

This selects local Python source rather than calling the Hub loader. Importing local
source also executes Python. This documentation check does not run that import,
install dependencies, qualify a runtime or establish a Hub publication.

## Install and verify (local checkout)

The package has no runtime dependencies (`torch` and `pynvml` are optional). Tested with
Python 3.12 and 3.13:

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[test]'      # installs torch-ext/szl_provctl as `szl_provctl`
python -m pytest                        # the full suite, CPU only, no network
python -c 'import szl_provctl as pc; print(pc.selfcheck()["ok"])'   # True
python -I scripts/eval.py               # no model.joblib, no pickle/joblib loader calls
```

CI runs the same suite without installing the package
(`PYTHONPATH=torch-ext python -m pytest tests -q`), the offline publisher tests
(`python -m unittest discover -s tests -p "test_szl_kernel_publish.py"`), and a
byte-equality check of `_chain.py` against `szl-holdings/szl-evidence-core`
(`.github/workflows/chain-drift-guard.yml`). CI tools install from the hash-locked files
in `requirements/ci/`. A passing suite exercises the programmed assertions only; it is not
a product qualification.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
