"""Per-call energy must exclude work queued before the measured call."""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

# Same bootstrap as the sibling tests, so this file also runs on its own
# (`pytest tests/test_energy_interval.py`) from a plain checkout.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

from szl_provctl import UnifiedReceiptChain
from szl_provctl import _energy


def test_energy_excludes_previously_queued_gpu_work(monkeypatch):
    state = {"millijoules": 1000, "pending": 7000, "calls": 0}

    def synchronize():
        state["millijoules"] += state["pending"]
        state["pending"] = 0

    def kernel(*args, **kwargs):
        assert args == ("fixture input",)
        assert kwargs == {"scale": 2}
        state["calls"] += 1
        state["pending"] += 1200
        return "kernel output"

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(
        is_available=lambda: True, synchronize=synchronize,
    )))
    monkeypatch.setattr(_energy, "_read_nvml_energy_millijoules", lambda: (
        state["millijoules"], "fixture GPU counter",
    ))
    chain = UnifiedReceiptChain()
    result = _energy.measure_kernel_energy(
        chain, kernel, kernel="example", op="run",
        args=("fixture input",), kwargs={"scale": 2},
    )

    assert result["output"] == "kernel output"
    assert state["calls"] == 1
    assert state["pending"] == 0
    attrs = result["receipt"]["attrs"]
    assert attrs["label"] == "MEASURED"
    assert attrs["joules"] == pytest.approx(1.2)
    assert chain.verify()[0] is True


@pytest.mark.parametrize("readings, label", [
    ([(9000, "fixture"), (1000, "fixture")], "UNAVAILABLE"),
    ([None, (1000, "fixture")], "UNAVAILABLE_NO_NVML"),
    ([(1000, "fixture"), None], "UNAVAILABLE_NO_NVML"),
])
def test_energy_missing_or_reset_counter_stays_unavailable(monkeypatch, readings, label):
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(
        is_available=lambda: False,
    )))
    counters = iter(readings)
    monkeypatch.setattr(_energy, "_read_nvml_energy_millijoules", lambda: next(counters))
    chain = UnifiedReceiptChain()

    def kernel(*args, **kwargs):
        assert args == ()
        assert kwargs == {}
        return 42

    result = _energy.measure_kernel_energy(chain, kernel, kernel="example", op="run")

    assert result["output"] == 42
    assert result["receipt"]["attrs"]["label"] == label
    assert result["receipt"]["attrs"]["joules"] is None
    assert chain.verify()[0] is True
