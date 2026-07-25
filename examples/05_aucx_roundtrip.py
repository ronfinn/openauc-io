"""Example 5 — export to AUCX and read it back.

An archive round-trips the canonical model exactly. Every checksum is verified
before a model is constructed. Checksums establish integrity, not authenticity.

Run: ``python examples/05_aucx_roundtrip.py``
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import openauc

DATA = Path(__file__).parent / "data" / "demo_experiment"


def main() -> None:
    experiment = openauc.load(DATA)

    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "demo.aucx"
        experiment.export(archive)
        print(f"wrote {archive.name} ({archive.stat().st_size} bytes)")

        info = openauc.inspect_aucx(archive)
        print(f"  format version: {info.aucx_format_version}")
        print(f"  radius mode:    {info.radius_axis_mode.value}")
        print(f"  scans:          {info.n_scans}")
        print(f"  members:        {', '.join(info.members)}")
        print(f"  verified:       {info.checksum_verified}")

        report = openauc.validate_aucx(archive)
        print(f"  integrity:      {'OK' if report.is_valid else 'FAILED'}")

        restored = openauc.load(archive)
        assert restored.to_dict() == experiment.to_dict()
        print("  round trip:     identical to the original model")

        # A restored archive is a full experiment again.
        print(f"  restored valid: {restored.validate().is_valid}")


if __name__ == "__main__":
    main()
