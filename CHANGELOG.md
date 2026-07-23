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

_Phase 2 provides data representation and structural validation only. There is
no CSV/TSV parsing, AUCX archive I/O, plotting, unit conversion, or scientific
quality control, and no claim of scientific validity._

[Unreleased]: https://github.com/ronfinn/openauc-io/commits/main
