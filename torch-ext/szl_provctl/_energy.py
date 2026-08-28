# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""Per-kernel MEASURED energy — bound to kernel identity in the chain.

The gap no leader fills: CodeCarbon measures real joules but at process
granularity with no provenance binding; NVML's energy counter is device-wide.
``measure_kernel_energy`` reads the **real NVML cumulative-energy counter delta**
around a SINGLE kernel call and writes an energy receipt that names the exact
kernel/op it measured — energy bound to kernel identity, inside the same
UnifiedReceiptChain.

DOCTRINE (binding): energy is MEASURED-only. No NVML / no GPU =>
joules=None, label=UNAVAILABLE_NO_NVML. A joule is NEVER fabricated, estimated,
or modeled here.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional, Tuple


def _read_nvml_energy_millijoules() -> Optional[Tuple[float, str]]:
    """Return (millijoules, source) from the real NVML total-energy counter, or None.

    Uses nvmlDeviceGetTotalEnergyConsumption (device-wide cumulative mJ since
    last driver reload). Returns None if pynvml/NVML/GPU is unavailable — caller
    then reports UNAVAILABLE_NO_NVML. Never raises into the hot path.
    """
    try:
        import pynvml  # type: ignore
    except Exception:
        return None
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mj = pynvml.nvmlDeviceGetTotalEnergyConsumption(handle)
        return (float(mj), "pynvml.nvmlDeviceGetTotalEnergyConsumption[gpu0]")
    except Exception:
        return None


def measure_kernel_energy(
    chain: Any,
    fn: Callable[..., Any],
    *,
    kernel: str,
    op: str,
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run ``fn(*args, **kwargs)`` once, MEASURE energy around just that call,
    and emit an energy receipt naming the kernel/op measured.

    Returns {"output", "receipt"}. The receipt's joules is a REAL NVML delta or
    None (UNAVAILABLE_NO_NVML) — never fabricated.
    """
    kwargs = kwargs or {}

    # CUDA sync (if torch+CUDA present) so the counter delta brackets the call.
    def _sync() -> None:
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                torch.cuda.synchronize()
        except Exception:
            pass

    before = _read_nvml_energy_millijoules()
    _sync()
    t0 = time.perf_counter()
    output = fn(*args, **kwargs)
    _sync()
    t1 = time.perf_counter()
    after = _read_nvml_energy_millijoules()

    wall_ms = (t1 - t0) * 1000.0
    if before is not None and after is not None:
        delta_mj = after[0] - before[0]
        # counter is monotonic; a negative delta means a reset/rollover — honest UNAVAILABLE
        if delta_mj >= 0:
            measurement = {
                "label": "MEASURED",
                "joules": delta_mj / 1000.0,
                "source": after[1],
            }
        else:
            measurement = {
                "label": "UNAVAILABLE",
                "joules": None,
                "source": "nvml counter rollback — not fabricated",
            }
    else:
        measurement = {
            "label": "UNAVAILABLE_NO_NVML",
            "joules": None,
            "source": "no NVML/GPU — joules not fabricated",
        }

    receipt = chain.emit(
        "energy_core",
        "measure_kernel_energy",
        {
            "measured_kernel": str(kernel),
            "measured_op": str(op),
            "label": measurement["label"],
            "joules": measurement["joules"],
            "wall_ms": round(wall_ms, 4),
            "source": measurement["source"],
            "policy": "MEASURED-only",
        },
    )
    return {"output": output, "receipt": receipt}


__all__ = ["measure_kernel_energy"]
