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

_Phase 3 ingests generic CSV/TSV only. Vendor/instrument formats, AUCX archive
I/O, plotting, automatic unit conversion, and scientific quality control are not
implemented, and no claim of scientific validity is made. Checksum (SHA-256)
computation remains deferred to Phase 6 (ADR-0003); `ImportProvenance.sha256` is
left `None`._

[Unreleased]: https://github.com/ronfinn/openauc-io/commits/main
