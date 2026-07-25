"""Example 6 — the same workflow from the command line.

Equivalent shell commands::

    openauc formats
    openauc inspect  examples/data/demo_experiment
    openauc validate examples/data/demo_experiment --readiness
    openauc convert  examples/data/demo_experiment demo.aucx
    openauc validate demo.aucx

Exit codes: 0 success, 1 structural validation failed, 2 input error,
3 output exists.

Run: ``python examples/06_cli_usage.py``
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

DATA = Path(__file__).parent / "data" / "demo_experiment"


def run(*args: str) -> int:
    printable = " ".join(("openauc", *args))
    print(f"\n$ {printable}")
    result = subprocess.run(
        [sys.executable, "-m", "openauc.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in (result.stdout or result.stderr).splitlines()[:12]:
        print(f"  {line}")
    print(f"  [exit {result.returncode}]")
    return result.returncode


def main() -> None:
    run("version")
    run("formats")
    run("inspect", str(DATA))
    run("validate", str(DATA), "--readiness")
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "demo.aucx"
        run("convert", str(DATA), str(archive))
        run("validate", str(archive))
        # Refusing to overwrite is exit code 3.
        code = run("convert", str(DATA), str(archive))
        assert code == 3, code


if __name__ == "__main__":
    main()
