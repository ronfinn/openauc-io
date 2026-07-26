# Create a manifest

**Goal:** write the `manifest.json` that tells openauc what your CSV/TSV is.

**Prerequisites:** a delimited data file.

## Why a manifest exists

A CSV of numbers cannot say what the experiment is, what the signal unit is, or
which optical system was used. openauc **never guesses**, so that information
must be declared. JSON is canonical; YAML is accepted for authoring.

## The minimum that works

```json title="manifest.json"
{
  "schema_version": "1.0",
  "data_file": "scans.csv",
  "experiment": {
    "experiment_id": "my-experiment-001"
  }
}
```

Only `schema_version`, `data_file` and `experiment.experiment_id` are required.

## Every field

### Top level

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `schema_version` | `str` | **yes** | Must be `"1.0"`. Any other value is rejected. |
| `data_file` | `str` | **yes** | Relative path to the data file. Absolute paths, `..` and drive letters are rejected. |
| `experiment` | object | **yes** | Experiment identity — see below. |
| `format` | `str` | no | `"generic-long"` or `"generic-wide"`. Omit to use detection. |
| `instrument` | object | no | Instrument and run metadata. |
| `samples` | array | no | Sample and buffer metadata. |
| `defaults` | object | no | Scan-level values applied where the table does not supply them. |
| `columns` | object | **for wide** | Radius column and per-scan column mapping. |
| `delimiter` | `str` | no | `"comma"`, `"tab"`, or the literal character. |
| `notes` | `str` | no | Free text. |
| `extension` | object | no | The only permitted unknown-key container. |

Unknown top-level keys are **rejected** (`extra="forbid"`), except `extension`.
A typo fails loudly rather than being ignored.

### `experiment`

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `experiment_id` | `str` | **yes** | Non-empty identifier. |
| `name` | `str` | no | Display name. |
| `description` | `str` | no | Free text. |
| `experiment_type` | `str` | no | `sedimentation_velocity`, `sedimentation_equilibrium`, `other`, `unknown` (default). Drives readiness routing. |
| `operator` | `str` | no | Who ran it. |
| `notes` | `str` | no | Free text. |

```json
"experiment": {
  "experiment_id": "run-2026-03-14",
  "name": "Third replicate",
  "experiment_type": "sedimentation_velocity",
  "operator": "R. Finn"
}
```

### `instrument`

All optional: `manufacturer`, `model`, `serial_number`, `rotor_id`,
`nominal_speed_rpm` (float), `temperature_c` (float), `cell`, `channel`,
`centrepiece`, `optical_system`, `wavelength_nm` (float).

```json
"instrument": { "rotor_id": "AN-60 Ti", "nominal_speed_rpm": 45000, "temperature_c": 20.0 }
```

`nominal_speed_rpm` here satisfies the rotor-speed readiness check even when no
per-scan speed is recorded.

### `samples`

An array. Each entry needs `sample_id`; optionally `description`,
`buffer_description`, `concentration_value` + `concentration_unit`, `density`,
`viscosity`, `partial_specific_volume`, `notes`.

```json
"samples": [
  { "sample_id": "s1", "buffer_description": "PBS pH 7.4", "density": 1.005 }
]
```

!!! note "No sample-to-scan linkage"
    `ScanMetadata` carries no `sample_id`, so samples are experiment-wide.

### `defaults`

Applied where the table does not supply a value: `optical_system`,
`signal_unit`, `cell`, `channel`, `wavelength_nm`, `rotor_speed_rpm`,
`temperature_c`.

```json
"defaults": { "optical_system": "absorbance", "signal_unit": "absorbance_unit", "wavelength_nm": 280 }
```

!!! warning "A default is not an override"
    If the table **and** the defaults both supply a value and they differ, that
    is a `DataConflictError`. openauc never silently picks one.

### `columns` (wide format only)

```json
"columns": {
  "radius": "radius_cm",
  "scans": [
    {"column": "scan_001", "scan_id": "scan_001", "elapsed_seconds": 0}
  ]
}
```

Each entry needs `column` and `scan_id`; optionally `elapsed_seconds`,
`wavelength_nm`, `optical_system`, `rotor_speed_rpm`, `temperature_c`, `cell`,
`channel`, `source_scan_id`.

### `delimiter`

```json
{ "delimiter": "tab" }
```

Accepts `"comma"`, `"tab"`, or the character itself. Omit it and the delimiter
is resolved from field-count consistency then the file suffix; genuine
ambiguity raises `AmbiguousFormatError` rather than a guess.

## Absent, missing, unknown, not-applicable

The canonical model distinguishes four states. **A generic CSV manifest cannot
express all four.** Omitting a field yields *absent*; there is no manifest
syntax for "explicitly unknown".

If that distinction matters to you, **AUCX is the exact-preservation format** —
it round-trips all four. See
[Missing and unknown metadata](missing-and-unknown-metadata.md).

## Validating your manifest

```bash
uv run openauc inspect my-experiment
```

A malformed manifest fails with a specific message and exit code `2`.

There is also a machine-readable JSON Schema at
`schemas/generic-manifest-v1.schema.json`, kept in sync with the model by a test.

## Common failure modes

| Error | Cause |
|-------|-------|
| `ManifestError: unknown schema version` | `schema_version` is not `"1.0"` |
| `ManifestError: ... resolves outside the experiment directory` | `data_file` uses `..` or an absolute path |
| pydantic `extra_forbidden` | A misspelt key — put non-standard data under `extension` |
| `ParseError: declared data_file not found` | Filename mismatch |

## Next step

- [Load generic-long data](../tutorials/load-generic-long.md)
- [Manifest specification](../formats/manifest-v1.md)
