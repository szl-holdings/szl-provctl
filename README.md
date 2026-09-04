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

```python
from kernels import get_kernel
get_kernel("SZLHOLDINGS/szl-provctl", revision="main", trust_remote_code=True)
```

A successful load is not a product qualification.

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.
