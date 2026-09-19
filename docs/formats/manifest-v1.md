# Experiment manifest (schema version 1.0)

A manifest declares which data file to read, its format, experiment identity, and
optional instrument/sample/default metadata. **JSON is canonical**; **YAML** is
accepted as an authoring convenience. The machine-readable schema is
[`schemas/generic-manifest-v1.schema.json`](https://github.com/ronfinn/openauc-io/blob/main/schemas/generic-manifest-v1.schema.json),
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

## Sample links

`samples` declares the samples; a scan is linked to one by its `sample_id`. The
link is stated, never inferred. It can come from:

- `defaults.sample_id` — the author states once that every scan measured that
  sample;
- a per-scan `sample_id` (a data-table column in long format, or a `columns`
  entry in wide format).

A `sample_id` that names no declared sample is rejected: in `defaults` or in a
wide `columns` entry as a `ManifestError`, in a long-format data column as a
`ParseError`. A data value that differs from `defaults.sample_id` is a
`DataConflictError`. **A scan with no stated link stays unlinked, even when the
manifest declares only one sample.**

## Acquisition timestamps

`experiment.acquired_at` (when the run was acquired) and, per scan,
`acquisition_timestamp` (wide `columns` entries, or the long-format data column)
take an ISO-8601 **date-time**:

- an explicit UTC offset (`2026-03-02T09:30:00+01:00`, or `Z`) is preserved
  exactly and never converted;
- a timestamp with no offset is accepted and kept **timezone-naive**, meaning
  "timezone not stated"; no zone is assumed;
- a date without a time of day (`2026-03-02`), a number (such as epoch seconds)
  or any other text is rejected — a time is never invented, for example by
  padding to midnight.

In YAML, quote a value or write a full date-time; an unquoted bare date is
rejected. The experiment time and the scan times are separate facts: neither is
derived from the other, or from `elapsed_seconds`. There is no timestamp
default, since one time for every scan is not a meaningful fact. Acquisition
time is distinct from the import time recorded in provenance.

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
(`elapsed_seconds`, `acquisition_timestamp`, `sample_id`, `wavelength_nm`,
`optical_system`, `rotor_speed_rpm`, `temperature_c`, `cell`, `channel`,
`source_scan_id`).

## Instrument and sample metadata

Instrument and sample fields use author-friendly, unit-suffixed scalars
(`nominal_speed_rpm`, `temperature_c`, `wavelength_nm`, `concentration_value`
with `concentration_unit`, …). The parser converts these into canonical
`Quantity` values with their declared units; it never infers a unit from a value.
