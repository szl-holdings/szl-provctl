# szl-provctl

**SOFTWARE_LIMITED.** Software kernel slot for provenance control (in-toto / DSSE over SZL receipts). **Not a model. No weights. Not a complete signing product.**

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

