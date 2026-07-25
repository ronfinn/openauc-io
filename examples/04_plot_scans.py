"""Example 4 — plot the radial scans.

Plots render what is stored: no interpolation, resampling, sorting, smoothing or
fitting. Figures are built without pyplot, so this runs headless.

Run: ``python examples/04_plot_scans.py [output.png]``
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import openauc
from openauc.plotting import plot_scans

DATA = Path(__file__).parent / "data" / "demo_experiment"


def main() -> None:
    experiment = openauc.load(DATA)

    axes = plot_scans(experiment, marker=".")
    print(f"plotted {len(axes.lines)} scan(s)")
    print(f"  x axis: {axes.get_xlabel()}")
    print(f"  y axis: {axes.get_ylabel()}")

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path(tempfile.gettempdir()) / "openauc-example-scans.png"
    figure = axes.figure
    assert figure is not None
    figure.savefig(target, dpi=120, bbox_inches="tight")
    print(f"  wrote:  {target}")


if __name__ == "__main__":
    main()
