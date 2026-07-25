# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Phase 0 — project foundation: development log `0001` and Architecture Decision
  Records ADR-0001 through ADR-0004.
- Phase 1 — packaging and tooling scaffold: `pyproject.toml` (hatchling build
  backend, uv-managed, src layout), package skeleton (`openauc` with typed
  marker, exception hierarchy, public API facade and CLI stub), test scaffold,
  ruff / mypy / pytest / pre-commit configuration, GitHub issue and PR templates,
  Dependabot, and a CI workflow across Python 3.11–3.13.
- Community-health files: `README`, `CONTRIBUTING`, `CODE_OF_CONDUCT`,
  `SECURITY`, `CITATION.cff`, `NOTICE`, and a filled Apache-2.0 `LICENSE`.
- Phase 2 — canonical in-memory data model (`openauc.models`): pydantic v2
  metadata (`ExperimentMetadata`, `InstrumentMetadata`, `SampleMetadata`,
  `ScanMetadata`), the `Quantity` value type with explicit
  present/missing/unknown/not-applicable status and per-value provenance, an
  xarray-backed `Observations` store supporting shared and per-scan radius axes
  (per-scan uses padded 2-D arrays with an authoritative validity mask; no
  silent interpolation), the `AUCExperiment` container with `summary()` and
  structural `validate_structure()`, an in-memory `ImportProvenance` record, and
  metadata/experiment serialisation via `to_dict()`/`from_dict()`. Adds
  `ObservationError` and `StructuralValidationError`. Concept docs under
  `docs/concepts/` and an API reference at `docs/api.md`.

- Phase 3 — generic delimited (CSV/TSV) ingestion (`openauc.formats`): the
  `openauc.load(path, *, format=None, manifest=None)` entry point and
  `openauc.available_formats()`; a parser plugin registry with confidence-based
  detection (ADR-0004); a typed, versioned experiment manifest (JSON canonical,
  YAML for authoring) with safe relative-path validation; `generic-long` and
  `generic-wide` parsers that preserve raw values and order, build shared- or
  per-scan-axis observations without interpolation, retain declared units, and
  populate `ImportProvenance`. Adds `UnsupportedFormatError`,
  `AmbiguousFormatError`, `ManifestError`, `ParseError` and `DataConflictError`;
  a machine-readable schema at `schemas/generic-manifest-v1.schema.json`; and
  docs under `docs/formats/`.

- Phase 4 — tiered validation, analysis readiness and structured summaries: a
  four-tier validation model (`ARCHIVAL`, `STRUCTURAL`, `SV_READINESS`,
  `SE_READINESS`) with 26 deterministic checks carrying stable codes, severity,
  tiers, blocked tiers, observed/expected values and suggested remediation;
  `experiment.validate()` for the full report and `experiment.assess_readiness()`
  for per-workflow metadata-presence reporting; a frozen `ExperimentSummary`
  (with `ValueRange`, `MetadataPresence` and `ValidationCounts`) exposed as
  `experiment.summary_data()`, of which `summary()` is now the text rendering.
  Adds `ValidationTier`, `ReadinessStatus` and `AnalysisKind`, and extends
  `ValidationIssue`/`ValidationReport` with tier-aware fields and filters. This
  phase resolves open question Q3 (see the ADR-0002 Phase 4 amendment) and marks
  ADR-0001 Accepted alongside an as-built amendment.

### Changed

- `AUCExperiment.summary()` now renders the structured summary and appends nine
  further lines (points per scan, total observations, wavelengths, cells,
  channels, rotor speed, temperature, source checksum, validation counts). Every
  previously emitted line is preserved verbatim.
- `validate_structure()` is now defined as the archival and structural findings
  of `ERROR` or `WARNING` severity; informational and readiness findings are
  reported by `validate()`. Existing codes, severities and the meaning of
  `ValidationReport.is_valid` are unchanged.

_Phase 3 ingests generic CSV/TSV only. Vendor/instrument formats, AUCX archive
I/O, plotting, automatic unit conversion, and scientific quality control are not
implemented, and no claim of scientific validity is made. Checksum (SHA-256)
computation remains deferred to Phase 6 (ADR-0003); `ImportProvenance.sha256` is
left `None`._

_Phase 4 validates and summarises structure and metadata presence only. It never
judges scientific validity, data quality or suitability for analysis: absent
metadata is reported, never required, and scientific suitability is permanently
reported as `NOT_ASSESSED`. Sample-to-scan linkage and heterogeneous per-scan
signal units remain deferred._

[Unreleased]: https://github.com/ronfinn/openauc-io/commits/main
