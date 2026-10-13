---
license: apache-2.0
library_name: kernels
tags:
  - kernel
  - szl-holdings
  - provenance
  - supply-chain
  - in-toto
  - slsa
  - governance
---

<p><img src="https://raw.githubusercontent.com/szl-holdings/szl-brand/27d12e77fc0f9f1a0e5fae8b34adf2380d51d070/kit/logos/orbit-v2/suite/szl-icon-32.svg" alt="SZL Holdings" width="40" height="40" /></p>


# {{KERNEL_NAME}}

Provenance-DAG traversal, receipt-chain records shaped as in-toto Statement v1 and SLSA
provenance v1, and an optional per-kernel NVML energy observation. Pure-Python (noarch)
kernel, **limited software maturity, no trained weights**.

Published from GitHub
[{{GITHUB_REPOSITORY}}](https://github.com/{{GITHUB_REPOSITORY}}) by its
`hf-kernel-publish` workflow. GitHub is the source of truth; this repository is
written only by that workflow.

## Load it

```python
# pip install "kernels>=0.17.2" torch
from kernels import get_kernel

kernel = get_kernel("{{REPO_ID}}", version={{KERNEL_VERSION}}, trust_remote_code=True)

report = kernel.selfcheck()          # CPU-only, never raises
assert report["ok"], report

chain = kernel.UnifiedReceiptChain()
chain.emit("example", "inspect", {"record": "synthetic"})
dag = kernel.ProvenanceDAG()
dag.add_run("example", chain)
print(kernel.verify_dag(dag)["ok"])
```

- `version={{KERNEL_VERSION}}` resolves the `v{{KERNEL_VERSION}}` branch, the stable API channel. It is
  republished on every release. The `kernels` library refuses a call that names neither a
  version nor a revision.
- `trust_remote_code` is required: SZLHOLDINGS is not a trusted kernel publisher on the Hub.
  Loading this kernel executes its Python. The narrowest form is
  `trust_remote_code=["{{REPO_ID}}"]`.
- CPU hosts load `build/torch-cpu`; CUDA and other hosts load `build/torch-universal`.
  Both variants carry identical code, built from the same GitHub commit.

### Pin an exact build (production)

```python
from huggingface_hub import HfApi
from kernels import get_kernel

refs = HfApi().list_repo_refs("{{REPO_ID}}", repo_type="kernel")
pin = next(b.target_commit for b in refs.branches if b.name == "v{{KERNEL_VERSION}}")
kernel = get_kernel("{{REPO_ID}}", revision=pin, trust_remote_code=["{{REPO_ID}}"])
```

Record `pin` (a commit of this kernel repository) in your lockfile.
`SZL_KERNEL_SOURCE.json` in this repository names the GitHub commit each build came from.
Commits of the model repository
[{{MODEL_TWIN_URL}}]({{MODEL_TWIN_URL}}) and GitHub commits are not kernel revisions and do
not resolve here.

## Before you use it

- Hash-chain consistency does not authenticate the producer, prove truthful inputs, or
  establish that a provenance graph is complete.
- SLSA-shaped JSON does not establish a SLSA level. Validate exported statements with the
  external verifier that will consume them.
- Treat malformed dependency graphs as failure. Energy is reported only as a real NVML
  measurement; it is unavailable (never estimated) when no measurement backend exists.
- `proven_trust` is structurally locked `False`. Lambda uniqueness is Conjecture 1: open
  and advisory, never a theorem.
- A successful load or `selfcheck()` exercises the programmed assertions only. It is not a
  product qualification. No benchmark numbers are claimed here.

Apache-2.0. © 2026 SZL Holdings.

Artwork: SZL Orbit · © 2026 SZL Holdings / Stephen Lutar · [CC BY 4.0](https://github.com/szl-holdings/szl-brand/blob/27d12e77fc0f9f1a0e5fae8b34adf2380d51d070/kit/LICENSE) · [Trademark notice](https://github.com/szl-holdings/szl-brand/blob/27d12e77fc0f9f1a0e5fae8b34adf2380d51d070/NOTICE).
