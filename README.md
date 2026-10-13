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

Hub mirror: [`kernels/SZLHOLDINGS/szl-provctl`](https://huggingface.co/kernels/SZLHOLDINGS/szl-provctl). Card: [`SZLHOLDINGS/szl-provctl`](https://huggingface.co/SZLHOLDINGS/szl-provctl). Hologram Space (separate): [`szl-provctl-live`](https://huggingface.co/spaces/SZLHOLDINGS/szl-provctl-live).

Public maturity stays limited while Hub residue (`model.joblib` if still listed) is quarantined and while product claims are forbidden by [szl-hf-frontier#7](https://github.com/szl-holdings/szl-hf-frontier/issues/7).

## What this is NOT

- Hub `model.joblib` is **QUARANTINED** executable serialization. Do not `joblib.load` it. GitHub source is the approved path.
- Not trained weights
- Not a complete signing product by itself (see `szl-receipt` + `governed-receipt-spec`)
- No MEASURED CUDA benches here
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

## Source-only development

Review [`torch-ext/szl_provctl/`](https://github.com/szl-holdings/szl-provctl/tree/ce4a4cd36abba999de44b774a559b6fe33cf329e/torch-ext/szl_provctl)
at that immutable GitHub source revision, separately from any Hub release.
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

