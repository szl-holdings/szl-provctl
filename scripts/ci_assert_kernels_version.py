#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""CI guard: the installed ``kernels`` loader is the version the workflow names.

``hf-kernel-publish.yml`` installs ``kernels`` (and its dependencies) from the
hash-locked ``requirements/ci/kernels.txt`` and reports ``KERNELS_VERSION`` in
step names and receipts. If the lock and the env pin ever disagree, this exits
non-zero before anything is built, published or verified with an unreviewed
loader version. It reads installed package metadata only (no import of
``kernels`` or ``torch``). Standard library only.
"""
from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version


def main() -> int:
    want = os.environ.get("KERNELS_VERSION", "")
    if not want:
        print("::error::KERNELS_VERSION is not set", file=sys.stderr)
        return 1
    try:
        got = version("kernels")
    except PackageNotFoundError:
        print("::error::kernels is not installed", file=sys.stderr)
        return 1
    if got != want:
        print(
            f"::error::kernels {got} is installed but KERNELS_VERSION is {want}; "
            "update requirements/ci/kernels.in, requirements/ci/kernels.txt and "
            "KERNELS_VERSION together",
            file=sys.stderr,
        )
        return 1
    print(f"kernels {got} matches KERNELS_VERSION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
