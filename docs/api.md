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
| `ValidationReport`, `ValidationIssue` | dataclasses | Validation results. |
| `ExperimentSummary` | pydantic model (frozen) | Structured structural summary. |
| `ValueRange`, `MetadataPresence`, `ValidationCounts` | pydantic models (frozen) | Summary components. |
| `ReadinessAssessment`, `AnalysisReadiness` | dataclasses | Metadata-presence reporting. |

## Enums

`ExperimentType`, `OpticalSystem`, `Unit`, `RadiusAxisMode`, `ValueStatus`,
`ValueProvenance`, `ValidationSeverity`, `ValidationTier`, `ReadinessStatus`,
`AnalysisKind`.

## Key methods

```python
AUCExperiment(metadata, scans, observations, samples=(), instrument=None,
              provenance=None)
AUCExperiment.summary() -> str                       # summary_data().to_text()
AUCExperiment.summary_data() -> ExperimentSummary
AUCExperiment.validate_structure() -> ValidationReport   # tiers A+B
AUCExperiment.validate() -> ValidationReport             # all four tiers
AUCExperiment.assess_readiness() -> ReadinessAssessment
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

ValidationReport.is_valid -> bool             # no ERROR-severity findings
ValidationReport.errors / .warnings / .infos
ValidationReport.counts() -> tuple[int, int, int]
ValidationReport.codes() -> tuple[str, ...]
ValidationReport.by_code(code) -> tuple[ValidationIssue, ...]
ValidationReport.for_tiers(*tiers, severities=None) -> ValidationReport
ValidationReport.blocking_for(tier) -> tuple[ValidationIssue, ...]
ValidationReport.raise_if_invalid() -> None   # raises StructuralValidationError
ValidationReport.to_dict() -> dict

ValidationIssue.code / .message / .severity / .location
ValidationIssue.tiers / .tier / .blocks
ValidationIssue.observed / .expected / .remediation / .component / .scan_ids
ValidationIssue.blocks_structural_validity -> bool
ValidationIssue.blocks_tier(tier) -> bool
ValidationIssue.describe() -> str
ValidationIssue.to_dict() -> dict

ExperimentSummary.to_dict() -> dict           # JSON-friendly
ExperimentSummary.to_text() -> str
ValueRange.render() -> str
ValueRange.is_observed -> bool

ReadinessAssessment.sedimentation_velocity / .sedimentation_equilibrium
ReadinessAssessment.scientific_suitability   # always NOT_ASSESSED
ReadinessAssessment.for_analysis(kind) -> AnalysisReadiness
ReadinessAssessment.to_dict() -> dict
AnalysisReadiness.status / .is_blocked / .blocking_issues / .advisory_issues

validate_experiment_structure(experiment) -> ValidationReport
validate_experiment(experiment) -> ValidationReport
summarise_experiment(experiment) -> ExperimentSummary
assess_experiment_readiness(experiment) -> ReadinessAssessment
```

## Validation and readiness (Phase 4)

Validation answers four independent questions, named by `ValidationTier`:
`ARCHIVAL`, `STRUCTURAL`, `SV_READINESS`, `SE_READINESS`. Only `ERROR`-severity
findings affect `is_valid`, and readiness findings never carry `ERROR`, so
structural validity and analysis readiness stay independent. Absent metadata is
reported, never required.

`assess_readiness()` reports metadata *presence* per workflow via
`ReadinessStatus` (`POTENTIALLY_READY`, `BLOCKED`, `NOT_APPLICABLE`,
`NOT_ASSESSED`). Scientific suitability is a permanent `NOT_ASSESSED` entry and
is never derived from any finding.

See [validation tiers](concepts/validation-tiers.md) for every check, its
severity and the tiers it blocks, and [analysis
readiness](concepts/analysis-readiness.md) for routing and blocking sets.

## Exceptions

`OpenAUCError` (base), `ValidationError`, `StructuralValidationError`,
`ObservationError`, `FormatError` (with `UnsupportedFormatError`,
`AmbiguousFormatError`, `ParseError`), `ManifestError`, `DataConflictError`,
`ArchiveError`.

## Note

Validation, readiness and summaries describe data structure and metadata
presence only. None of them makes any claim about scientific validity, data
quality or suitability for sedimentation analysis. AUCX archive I/O, plotting,
vendor formats, unit conversion, CLI domain commands and scientific quality
control are not implemented.
