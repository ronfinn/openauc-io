# Load generic-wide data

**Goal:** read data where **each scan is a column**, sharing one radius column.

**Prerequisites:** [Installation](../getting-started/installation.md).

## The data file

```csv title="wide-example/scans.csv"
radius_cm,scan_001,scan_002,scan_003
5.90,0.0120,0.0080,0.0055
5.92,0.0185,0.0110,0.0075
5.94,0.0410,0.0240,0.0160
5.96,0.0925,0.0670,0.0450
5.98,0.1840,0.1510,0.1190
```

## The manifest

Wide format **requires** an explicit column mapping. Metadata is never inferred
from column-name conventions.

```json title="wide-example/manifest.json"
{
  "schema_version": "1.0",
  "format": "generic-wide",
  "data_file": "scans.csv",
  "experiment": {
    "experiment_id": "wide-example-001",
    "name": "Wide-format example",
    "experiment_type": "sedimentation_velocity"
  },
  "defaults": {
    "optical_system": "absorbance",
    "signal_unit": "absorbance_unit"
  },
  "columns": {
    "radius": "radius_cm",
    "scans": [
      {"column": "scan_001", "scan_id": "scan_001", "elapsed_seconds": 0},
      {"column": "scan_002", "scan_id": "scan_002", "elapsed_seconds": 600},
      {"column": "scan_003", "scan_id": "scan_003", "elapsed_seconds": 1200}
    ]
  }
}
```

Each entry in `columns.scans` maps one data column to one scan and may carry
`elapsed_seconds`, `wavelength_nm`, `optical_system`, `rotor_speed_rpm`,
`temperature_c`, `cell`, `channel` and `source_scan_id`.

## Load it

```python
import openauc

experiment = openauc.load("wide-example")
print(experiment.observations.mode)  # RadiusAxisMode.SHARED
print(experiment.validate_structure())  # structural validation: OK (no issues)
```

## Why wide is shared-axis only

A wide table has **one** radius column, so by construction every scan is read
against the same radial positions. That is the format's defining property, not a
limitation of the reader.

It follows that an experiment whose scans have *different* radius vectors
**cannot** be written wide without placing them on a common grid — which means
interpolating or resampling measured data.

**`openauc` refuses rather than resamples.**

```python
from openauc.synthetic import (
    SyntheticExperimentConfig,
    generate_experiment,
    write_generic_wide,
)

ragged = generate_experiment(
    SyntheticExperimentConfig(scenario="per-scan-radius", n_scans=4)
)
write_generic_wide(ragged, "out/wide")
```

```text
SyntheticWriteError: wide layout needs one shared radius axis, but this
experiment uses 'per_scan' axes. Writing it wide would require resampling onto
a common grid, which openauc never does; use write_generic_long or write_aucx
instead.
```

This follows [ADR-0002](../project/decisions.md): any operation placing per-scan
data onto a common grid must be an explicit, opt-in, recorded transformation.
No such operation exists in the library today.

Use [generic-long](load-generic-long.md) or [AUCX](export-and-reload-aucx.md)
for ragged data — both represent per-scan axes natively.

## Common failure modes

| Error | Cause | Fix |
|-------|-------|-----|
| `ManifestError` / missing `columns` | Wide format needs a column mapping | Add the `columns` block |
| `ParseError: missing required column` | A mapped column is absent | Check the header matches `column` values exactly |
| `DataConflictError: duplicate radius` | Repeated values in the radius column | Deduplicate at source |
| `SyntheticWriteError: wide layout needs one shared radius axis` | Ragged data | Use long or AUCX |

## Next step

- [Load generic-long data](load-generic-long.md)
- [Per-scan radius axes](../how-to/per-scan-radius-axes.md)
