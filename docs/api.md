# API reference

The stable public surface is `openauc.api` (re-exported from the top-level
`openauc` package). The canonical model types are also importable from
`openauc.models`. Internal module paths are not part of the public contract.

## Ingestion (Phase 3)

```python
import openauc

experiment = openauc.load(path, *, format=None, manifest=None)  # -> AUCExperiment
openauc.available_formats()  # -> tuple[FormatInfo, ...]
```

`load` reads generic delimited (CSV/TSV) experiments via a manifest; see
[generic delimited](formats/generic-delimited.md), [manifest v1](formats/manifest-v1.md)
and [parser detection](formats/parser-detection.md). It attaches an
`ImportProvenance` record (parser id/version, source and manifest/data paths,
timestamp, warnings, assumptions; `sha256` stays `None` — deferred to Phase 6).

`FormatInfo` fields: `format_id`, `name`, `suffixes`, `layouts`, `limitations`,
`doc_reference`. Ingestion exceptions: `UnsupportedFormatError`,
`AmbiguousFormatError`, `ManifestError`, `ParseError`, `DataConflictError`.

## Model types

| Name | Kind | Purpose |
|------|------|---------|
| `AUCExperiment` | frozen dataclass | Top-level experiment container. |
| `ExperimentMetadata` | pydantic model | Experiment identity (area A). |
| `InstrumentMetadata` | pydantic model | Instrument & run metadata (area B). |
| `SampleMetadata` | pydantic model | Sample & buffer metadata (area C). |
| `ScanMetadata` | pydantic model | Per-scan metadata (area D). |
| `Observations` | class (xarray-backed) | Radial signal data (area E). |
| `ImportProvenance` | pydantic model | Provenance record (area F). |
| `Quantity` | pydantic model | Scientific scalar with unit/status/provenance. |
| `ValidationReport`, `ValidationIssue` | dataclasses | Structural-validation results. |

## Enums

`ExperimentType`, `OpticalSystem`, `Unit`, `RadiusAxisMode`, `ValueStatus`,
`ValueProvenance`, `ValidationSeverity`.

## Key methods

```python
AUCExperiment(metadata, scans, observations, samples=(), instrument=None,
              provenance=None)
AUCExperiment.summary() -> str
AUCExperiment.validate_structure() -> ValidationReport
AUCExperiment.optical_systems() -> tuple[OpticalSystem, ...]
AUCExperiment.to_dict() -> dict
AUCExperiment.from_dict(data) -> AUCExperiment

Observations.from_shared_axis(*, radius, signal, scan_ids,
                              signal_unit=Unit.UNKNOWN,
                              radius_unit=Unit.CENTIMETRE) -> Observations
Observations.from_per_scan(*, radii, signals, scan_ids,
                           signal_unit=Unit.UNKNOWN,
                           radius_unit=Unit.CENTIMETRE) -> Observations
Observations.to_dict() -> dict
Observations.from_dict(data) -> Observations
Observations.points_per_scan() -> tuple[int, ...]
Observations.valid_radius_values() -> numpy.ndarray
Observations.radius_range() -> tuple[float, float] | None

Quantity.of(value, unit, *, unit_label=None, provenance=SUPPLIED) -> Quantity
Quantity.missing() / Quantity.unknown() / Quantity.not_applicable()

ValidationReport.is_valid -> bool
ValidationReport.errors / ValidationReport.warnings
ValidationReport.raise_if_invalid() -> None   # raises StructuralValidationError

validate_experiment_structure(experiment) -> ValidationReport
```

## Exceptions

`OpenAUCError` (base), `ValidationError`, `StructuralValidationError`,
`ObservationError`, `FormatError` (with `UnsupportedFormatError`,
`AmbiguousFormatError`, `ParseError`), `ManifestError`, `DataConflictError`,
`ArchiveError`.

## Note

Structural validation and `summary()` describe data structure only. Neither
makes any claim about scientific validity or suitability for sedimentation
analysis. Phase 3 adds generic CSV/TSV ingestion; AUCX archive I/O, plotting,
vendor formats and scientific quality control are not implemented.
