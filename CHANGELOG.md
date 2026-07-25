# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0a1] - unreleased

First internally coherent alpha. **Not published**: no PyPI release, no GitHub
release, no tag.

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

- Phase 5 — basic scan plotting (`openauc.plotting`): `plot_scans` and
  `plot_scan` draw radial scans from the canonical model onto a
  `matplotlib.axes.Axes`. Each scan is rendered from its own stored
  `(radius, signal)` vectors in stored order — nothing is interpolated,
  resampled, sorted or smoothed, and per-scan radius axes are never placed on a
  common grid (ADR-0002). Figures are built without `pyplot`, so plotting works
  headless and leaks no global figures; matplotlib is imported on the first draw
  so `import openauc` stays light, and `openauc.api.plot_scans` resolves lazily.
  Adds `Observations.scan_vectors()` / `iter_scan_vectors()` for masked per-scan
  access, and the `PlottingError` exception.

- Phase 6 — the **AUCX archival container** (`openauc.formats.aucx`): a ZIP of
  JSON metadata and NumPy `.npy` arrays at format version `1.0`.
  `openauc.export_aucx` / `experiment.export()` write it; `openauc.load()`
  reads it via suffix or `format="aucx"`; `openauc.inspect_aucx` and
  `openauc.validate_aucx` report on it. Both radius modes, masks, dtypes,
  shapes, units and all four value statuses round-trip exactly. Every checksum
  is verified before a model is constructed. Exports are deterministic (fixed
  member order, ZIP timestamps, permissions and compression; JSON with sorted
  keys) and atomic (written to a sibling temporary file, verified, then moved).
  Adds `ArchiveIntegrityError`, `ArchiveVersionError`, `AUCXInfo`, `AUCXExport`
  and `ArchiveValidationReport`.
- Phase 6 — **source checksums at import**, resolving the Phase 3 deferral.
  `ImportProvenance` gains `source_checksums: tuple[SourceChecksum, ...]`, one
  typed entry per source file with its role (`manifest`, `data_file`), digest
  and byte size. `sha256` is retained and mirrors the `data_file` entry.
- Phase 7 — a practical **CLI**: `openauc version | formats | inspect |
  validate | convert`, each with `--json` where useful, `--readiness` on
  `validate`, `--overwrite` on `convert`, and documented exit codes (0 success,
  1 structural failure, 2 input error, 3 output exists). Domain errors print one
  clear line, never a traceback.
- Phase 8 — six runnable `examples/` over new synthetic demo data, `docs/cli.md`,
  and release-readiness tests covering the public surface, examples, packaging
  metadata and repository hygiene.

### Changed

- **Version is now `0.1.0a1`** (was `0.1.0.dev0`), in the package and
  `CITATION.cff`.
- Imported experiments now record source checksums, so `source_checksum_absent`
  no longer fires for them and `ExperimentSummary.checksum_available` is true.
  This is the intended resolution of the Phase 3 deferral.
- `available_formats()` now also lists archive formats, so `aucx` appears
  alongside the delimited parsers.
- ADR-0003 amended and accepted, recording the implemented archive structure and
  resolving Q1 (in-archive encoding) and Q5 (provenance schema, SHA-256).
- `AUCExperiment.summary()` now renders the structured summary and appends nine
  further lines (points per scan, total observations, wavelengths, cells,
  channels, rotor speed, temperature, source checksum, validation counts). Every
  previously emitted line is preserved verbatim.
- `validate_structure()` is now defined as the archival and structural findings
  of `ERROR` or `WARNING` severity; informational and readiness findings are
  reported by `validate()`. Existing codes, severities and the meaning of
  `ValidationReport.is_valid` are unchanged.

_Generic delimited ingestion reads CSV/TSV only. Vendor and instrument formats,
automatic unit conversion, and scientific quality control are not implemented,
and no claim of scientific validity is made anywhere._

_Phase 4 validates and summarises structure and metadata presence only. It never
judges scientific validity, data quality or suitability for analysis: absent
metadata is reported, never required, and scientific suitability is permanently
reported as `NOT_ASSESSED`. Sample-to-scan linkage and heterogeneous per-scan
signal units remain deferred._

_AUCX checksums establish **integrity, not authenticity**: a verified archive is
one whose bytes are unchanged since it was written, not one whose origin is
proven. AUCX carries no signature. Vendor and instrument formats remain
unsupported, and no scientific analysis, quality control or unit conversion is
implemented._

_Phase 5 plots only what is stored. No fitting, smoothing, baseline correction,
derivative or derived overlay is drawn, and no regridding API is offered:
placing per-scan data on a common grid remains an explicit, opt-in, recorded
transformation that does not yet exist._

[0.1.0a1]: https://github.com/ronfinn/openauc-io/commits/main
