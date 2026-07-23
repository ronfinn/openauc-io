# Experiment manifest (schema version 1.0)

A manifest declares which data file to read, its format, experiment identity, and
optional instrument/sample/default metadata. **JSON is canonical**; **YAML** is
accepted as an authoring convenience. The machine-readable schema is
[`schemas/generic-manifest-v1.schema.json`](../../schemas/generic-manifest-v1.schema.json),
kept consistent with the Pydantic model by a test.

## Minimal example

```json
{
  "schema_version": "1.0",
  "format": "generic-long",
  "data_file": "scans.csv",
  "experiment": {
    "experiment_id": "synthetic-001",
    "name": "Synthetic absorbance run",
    "experiment_type": "sedimentation_velocity"
  },
  "defaults": {
    "optical_system": "absorbance",
    "signal_unit": "absorbance_unit",
    "cell": "1",
    "channel": "A"
  }
}
```

## Top-level fields

| Field | Required | Notes |
|-------|----------|-------|
| `schema_version` | yes | Must be `"1.0"`. Any other value is a `ManifestError`. |
| `data_file` | yes | Relative path to the data file. Absolute paths and paths escaping the experiment directory (`..`, drive letters) are rejected. |
| `experiment` | yes | Contains at least `experiment_id`. |
| `format` | no | `"generic-long"` or `"generic-wide"`. If omitted, the parser is chosen by detection. |
| `instrument` | no | Optional instrument/run metadata. |
| `samples` | no | Optional list of sample metadata. |
| `defaults` | no | Scan-level defaults (see below). |
| `columns` | no | Required for wide format (see below). |
| `delimiter` | no | `","`, `"\t"`, `"comma"` or `"tab"` — an explicit override. |
| `notes` | no | Free text, retained. |
| `extension` | no | A documented escape hatch object for forward-compatible extra data. |

Unknown top-level fields are **rejected** (`extra="forbid"`), except the
documented `extension` object.

## Defaults and conflicts

`defaults` supplies scan metadata where the table does not. A default that
**conflicts** with a value supplied in the table is an error
(`DataConflictError`), never a silent override.

## Missing vs unknown

Absent optional fields stay absent (`None`); the model does not invent values.
Where the canonical model distinguishes present / missing / unknown /
not-applicable, that distinction is preserved (for example, a scan with no
`elapsed_seconds` gets an explicitly *missing* elapsed time). See
[missing and unknown values](../concepts/missing-and-unknown-values.md).

## Wide-format `columns`

```json
"columns": {
  "radius": "radius_cm",
  "scans": [
    {"column": "scan_001", "scan_id": "scan_001", "elapsed_seconds": 0},
    {"column": "scan_002", "scan_id": "scan_002", "elapsed_seconds": 600}
  ]
}
```

Each entry maps a signal column to a scan id and optional per-scan metadata
(`elapsed_seconds`, `wavelength_nm`, `optical_system`, `rotor_speed_rpm`,
`temperature_c`, `cell`, `channel`, `source_scan_id`).

## Instrument and sample metadata

Instrument and sample fields use author-friendly, unit-suffixed scalars
(`nominal_speed_rpm`, `temperature_c`, `wavelength_nm`, `concentration_value`
with `concentration_unit`, …). The parser converts these into canonical
`Quantity` values with their declared units; it never infers a unit from a value.
