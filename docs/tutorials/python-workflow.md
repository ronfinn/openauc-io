# Complete Python workflow

**Goal:** work through every public method on `AUCExperiment`, understanding
what each returns and why it exists.

**Prerequisites:** [Installation](../getting-started/installation.md). Commands
run **from the repository root**, using the repository's own demo data at
`examples/data/demo_experiment`.

A runnable condensation of this page lives at
[`examples/02_inspect_summary.py`](https://github.com/ronfinn/openauc-io/blob/main/examples/02_inspect_summary.py).

## 1. Import

```python
import openauc
```

`import openauc` is deliberately light — it does **not** pull in matplotlib.
Plotting is imported separately when you need it.

## 2. Load a directory of CSV/TSV data

```python
experiment = openauc.load("examples/data/demo_experiment")
```

`openauc.load` returns an **`AUCExperiment`**: the canonical in-memory model. It
accepts an experiment directory, a data file with an adjacent manifest, a
manifest file, or an `.aucx` archive.

## 3. Load an AUCX archive

Identical call — dispatch is on the suffix:

```python
archived = openauc.load("demo.aucx")
```

or force it:

```python
archived = openauc.load("some-file", format="aucx")
```

Every checksum is verified **before** a model is constructed.

## 4. `summary()` → `str`

```python
print(experiment.summary())
```

A human-readable structural description: identity, counts, units, ranges,
metadata presence, provenance, validation counts. It ends with an explicit
statement that no scientific claim is made.

## 5. `summary_data()` → `ExperimentSummary`

```python
summary = experiment.summary_data()

summary.n_scans  # int
summary.total_valid_observations  # int
summary.points_per_scan  # tuple[int, ...]
summary.radius.render()  # '5.9 to 7.2 cm (observed)'
summary.elapsed_time.minimum  # float | None
summary.to_dict()  # JSON-friendly dict
```

A **frozen** pydantic model. Every collection is a tuple; there are no mutable
fields. `summary()` is exactly `summary_data().to_text()`.

Metadata absence is *counted*, never defaulted:

```python
for entry in summary.metadata_presence:
    if entry.unrecorded:
        print(entry.component, entry.field, entry.unrecorded, "of", entry.total)
```

## 6. `validate_structure()` → `ValidationReport`

```python
report = experiment.validate_structure()
report.is_valid  # bool — True when there are no ERROR findings
report.errors  # tuple[ValidationIssue, ...]
report.warnings
```

Returns the **`ARCHIVAL`** and **`STRUCTURAL`** findings of `ERROR` or
`WARNING` severity. It never raises.

## 7. `validate()` → `ValidationReport`

```python
full = experiment.validate()
full.counts()  # (errors, warnings, infos)
full.codes()  # ('cell_absent', 'rotor_speed_absent', ...)
```

The superset: all four tiers, all severities, including informational findings.

## 8. Filtering findings

```python
from openauc.models import ValidationSeverity, ValidationTier

full.by_code("rotor_speed_absent")  # tuple of matching issues
full.for_tiers(ValidationTier.SV_READINESS)  # a narrowed report
full.blocking_for(ValidationTier.SV_READINESS)  # what prevents that tier
full.for_tiers(
    ValidationTier.STRUCTURAL,
    severities=(ValidationSeverity.ERROR,),
)
```

Each `ValidationIssue` carries `code`, `severity`, `tiers`, `blocks`,
`message`, `observed`, `expected`, `remediation`, `component`, `location` and
`scan_ids`. `issue.describe()` renders all of it:

```python
for issue in full.warnings:
    print(issue.describe())
```

## 9. `assess_readiness()` → `ReadinessAssessment`

```python
assessment = experiment.assess_readiness()
sv = assessment.sedimentation_velocity
sv.status  # ReadinessStatus
sv.is_blocked  # bool
sv.blocking_issues  # findings that prevent this tier
sv.advisory_issues  # findings that pertain to it but block nothing
```

## 10. Reading the four statuses

| Status | Meaning |
|--------|---------|
| `POTENTIALLY_READY` | Every metadata prerequisite is **present**. Nothing is claimed about the data. |
| `BLOCKED` | A prerequisite is absent, or a structural error prevents assessment. |
| `NOT_APPLICABLE` | The declared experiment type says this workflow does not apply. |
| `NOT_ASSESSED` | Not evaluated — and, for scientific suitability, never will be. |

```python
assessment.scientific_suitability.status  # always NOT_ASSESSED
```

That entry is a constant. It is never derived from any finding.

## 11. Reading the numbers

```python
radius, signal = experiment.observations.scan_vectors("scan_001")
# both numpy float64 arrays, padding excluded, stored order preserved

for scan_id, radius, signal in experiment.observations.iter_scan_vectors():
    print(scan_id, len(radius))
```

In shared-axis mode every scan returns the same radius array; in per-scan mode
each returns its own. Nothing is sorted or resampled.

Other accessors:

```python
experiment.observations.mode  # RadiusAxisMode.SHARED | PER_SCAN
experiment.observations.scan_ids  # tuple[str, ...]
experiment.observations.points_per_scan()  # tuple[int, ...]
experiment.observations.radius_range()  # (min, max) | None
```

## 12. Plotting

```python
from openauc.plotting import plot_scan, plot_scans

ax = plot_scans(experiment)  # all scans overlaid
ax = plot_scans(experiment, scan_ids=["scan_001", "scan_002"])
ax = plot_scan(experiment, "scan_001")  # exactly one
```

Both return a `matplotlib.axes.Axes`. matplotlib loads on the first draw.

## 13. Saving without a display

```python
ax = plot_scans(experiment)
ax.figure.savefig("scans.png", dpi=150, bbox_inches="tight")
```

`pyplot` is never used, so no backend or display is required. To show a window,
create your own axes and pass them in:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
plot_scans(experiment, ax=ax)
plt.show()
```

## 14. Export to AUCX

```python
path = experiment.export("demo.aucx")  # refuses to overwrite
path = experiment.export("demo.aucx", overwrite=True)
```

Writes atomically: a temporary sibling file is written, verified in full, then
moved into place. Also available as `openauc.export_aucx(experiment, path)`.

## 15. Reload

```python
restored = openauc.load("demo.aucx")
```

## 16. Compare

```python
assert restored.to_dict() == experiment.to_dict()
```

AUCX round-trips the canonical model **exactly** — both radius modes, masks,
dtypes, units, and all four value statuses.

!!! note "CSV cannot promise this"
    Generic delimited output cannot express "explicitly unknown" as distinct
    from "missing", so exact dict equality is an AUCX property only. See
    [Missing and unknown metadata](../how-to/missing-and-unknown-metadata.md).

## 17. Handling exceptions

Everything derives from `OpenAUCError`:

```python
from openauc.exceptions import (
    OpenAUCError,
    ManifestError,
    ParseError,
    DataConflictError,
    ArchiveError,
    ArchiveIntegrityError,
    ArchiveVersionError,
    PlottingError,
    StructuralValidationError,
)

try:
    experiment = openauc.load("some-directory")
except ManifestError as exc:
    print("manifest problem:", exc)
except ParseError as exc:
    print("data problem:", exc)
except OpenAUCError as exc:
    print("openauc:", exc)
```

Validation never raises — unless you ask it to:

```python
experiment.validate_structure().raise_if_invalid()  # StructuralValidationError
```

## Next step

- [Validate an experiment](validate-an-experiment.md)
- [Export and reload AUCX](export-and-reload-aucx.md)
- [Recipes](../how-to/recipes.md)
