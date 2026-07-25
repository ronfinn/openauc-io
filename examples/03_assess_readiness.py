"""Example 3 — assess analysis readiness without claiming scientific validity.

Readiness reports whether the metadata a future workflow would need is present.
It never inspects the signal and never judges the science. Scientific
suitability is permanently reported as NOT_ASSESSED.

Run: ``python examples/03_assess_readiness.py``
"""

from __future__ import annotations

from pathlib import Path

import openauc

DATA = Path(__file__).parent / "data" / "demo_experiment"


def main() -> None:
    experiment = openauc.load(DATA)
    assessment = experiment.assess_readiness()

    for entry in assessment.entries:
        print(f"{entry.analysis.value}: {entry.status.value}")
        if entry.note:
            print(f"  note: {entry.note}")
        for issue in entry.blocking_issues:
            print(f"  blocking: {issue.code} - {issue.message}")
        for issue in entry.advisory_issues:
            print(f"  advisory: {issue.code} - {issue.message}")

    # This is always true, for every experiment, forever.
    scientific = assessment.scientific_suitability
    assert scientific.status.value == "not_assessed"
    print("\nopenauc does not assess scientific validity, and never will.")


if __name__ == "__main__":
    main()
