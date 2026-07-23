# Development Log 0003 — Generic delimited parser (Phase 3)

- **Date:** 2026-07-23
- **Branch:** `feat/generic-delimited-parser` (based on the Phase 2 tip `b73bde0`)
- **Status:** Phase 3 complete. Generic CSV/TSV ingestion only.
- **Author:** Ron Finn

## 1. Objective

Implement a clean, typed, extensible ingestion layer that identifies and loads
generic CSV/TSV radial-scan data into the canonical `AUCExperiment`, exposed as
`openauc.load(path)`. Preserve raw values and order; never interpolate, resample,
infer units from values, or invent metadata; represent missing/unknown metadata
explicitly; and produce clear errors for ambiguous or malformed input.

## 2. Accepted decisions

- Base branch created from the Phase 2 tip `b73bde0` (Phase 2 was not on `main`).
- **SHA-256 checksum computation stays deferred to Phase 6** (ADR-0003);
  `ImportProvenance.sha256` is `None`. No ADR amendment.
- **No CLI** command this phase; format discovery is the Python
  `openauc.available_formats()`.
- Parser registry per ADR-0004 (decorator registration; confidence detection;
  entry-point discovery deferred).

## 3. Parser architecture

`src/openauc/formats/`:

| Module | Responsibility |
|--------|----------------|
| `base.py` | `Parser` ABC; `Table`, `ResolvedSource`, `DetectionResult`, `ParseResult`, `FormatInfo`. |
| `registry.py` | `@register_parser`, `get_parser`, `available_formats`, `detect_parser` (min-confidence 0.5, tie-margin 0.15). |
| `manifest.py` | Pydantic v2 `GenericManifest` (+ sub-models) and `load_manifest` (JSON/YAML). |
| `generic_delimited.py` | `GenericLongParser`, `GenericWideParser` and shared metadata assembly. |
| `loader.py` | `load()`, source resolution, delimiter detection, table reading, parser selection, provenance. |

`openauc.load` and `openauc.available_formats` are exposed at the package top
level and re-exported from `openauc.api`.

## 4. Manifest schema

Schema version `1.0`. Required: `schema_version`, `data_file`, `experiment`
(with `experiment_id`). Optional: `format`, `instrument`, `samples`, `defaults`,
`columns` (wide), `delimiter`, `notes`, `extension`. Unknown top-level keys are
rejected (`extra="forbid"`) except the documented `extension` object. `data_file`
must be a safe relative path (absolute, `..`, and drive-letter forms rejected).
The machine-readable schema is `schemas/generic-manifest-v1.schema.json`, kept in
sync with the model by `tests/unit/test_schema_consistency.py`.

## 5. Long and wide input contracts

- **Long:** required `scan`, `radius_cm`, `signal`; optional `elapsed_seconds`,
  `acquisition_timestamp`, `cell`, `channel`, `wavelength_nm`, `optical_system`,
  `signal_unit`, `rotor_speed_rpm`, `temperature_c`, `source_scan_id`. One row per
  observation; rows grouped by `scan` in first-appearance order; radius order
  preserved.
- **Wide:** first/declared radius column plus one signal column per scan, mapped
  by the manifest `columns` block; shares one radius axis.

Units are canonical (`radius_cm`→cm, `elapsed_seconds`→s, `wavelength_nm`→nm,
`rotor_speed_rpm`→rpm, `temperature_c`→°C); `signal_unit` accepts a `Unit` value
or name. No unit inference or conversion.

## 6. Detection rules

Selection precedence: explicit `format=` → manifest `format` → detection.
`generic-long` is confident (0.8, or 0.95 with a matching manifest) when the
required columns are present; `generic-wide` requires a manifest column mapping.
Delimiter detection is deterministic (manifest declaration, then per-delimiter
field-count consistency, then suffix tie-break); genuine ambiguity raises
`AmbiguousFormatError`. Extension alone is never trusted; no arbitrary guessing.

## 7. Conflict behaviour

- Duplicate `(scan, radius_cm)` (long) or duplicate radius (wide) →
  `DataConflictError`.
- A per-scan optional column with inconsistent values within one scan →
  `DataConflictError`.
- Table metadata vs manifest default disagreement (including `signal_unit`) →
  `DataConflictError` (never a silent override).
- Multiple `signal_unit` values in one file → `DataConflictError`.
- An explicitly-supplied data-file path that does not match the manifest's
  `data_file` → `DataConflictError`.

## 8. Shared vs per-scan radius construction

Long format builds **shared-axis** observations when every scan has an identical
radius vector (same values, same order); otherwise **per-scan-axis** observations
using the Phase 2 padded-array-plus-mask representation. Wide format is always
shared-axis. No interpolation onto a common grid ever occurs.

## 9. Provenance behaviour

Each load attaches `ImportProvenance`: `parser_name` (format id),
`parser_version` (`openauc.__version__`), `source_path`/`source_filename` (data
file), `imported_at` (UTC), `warnings`, and `assumptions` (unit interpretation,
resolved signal unit, radius-axis mode, and the manifest + data-file names).
`sha256` is `None` (deferred to Phase 6). Manifest and data paths are currently
recorded in `assumptions`; a dedicated provenance field is a candidate future
amendment (see §13).

## 10. Tests added

`tests/unit/`: `test_manifest.py`, `test_registry.py`, `test_schema_consistency.py`.
`tests/integration/`: `test_generic_delimited.py`, `test_ingestion_edges.py`.
Synthetic fixtures under `tests/fixtures/generic_delimited/` (valid long/wide
CSV/TSV, non-uniform per-scan, matching JSON+YAML manifests, detection,
ambiguous, conflict, and malformed cases). All 28 required scenarios are covered,
including order preservation, no-silent-sort, provenance, `to_dict` round-trip,
and clear error messages. **126 tests pass**; new-module coverage ≥ 90%.

## 11. Commands run

```
uv sync --all-groups
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=openauc --cov-report=term-missing
uv build
git diff --check
```

## 12. Known limitations

- One `signal_unit` per file (per the Phase 2 `Observations` limitation).
- Wide format is shared-axis only.
- No vendor/instrument formats, AUCX I/O, plotting, CLI, or scientific QC.
- Reading uses the standard library's line/split parsing rather than pandas;
  pandas remains a declared dependency reserved for later tabular needs. This
  keeps error locations precise (row/column) and typing clean.
- Third-party entry-point parser discovery is not enabled yet.

## 13. Rejected alternatives

- **pandas for reading** — rejected for this phase in favour of stdlib parsing
  for precise per-row/column errors and clean strict typing; revisit if richer
  tabular handling is needed.
- **Interpolating ragged scans to a shared grid** — rejected (violates the
  no-silent-transform boundary); per-scan observations are used instead.
- **Silent manifest choice when both JSON and YAML are present** — rejected;
  raises `AmbiguousFormatError`.
- **Computing SHA-256 now** — rejected to honour the accepted Phase 6 deferral.

## 14. Licensing considerations

Independent, clean-room implementation. No vendor format logic and no third-party
code. All fixtures are synthetic and safe to redistribute. No bundled binaries.

## 15. Next steps

Phase 4 — validation and scan summaries built on these imports; and the minimum
analysis-level metadata question (Q3). A future amendment could add explicit
manifest/data-path fields to `ImportProvenance`, and enable third-party
entry-point parser discovery once the interface is stable.
