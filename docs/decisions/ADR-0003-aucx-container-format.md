# ADR-0003 — AUCX container format

- **Status:** Proposed
- **Date:** 2026-07-23
- **Deciders:** Ron Finn
- **Related:** ADR-0002, ADR-0004; development-log/0001

## Context

The first release must be able to **export** a canonical AUC experiment to a
durable archival file and **reload** it losslessly, together with checksums and
provenance. This archival format is new and project-defined: **AUCX**, file
extension `.aucx`. Because AUCX is authored here rather than reverse-engineered
from an existing product, its rules can and must be documented fully and openly;
this does not conflict with the boundary against fabricating undocumented rules
for *third-party* formats.

Design priorities, in order: **losslessness** (round-trips the canonical model
including per-scan radius axes), **inspectability** (a scientist can open and
audit it without bespoke tooling), **integrity** (per-part checksums and
provenance), **portability** (no compiled backend or platform-specific
dependency), and **forward-compatibility** (readable across format versions).

## Decision under consideration

AUCX is a **zip-of-parts container**: a `.aucx` file is a ZIP archive holding
several named parts. The intended part layout (details to be finalised in the
Phase 6 specification under `docs/formats/` and `schemas/`):

- **`manifest.json`** — canonical experiment metadata (JSON is canonical per the
  project manifest decision; YAML is an authoring convenience only and is not the
  in-archive form). Includes a mandatory **AUCX format-version** field.
- **Data parts** — the numeric scan data (one or more parts). Both radius-axis
  regimes from ADR-0002 are representable: a shared axis is stored once; per-scan
  axes are stored per scan. No interpolation occurs on write or read.
- **`checksums`** — a manifest of per-part checksums (SHA-256 assumed) so
  integrity can be verified part-by-part.
- **`provenance`** — how the archive was produced (tool version, source inputs,
  timestamps, and the transformations applied), recorded rather than inferred.

Being a ZIP, an AUCX file is inspectable with ubiquitous tools, streamable, and
requires no compiled scientific backend. This directly avoids the wheel- and
platform-availability risk that a single NetCDF/HDF5 file would introduce across
Python 3.11–3.13.

## Alternatives considered

- **Single NetCDF/HDF5 file** (via an xarray backend). Idiomatic for array data
  and compact, but adds a compiled dependency (`h5netcdf`/`netCDF4`), complicates
  per-part checksumming and provenance embedding, and is less transparent to
  casual inspection. Rejected for v0.1; may be reconsidered as an *optional*
  interchange target later.
- **A single flat file (custom binary).** Rejected: bespoke binary formats are
  opaque, hard to validate, and hostile to long-term archival readability.
- **Bare directory of files (no container).** Good inspectability, but poor as a
  single portable artefact to name, move, checksum, and cite. The ZIP gives the
  same internal structure inside one addressable file.
- **SQLite database file.** Durable and inspectable with tooling, but heavier
  than needed for a write-once archival snapshot and less transparent than plain
  JSON + array parts.

## Consequences

**Positive**

- Inspectable and tool-agnostic; opens with any ZIP utility.
- Lossless for both shared and per-scan radius representations.
- Per-part SHA-256 and an explicit provenance part support integrity and
  auditability.
- No compiled backend; broad wheel/platform availability across 3.11–3.13.
- Serialisation cleanly mirrors the two-layer canonical model (metadata as JSON,
  numeric as data parts).

**Negative / costs**

- The in-archive encoding of the numeric data parts is not yet fixed (see below),
  so the on-disk spec is incomplete until Phase 6.
- ZIP plus multiple parts is slightly more to specify and version than one binary
  file.
- Forward-compatibility must be actively managed through the format-version field
  and a documented migration policy.

## Unresolved questions

- **In-archive data encoding** (development-log Q1): Parquet, NetCDF-per-part,
  `.npy`/`.npz`, or plain CSV for the numeric parts? This choice may add
  `pyarrow` (Parquet) or a backend (NetCDF) as an optional dependency and will be
  settled before Phase 6.
- **Checksum algorithm confirmation:** SHA-256 is assumed; to be confirmed with
  the provenance schema (development-log Q5).
- **Provenance schema:** exact fields and their required/optional status.
- **Versioning policy:** how AUCX format-version increments map to reader
  compatibility and the supported migration path between versions.

## References

- Prior art in zip-of-parts scientific/document containers (e.g. OOXML `.xlsx`,
  NumPy `.npz`) as design precedent, not as an implementation source.
- The ZIP file format (PKWARE APPNOTE) and Python's standard-library `zipfile`.
- FIPS 180-4 (SHA-256) for the integrity checksums.
