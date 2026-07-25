"""Example 2 — inspect the structured summary and validation findings.

Summaries and validation describe structure and metadata only. They make no
claim about scientific validity or suitability for analysis.

Run: ``python examples/02_inspect_summary.py``
"""

from __future__ import annotations

from pathlib import Path

import openauc

DATA = Path(__file__).parent / "data" / "demo_experiment"


def main() -> None:
    experiment = openauc.load(DATA)

    print(experiment.summary())
    print()

    summary = experiment.summary_data()
    print(f"total observations: {summary.total_valid_observations}")
    print(f"points per scan:    {summary.points_per_scan}")
    print(f"elapsed time:       {summary.elapsed_time.render()}")
    print(f"radius:             {summary.radius.render()}")

    # Absence is counted explicitly, never defaulted.
    for entry in summary.metadata_presence:
        if entry.unrecorded:
            print(
                f"unrecorded: {entry.component}.{entry.field} "
                f"({entry.unrecorded}/{entry.total})"
            )

    report = experiment.validate()
    errors, warnings, infos = report.counts()
    print(f"\nfindings: {errors} error(s), {warnings} warning(s), {infos} info")
    for issue in report.issues:
        print(f"  {issue.describe()}")

    print(f"\nstructurally valid: {experiment.validate_structure().is_valid}")


if __name__ == "__main__":
    main()
