# SPDX-License-Identifier: Apache-2.0
"""Governance predicates must preserve usable numeric energy evidence."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

from szl_provctl import build_governance_predicate, canonical_json


def predicate(energy):
    return build_governance_predicate(
        chain_head="a" * 64,
        kernels_touched=["fixture"],
        chain_depth=1,
        energy=energy,
    )


@pytest.mark.parametrize(
    "joules",
    [True, False, "1.5", "nan", float("nan"), float("inf"), -float("inf"), -1, -0.1],
)
def test_measured_energy_rejects_invalid_values_before_building_predicate(joules):
    with pytest.raises(ValueError, match="finite non-negative number"):
        predicate({"label": "MEASURED", "joules": joules, "source": "fixture"})


@pytest.mark.parametrize("joules", [0, 0.0, 1, 1.5])
def test_measured_energy_preserves_valid_numbers(joules):
    result = predicate({"label": "MEASURED", "joules": joules, "source": "fixture"})
    assert result["energy"] == {
        "label": "MEASURED", "joules": float(joules), "source": "fixture"
    }
    assert result["lambda"]["proven_trust"] is False
    canonical_json(result)


def test_measured_energy_rejects_integer_float_overflow():
    with pytest.raises(ValueError, match="finite non-negative number"):
        predicate({"label": "MEASURED", "joules": 10**400, "source": "fixture"})


@pytest.mark.parametrize("label", ["UNAVAILABLE", "UNAVAILABLE_NO_NVML"])
def test_unavailable_energy_remains_null(label):
    result = predicate({"label": label, "joules": None, "source": "fixture"})
    assert result["energy"] == {"label": label, "joules": None, "source": "fixture"}

