# Roadmap

## Delivered

| Phase | Capability |
|-------|-----------|
| 0 | Foundation: development log and four ADRs |
| 1 | Packaging, tooling, CI across Python 3.11–3.13 |
| 2 | Canonical in-memory data model |
| 3 | Generic CSV/TSV ingestion and the parser registry |
| 4 | Validation tiers, analysis readiness, structured summaries |
| 5 | Basic scan plotting |
| 6 | AUCX archival container, source checksums |
| 7 | Command-line interface |
| 8 | Alpha-release readiness at `0.1.0a1` |
| — | Deterministic synthetic-data generator |
| — | This documentation site |
| 9 | Release mechanics: coverage gate, release-check and artifact-verification scripts, a publish-free release dry-run workflow, and a written [release checklist](release-checklist.md) |
| 10 | First public alpha: `v0.1.0a1` tagged, published as a GitHub pre-release, and uploaded to [PyPI](https://pypi.org/project/openauc/0.1.0a1/) over Trusted Publishing |

Release-hardening follow-ups after Phase 9 — such as isolating the artifact
verifier's unit tests from the repository's mutable `dist/` — are corrections to
that machinery, not a new phase.

## Open questions

Seven were raised at the outset. All seven are resolved:

| Question | Status |
|----------|--------|
| Q1 — In-archive data encoding | **Resolved**: NumPy `.npy` (ADR-0003) |
| Q2 — Canonical units | **Resolved**: fixed, retained, never converted (ADR-0002) |
| Q3 — Minimum valid-experiment metadata | **Resolved**: construction invariants plus unambiguous keying (ADR-0002) |
| Q4 — Optical systems in v1 | **Resolved**: five represented (ADR-0002) |
| Q5 — Provenance schema and checksum algorithm | **Resolved**: SHA-256, per-source entries (ADR-0003) |
| Q6 — Documentation tooling | **Resolved**: MkDocs Material — this site |
| Q7 — CLI command surface | **Resolved**: six commands with documented exit codes |

## Delivered after 0.1.0a1 (unreleased)

- Sample-to-scan linkage: an optional `sample_id` on `ScanMetadata`, the
  `scan_sample_unresolved` structural finding, and manifest support for
  `defaults.sample_id`.
- Acquisition times in the manifest (`experiment.acquired_at`, wide-format
  `acquisition_timestamp`) with strict timestamp parsing.
- AUCX format version 1.1 (reads 1.0 and 1.1).

## Next milestone

None is committed beyond the above. The first public alpha has been taken — `0.1.0a1` is tagged,
released and on PyPI — and no successor version has been selected, scheduled or
promised. What comes next will be chosen from the candidates below, and this
section will say so once it is.

## Candidates, not commitments

- Vendor-format readers. Each needs a **documented, non-reverse-engineered**
  specification before any parsing code is written. See
  [Scientific boundaries](../concepts/scientific-boundaries.md).
- Heterogeneous per-scan signal units.
- Third-party parser discovery through entry points.

## Never

Scientific analysis, quality control, unit conversion and physical simulation
are permanent non-goals, not deferred work.

## Next step

- [Known limitations](limitations.md)
- [Architecture decisions](decisions.md)
