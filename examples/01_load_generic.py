"""Example 1 — load a generic delimited experiment.

Run: ``python examples/01_load_generic.py``
"""

from __future__ import annotations

from pathlib import Path

import openauc

DATA = Path(__file__).parent / "data" / "demo_experiment"


def main() -> None:
    experiment = openauc.load(DATA)

    print(f"loaded {experiment.metadata.experiment_id!r}")
    print(f"  scans:       {len(experiment.scans)}")
    print(f"  radius axis: {experiment.observations.mode.value}")
    print(f"  signal unit: {experiment.observations.signal_unit.value}")

    # Values and their order are preserved exactly; nothing is interpolated.
    radius, signal = experiment.observations.scan_vectors("scan_001")
    print(f"  first scan:  {len(radius)} points, r = {radius[0]:g}..{radius[-1]:g} cm")
    print(f"               signal[0] = {signal[0]:g}")

    # Which formats this build can read:
    for info in openauc.available_formats():
        print(f"  format:      {info.format_id} ({info.name})")


if __name__ == "__main__":
    main()
