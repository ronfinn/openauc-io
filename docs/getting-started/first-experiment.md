# Your first experiment

**Goal:** load radial-scan data you already have, as CSV or TSV.

**Prerequisites:** [Installation](installation.md), and a CSV/TSV file of
radial scans.

## What openauc needs from you

Two files in one directory:

```text
my-experiment/
├── manifest.json     # who the experiment is, and how to read the data file
└── scans.csv         # the numbers
```

The **manifest** exists because a CSV alone cannot say what the experiment is,
what the units are, or which optical system was used — and openauc will
never guess. See [Create a manifest](../how-to/create-a-manifest.md).

## A complete worked example

Create a directory called `my-experiment`. Put this in `my-experiment/scans.csv`:

```csv title="my-experiment/scans.csv"
scan,radius_cm,signal,elapsed_seconds
scan_001,5.90,0.012,0
scan_001,5.92,0.018,0
scan_001,5.94,0.041,0
scan_001,5.96,0.092,0
scan_002,5.90,0.008,600
scan_002,5.92,0.011,600
scan_002,5.94,0.024,600
scan_002,5.96,0.067,600
```

And this in `my-experiment/manifest.json`:

```json title="my-experiment/manifest.json"
{
  "schema_version": "1.0",
  "format": "generic-long",
  "data_file": "scans.csv",
  "experiment": {
    "experiment_id": "my-first-experiment",
    "name": "First run",
    "experiment_type": "sedimentation_velocity"
  },
  "defaults": {
    "optical_system": "absorbance",
    "signal_unit": "absorbance_unit"
  }
}
```

## Load it

From the directory containing `my-experiment`:

```python
import openauc

experiment = openauc.load("my-experiment")
print(experiment.summary())
```

Expected first lines:

```text
Experiment: my-first-experiment - First run
  Type: sedimentation_velocity
  Acquired: unknown
  Operator: unknown
  Scans: 2
  Samples: 0
  Optical systems: absorbance
  Radius axis: shared
```

Or from the shell:

```bash
uv run openauc inspect my-experiment
```

## Check it

```python
report = experiment.validate_structure()
print(report)  # 'structural validation: OK (no issues)'
print(report.is_valid)  # True
```

`is_valid` being `True` means the scans and observations correspond
unambiguously and are internally consistent. It is **not** a statement that
your experiment is scientifically sound — see
[Validation tiers](../concepts/validation-tiers.md).

## What openauc did, and did not, do

- **Preserved** your row order and radius values exactly. Nothing was sorted,
  resampled or interpolated.
- **Retained** the units you declared. Nothing was converted.
- **Recorded** that `Acquired` and `Operator` are unknown, rather than inventing
  values.
- **Computed** a SHA-256 checksum of both files, recorded in provenance.

## Common failure modes

| Error | Cause | Fix |
|-------|-------|-----|
| `ManifestError: no manifest found in ...` | No `manifest.json`/`manifest.yaml` in the directory | Add one — see [Create a manifest](../how-to/create-a-manifest.md) |
| `ParseError: declared data_file not found` | `data_file` names a file that is not there | Check the filename matches exactly |
| `ParseError: missing required column` | Long format needs `scan`, `radius_cm`, `signal` | Rename your columns, or use [wide format](../tutorials/load-generic-wide.md) |
| `DataConflictError` | The table and the manifest disagree about a value | Remove the duplicate declaration — openauc never silently picks one |

Full list: [Troubleshooting](../how-to/troubleshooting.md).

## Next step

- Your scans have different radius axes? [Per-scan radius axes](../how-to/per-scan-radius-axes.md)
- One column per scan instead of one row per point? [Load generic-wide data](../tutorials/load-generic-wide.md)
- Archive it: [Export and reload AUCX](../tutorials/export-and-reload-aucx.md)
