"""Run every gate a release must pass, in one command.

Usage::

    uv run python scripts/release_check.py

Each step is run to completion and reported; the script exits non-zero if any
step failed. It builds nothing and publishes nothing: see
``scripts/verify_artifacts.py`` for the artifact checks that follow ``uv build``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("types", ("uv", "run", "mypy")),
    ("tests", ("uv", "run", "pytest")),
    ("docs", ("uv", "run", "mkdocs", "build", "--strict")),
)


def main() -> int:
    failed: list[str] = []
    for name, command in STEPS:
        print(f"\n=== {name}: {' '.join(command)}", flush=True)
        if subprocess.run(command, cwd=ROOT, check=False).returncode != 0:
            failed.append(name)

    print("\n=== summary")
    for name, _ in STEPS:
        print(f"{'FAIL' if name in failed else 'PASS'}  {name}")

    if failed:
        print(f"\n{len(failed)} step(s) failed: {', '.join(failed)}")
        return 1
    print("\nAll release checks passed. Nothing was built, tagged or published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
