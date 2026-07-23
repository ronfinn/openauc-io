# Generic delimited formats (CSV / TSV)

Phase 3 ingests **generic** delimited radial-scan data — plain CSV or TSV with no
vendor-specific conventions — into the canonical
[`AUCExperiment`](../concepts/data-model.md). Two layouts are supported:
`generic-long` and `generic-wide`. A [manifest](manifest-v1.md) supplies
experiment identity and metadata.

> This is **not** a vendor format reader. Beckman XL-A/XL-I, Optima AUC, OpenAUC,
> SEDFIT/SEDPHAT native files and AUCX archives are **not** supported here; they
> remain future parser plugins.

## Loading

```python
import openauc

experiment = openauc.load("path/to/experiment")     # a directory
experiment = openauc.load("path/to/experiment/scans.csv")   # a data file
experiment = openauc.load("path/to/experiment", format="generic-long")
experiment = openauc.load("dir", manifest="dir/manifest.json")

print(experiment.summary())
print(experiment.validate_structure())
```

`load` resolves a directory to its manifest and data file, or a data-file path to
an adjacent manifest. It does **not** search directory trees recursively.

## Long format (`generic-long`)

One row per radial observation.

**Required columns:** `scan`, `radius_cm`, `signal`.

**Optional columns:** `elapsed_seconds`, `acquisition_timestamp`, `cell`,
`channel`, `wavelength_nm`, `optical_system`, `signal_unit`, `rotor_speed_rpm`,
`temperature_c`, `source_scan_id`.

```csv
scan,radius_cm,signal,elapsed_seconds
scan_001,5.90,0.012,0
scan_001,5.91,0.014,0
scan_002,5.90,0.010,600
scan_002,5.91,0.011,600
```

Rules:

- Each `scan` value groups the rows of one radial vector.
- **Row and radius order are preserved** — data is never sorted.
- If every scan shares an identical radius vector, **shared-axis** observations
  are built; otherwise **per-scan-axis** observations are built (with the
  authoritative validity mask from Phase 2). **No interpolation onto a common
  grid.**
- A duplicate `(scan, radius_cm)` pair is a `DataConflictError`.
- Non-finite or non-numeric `radius_cm`/`signal` is a `ParseError`.
- A per-scan optional column with inconsistent values within one scan is a
  `DataConflictError`.
- Optional scan metadata may come from the table or the manifest defaults; if
  both supply it and they differ, that is a `DataConflictError` (never silently
  resolved).

## Wide format (`generic-wide`)

One radius column and one signal column per scan. In Phase 3, wide format
represents scans that **share one radius axis**.

```csv
radius_cm,scan_001,scan_002,scan_003
5.90,0.012,0.010,0.011
5.91,0.014,0.011,0.012
```

The manifest's [`columns`](manifest-v1.md#wide-format-columns) block declares the
radius column, each signal column, its scan id, and optional per-scan metadata.
Metadata is **never** inferred from column-name conventions.

## Units

`radius_cm` is centimetres; `elapsed_seconds` is seconds; `wavelength_nm` is
nanometres; `rotor_speed_rpm` is rpm; `temperature_c` is °C. `signal_unit`
accepts a `Unit` value (`AU`, `fringe`, …) or name (`absorbance_unit`). Units are
**retained, never inferred from values and never converted**. See
[units](../concepts/units.md).

## Delimiter detection

See [parser detection](parser-detection.md). CSV and TSV are supported; the
delimiter is resolved from the manifest declaration, the file suffix and header
consistency — never by arbitrary guessing.

## Provenance

Each load attaches an [`ImportProvenance`](../api.md) record: parser id and
version, source and manifest/data paths, an import timestamp, warnings and
assumptions. **Checksums are not computed in Phase 3** — SHA-256 remains deferred
to Phase 6 (ADR-0003), so `sha256` is `None`.
