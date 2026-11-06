#!/usr/bin/env python3
"""Refuse pickle/joblib loaders in the approved source path."""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CALL = re.compile(r"\b(?:joblib\.(?:load|dump)|pickle\.loads?|dill\.load)\s*\(")


def source_files(root: pathlib.Path = ROOT) -> list:
    """Repository Python files: tracked plus untracked-but-not-ignored.

    Git-ignored paths (a local .venv/, build/) are third-party or generated code,
    not this repository's source. Without git, walk the tree but skip VCS
    metadata and any virtualenv (a directory holding pyvenv.cfg).
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root, check=True, capture_output=True,
        ).stdout.decode("utf-8")
        names = sorted({n for n in out.split("\0") if n.endswith(".py")})
        return [root / n for n in names if (root / n).is_file()]
    except (OSError, subprocess.CalledProcessError):
        found = []
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"
                           and not os.path.isfile(os.path.join(dirpath, d, "pyvenv.cfg"))]
            found += [pathlib.Path(dirpath, f) for f in files if f.endswith(".py")]
        return sorted(found)


class NoUnsafeSerialization(unittest.TestCase):
    def test_no_model_joblib_in_tree(self) -> None:
        self.assertFalse((ROOT / "model.joblib").exists())

    def test_no_forbidden_loader_calls(self) -> None:
        hits = []
        for path in source_files():
            text = path.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), 1):
                if CALL.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{i}:{line.strip()}")
        self.assertEqual(hits, [])

    def test_scope_skips_virtualenvs_but_not_source(self) -> None:
        # A local virtualenv's site-packages (pip, packaging) mention pickle loaders;
        # that is not this repository's source. New source files still count.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / ".venv" / "lib").mkdir(parents=True)
            (root / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
            (root / ".venv" / "lib" / "dep.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
            (root / ".gitignore").write_text(".venv/\n", encoding="utf-8")
            expected = [root / "pkg" / "mod.py"]
            if _git(root, "rev-parse", "--is-inside-work-tree") != 0:
                self.assertEqual(source_files(root), expected)  # no git repository: walk
            if _git(root, "init", "-q") == 0:
                self.assertEqual(source_files(root), expected)  # git: ignored .venv skipped


def _git(root: pathlib.Path, *args: str):
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True).returncode
    except OSError:
        return None


if __name__ == "__main__":
    unittest.main()
