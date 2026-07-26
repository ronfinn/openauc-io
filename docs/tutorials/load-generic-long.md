# Load generic-long data

**Goal:** read radial-scan data where **each row is one radial observation**.

**Prerequisites:** [Installation](../getting-started/installation.md).

## Directory layout

```text
long-example/
├── manifest.json
└── scans.csv
```

Both files must sit in the same directory. `openauc` does not search
recursively.

## The data file

```csv title="long-example/scans.csv"
scan,radius_cm,signal,elapsed_seconds
scan_001,5.90,0.0120,0
scan_001,5.92,0.0185,0
scan_001,5.94,0.0410,0
scan_001,5.96,0.0925,0
scan_001,5.98,0.1840,0
scan_002,5.90,0.0080,600
scan_002,5.92,0.0110,600
scan_002,5.94,0.0240,600
scan_002,5.96,0.0670,600
scan_002,5.98,0.1510,600
scan_003,5.90,0.0055,1200
scan_003,5.92,0.0075,1200
scan_003,5.94,0.0160,1200
scan_003,5.96,0.0450,1200
scan_003,5.98,0.1190,1200
```

## The manifest

```json title="long-example/manifest.json"
{
  "schema_version": "1.0",
  "format": "generic-long",
  "data_file": "scans.csv",
  "experiment": {
    "experiment_id": "long-example-001",
    "name": "Long-format example",
    "experiment_type": "sedimentation_velocity",
    "operator": "example"
  },
  "instrument": {
    "manufacturer": "example",
    "rotor_id": "example-rotor",
    "nominal_speed_rpm": 45000,
    "temperature_c": 20.0
  },
  "defaults": {
    "optical_system": "absorbance",
    "signal_unit": "absorbance_unit",
    "cell": "1",
    "channel": "A",
    "wavelength_nm": 280
  },
  "notes": "Synthetic example data."
}
```

Declaring `"format": "generic-long"` is optional but recommended — it removes
any need for detection.

## Columns

**Required:** `scan`, `radius_cm`, `signal`.

**Optional:** `elapsed_seconds`, `acquisition_timestamp`, `cell`, `channel`,
`wavelength_nm`, `optical_system`, `signal_unit`, `rotor_speed_rpm`,
`temperature_c`, `source_scan_id`.

Column names carry their units: `radius_cm` is centimetres, `elapsed_seconds`
seconds, `wavelength_nm` nanometres, `rotor_speed_rpm` rpm, `temperature_c`
degrees Celsius. **Units are retained, never converted, never inferred from
values.**

## Load it

```python
import openauc

experiment = openauc.load("long-example")
print(experiment.summary())
```

```bash
uv run openauc inspect long-example
```

## The rules openauc follows

- **Each row is one radial observation.** The `scan` value groups rows into
  scans, in first-appearance order.
- **Stored order is preserved.** Rows are never sorted. A descending (inward)
  radius vector renders exactly as acquired.
- **Scans are never interpolated.** If every scan shares an identical radius
  vector, shared-axis observations are built; otherwise per-scan-axis
  observations are built, and each scan keeps its own axis.
- **Distinct radius axes stay distinct.** No regridding onto a common grid ever
  happens. See [Per-scan radius axes](../how-to/per-scan-radius-axes.md).
- **Conflicting metadata is an error, never a silent choice.** If the table and
  the manifest defaults both supply a value and they differ, that is a
  `DataConflictError`.
- **Duplicate `(scan, radius_cm)` pairs** raise `DataConflictError`.
- **Non-numeric or non-finite** `radius_cm`/`signal` raise `ParseError`.

## TSV

Identical, with tabs. Name the file `scans.tsv`; the delimiter is resolved from
the manifest declaration, then field-count consistency, then the suffix. Genuine
ambiguity raises `AmbiguousFormatError` rather than a guess. You can also
declare it:

```json
{ "delimiter": "tab" }
```

## Common failure modes

| Error | Cause | Fix |
|-------|-------|-----|
| `ParseError: missing required column` | No `scan`/`radius_cm`/`signal` | Rename your columns |
| `DataConflictError: ... in the data but ... in the manifest defaults` | Both declare a differing value | Remove one |
| `DataConflictError: duplicate` | Two rows share `(scan, radius_cm)` | Deduplicate at source |
| `ManifestError: data_file ... resolves outside` | `data_file` escapes the directory | Use a plain relative filename |
| `AmbiguousFormatError` | Comma and tab both parse consistently | Declare `"delimiter"` |

## Next step

- [Load generic-wide data](load-generic-wide.md)
- [Create a manifest](../how-to/create-a-manifest.md)
- [Format specification](../formats/generic-delimited.md)
