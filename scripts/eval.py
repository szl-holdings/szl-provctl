#!/usr/bin/env python3
"""Fail-closed evaluator.

Approved path: kernel source under torch-ext/.
model.joblib is executable serialization. This script never calls a pickle
loader. If the pickle file is in the tree, exit 2.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALL = re.compile(r"\b(?:joblib\.(?:load|dump)|pickle\.loads?|dill\.load)\s*\(")


def source_files():
    """Repository Python files: tracked plus untracked-but-not-ignored.

    Git-ignored paths (a local .venv/, build/) are third-party or generated code,
    not this repository's source. Without git, walk the tree but skip VCS
    metadata and any virtualenv (a directory holding pyvenv.cfg).
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout.decode("utf-8")
        names = sorted({n for n in out.split("\0") if n.endswith(".py")})
        return [os.path.join(ROOT, n) for n in names if os.path.isfile(os.path.join(ROOT, n))]
    except (OSError, subprocess.CalledProcessError):
        found = []
        for dirpath, dirnames, files in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d != ".git"
                           and not os.path.isfile(os.path.join(dirpath, d, "pyvenv.cfg"))]
            found += [os.path.join(dirpath, f) for f in files if f.endswith(".py")]
        return sorted(found)


def main() -> int:
    joblib_path = os.path.join(ROOT, "model.joblib")
    if os.path.exists(joblib_path):
        digest = hashlib.sha256(open(joblib_path, "rb").read()).hexdigest()
        print(f"QUARANTINE: model.joblib present sha256={digest} — not an approved load path")
        return 2
    hits = []
    for path in source_files():
        text = open(path, encoding="utf-8").read()
        for i, line in enumerate(text.splitlines(), 1):
            if CALL.search(line):
                hits.append(f"{path}:{i}:{line.strip()}")
    if hits:
        print("QUARANTINE: forbidden loader calls still in source:")
        print("\n".join(hits))
        return 2
    print("PASS: no model.joblib; no pickle loader calls in source. Kernel source is the approved path.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
