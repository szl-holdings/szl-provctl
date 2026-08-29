# SPDX-License-Identifier: Apache-2.0
"""CPU smoke: import szl_provctl and run selfcheck (in-toto / SLSA / DAG)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

import szl_provctl as pc


def test_selfcheck():
    report = pc.selfcheck()
    assert report.get("error") is None, report
    assert report["ok"] is True
    checks = report["checks"]
    assert checks["proven_trust_locked_false"] is True
    assert checks["fabricated_energy_rejected"] is True
    assert checks["honest_blocked_not_flippable"] is True
    assert checks["dag_tamper_detected"] is True
    assert checks["energy_cpu_unavailable_not_fabricated"] is True


if __name__ == "__main__":
    test_selfcheck()
    print("OK — szl_provctl CPU smoke")
