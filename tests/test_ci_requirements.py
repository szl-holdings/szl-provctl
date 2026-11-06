# SPDX-License-Identifier: Apache-2.0
"""CI dependency locks stay hash-pinned and agree with the workflow pins.

Standard library + pytest only. The kernels loader is never imported here: the
runtime guard (scripts/ci_assert_kernels_version.py) is exercised with a stubbed
metadata lookup, and the static checks read the committed files.
"""
from __future__ import annotations

import importlib.util
import re
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CI_REQ = ROOT / "requirements" / "ci"
SCRIPT = ROOT / "scripts" / "ci_assert_kernels_version.py"

spec = importlib.util.spec_from_file_location("ci_assert_kernels_version", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def _pins(lock: Path) -> dict:
    """name -> version for every requirement line, asserting each one is hashed."""
    pins = {}
    blocks = re.split(r"\n(?=[A-Za-z0-9])", lock.read_text(encoding="utf-8"))
    for block in blocks:
        first = block.split("\n", 1)[0]
        if not first or first.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\;]+)", first)
        assert match, f"{lock.name}: not an exact pin: {first!r}"
        assert "--hash=sha256:" in block, f"{lock.name}: {first!r} has no hash"
        pins[match.group(1).lower()] = match.group(2)
    return pins


@pytest.mark.parametrize("name", ["test", "kernels"])
def test_every_ci_lock_line_is_pinned_and_hashed(name):
    pins = _pins(CI_REQ / f"{name}.txt")
    assert pins, f"{name}.txt is empty"
    for requirement in (CI_REQ / f"{name}.in").read_text(encoding="utf-8").splitlines():
        requirement = requirement.split("#", 1)[0].strip()
        if requirement:
            top = re.split(r"[=<>!~ ;\[]", requirement, maxsplit=1)[0].lower()
            assert top in pins, f"{name}.in requires {top!r}, missing from {name}.txt"


def test_kernels_pin_matches_workflow_env():
    workflow = (ROOT / ".github" / "workflows" / "hf-kernel-publish.yml").read_text(encoding="utf-8")
    env_pin = re.search(r'^\s*KERNELS_VERSION:\s*"([^"]+)"', workflow, re.MULTILINE).group(1)
    in_pin = re.search(r"^kernels==(\S+)", (CI_REQ / "kernels.in").read_text(encoding="utf-8"),
                       re.MULTILINE).group(1)
    assert _pins(CI_REQ / "kernels.txt")["kernels"] == in_pin == env_pin


# Known gap (tracked as a follow-up): torch comes from the PyTorch CPU index,
# whose wheels are not in a hash lock yet. Only this exact command is exempt.
TORCH_CPU_INSTALL = (
    'python -m pip install --disable-pip-version-check --index-url "$TORCH_INDEX" '
    '"torch==${TORCH_VERSION}"'
)


def test_workflows_install_ci_deps_only_from_hashed_locks():
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#"):
                continue  # YAML comment, not a command
            if re.search(r"\bpip3?\s+install\b", line) and line.strip() != TORCH_CPU_INSTALL:
                assert "--require-hashes -r requirements/ci/" in line, f"{path.name}: {line.strip()}"


def test_guard_accepts_matching_version(monkeypatch, capsys):
    monkeypatch.setenv("KERNELS_VERSION", "0.17.2")
    monkeypatch.setattr(guard, "version", lambda name: "0.17.2")
    assert guard.main() == 0
    assert "matches" in capsys.readouterr().out


@pytest.mark.parametrize("env, installed, message", [
    ("0.17.2", "0.18.0", "kernels 0.18.0 is installed but KERNELS_VERSION is 0.17.2"),
    ("", "0.17.2", "KERNELS_VERSION is not set"),
    ("0.17.2", None, "kernels is not installed"),
])
def test_guard_rejects_drift(monkeypatch, capsys, env, installed, message):
    monkeypatch.setenv("KERNELS_VERSION", env)

    def fake_version(name):
        if installed is None:
            raise PackageNotFoundError(name)
        return installed

    monkeypatch.setattr(guard, "version", fake_version)
    assert guard.main() == 1
    assert message in capsys.readouterr().err
