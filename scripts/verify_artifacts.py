"""Verify built distributions against the declared package version.

Usage::

    uv build
    uv run python scripts/verify_artifacts.py [DIST_DIR]

Checks that ``dist/`` holds exactly one wheel and one sdist, that both carry the
version declared in ``src/openauc/__init__.py``, that ``CITATION.cff`` agrees,
and that the wheel contains every subpackage plus the ``py.typed`` marker.

If the environment names a tag (``GITHUB_REF`` of the form ``refs/tags/...``),
the tag must be ``v<version>``. This script publishes nothing.
"""

from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WHEEL_ENTRIES = (
    "openauc/py.typed",
    "openauc/api.py",
    "openauc/cli.py",
    "openauc/models/__init__.py",
    "openauc/formats/__init__.py",
    "openauc/formats/aucx.py",
    "openauc/plotting/__init__.py",
    "openauc/synthetic/__init__.py",
)


def declared_version() -> str:
    source = (ROOT / "src" / "openauc" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', source, flags=re.MULTILINE)
    if match is None:  # pragma: no cover - defensive
        raise SystemExit("could not find __version__ in src/openauc/__init__.py")
    return match.group(1)


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main(argv: list[str]) -> int:
    dist = Path(argv[1]) if len(argv) > 1 else ROOT / "dist"
    version = declared_version()
    errors: list[str] = []

    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    check(errors, len(wheels) == 1, f"expected exactly one wheel, found {wheels}")
    check(errors, len(sdists) == 1, f"expected exactly one sdist, found {sdists}")

    expected_wheel = f"openauc-{version}-py3-none-any.whl"
    expected_sdist = f"openauc-{version}.tar.gz"
    if wheels:
        check(
            errors,
            wheels[0].name == expected_wheel,
            f"wheel is {wheels[0].name}, expected {expected_wheel}",
        )
    if sdists:
        check(
            errors,
            sdists[0].name == expected_sdist,
            f"sdist is {sdists[0].name}, expected {expected_sdist}",
        )

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    check(
        errors,
        f"version: {version}" in citation,
        f"CITATION.cff does not declare version {version}",
    )

    if wheels:
        try:
            with zipfile.ZipFile(wheels[0]) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile:
            errors.append(f"{wheels[0].name} is not a readable wheel")
        else:
            for entry in REQUIRED_WHEEL_ENTRIES:
                check(errors, entry in names, f"wheel is missing {entry}")

    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/"):
        tag = ref.removeprefix("refs/tags/")
        check(errors, tag == f"v{version}", f"tag {tag} does not match v{version}")

    if errors:
        for error in errors:
            print(f"FAIL  {error}")
        return 1

    print(f"PASS  distributions for {version} verified in {dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
