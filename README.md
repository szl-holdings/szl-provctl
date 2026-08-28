# szl-provctl

Software kernel slot for provenance control (in-toto / DSSE over SZL receipts). **Not a model. No weights.**

Hub mirror: [`kernels/SZLHOLDINGS/szl-provctl`](https://huggingface.co/kernels/SZLHOLDINGS/szl-provctl). Card: [`SZLHOLDINGS/szl-provctl`](https://huggingface.co/SZLHOLDINGS/szl-provctl). Hologram Space (separate): [`szl-provctl-live`](https://huggingface.co/spaces/SZLHOLDINGS/szl-provctl-live).

## What this is NOT

- Hub `model.joblib` is **QUARANTINED** executable serialization. Do not `joblib.load` it. GitHub source is the approved path.

- Not trained weights
- Not a complete signing product by itself (see `szl-receipt` + `governed-receipt-spec`)
- No MEASURED CUDA benches here

## Load

```python
from kernels import get_kernel
get_kernel("SZLHOLDINGS/szl-provctl", revision="main", trust_remote_code=True)
```

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.
