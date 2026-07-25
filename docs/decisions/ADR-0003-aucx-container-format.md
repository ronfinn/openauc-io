# ADR-0003 — AUCX container format

- **Status:** Accepted (Phase 6 — implemented; see the Phase 6 amendment below)
- **Date:** 2026-07-23 (proposed); amended and accepted 2026-07-25 (Phase 6)
- **Deciders:** Ron Finn
- **Related:** ADR-0002, ADR-0004; development-log/0001;
  development-log/0006

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

---

## Amendment — Phase 6 implementation (2026-07-25)

AUCX is implemented and the status is changed to **Accepted** alongside this
record of what was actually built. The load-bearing choice — a zip of parts
rather than a single binary file — held up: no compiled backend is needed, and
the archive is inspectable with `unzip` and any JSON viewer.

### Resolved: Q1, in-archive data encoding

**NumPy `.npy` for every array; JSON for every metadata part.** Parquet, CSV and
NetCDF were all rejected for version 1.0.

- CSV loses dtype and cannot carry the validity mask without inventing a
  convention; it would also re-encode floating-point values as text.
- Parquet and NetCDF are columnar/scientific container formats that would each
  add a substantial dependency (`pyarrow`, `h5netcdf`/`netCDF4`) for data that
  is already a small dense array, reintroducing exactly the wheel-availability
  risk that R4 in development-log 0001 avoided.
- `.npy` preserves dtype, shape and byte layout exactly, is part of an existing
  required dependency, and is trivially readable by any NumPy user.

Arrays are always read with `allow_pickle=False`, and object arrays are
rejected, so opening an archive can never execute code.

### Resolved: Q5, provenance schema and checksum algorithm

**SHA-256 is confirmed**, and the deferral recorded in Phase 3 is now closed:
source-file digests are computed at import.

A single `sha256` field could not honestly describe an import that reads both a
manifest and a data file, so `ImportProvenance` gained an additive typed
`source_checksums: tuple[SourceChecksum, ...]`, each entry naming its `role`
(`manifest`, `data_file`), filename, algorithm, digest and byte size. The
original `sha256` field is retained and mirrors the `data_file` entry, so
existing readers keep working.

Archive provenance separates two things that were previously conflated: the
experiment's **import** provenance (where the data came from — preserved
unchanged through a round trip) and the **export** record (`AUCXExport`: format
version, software and version, export timestamp, checksum algorithm). The export
record is reached through `inspect_aucx`, deliberately not grafted onto the
restored model.

### Structure as built

```text
manifest.json  experiment.json  provenance.json
arrays/radius.npy  arrays/signal.npy  arrays/mask.npy
checksums.sha256
```

A mask is written in **both** radius modes so a reader never infers one; in
shared mode it must be all-true, because the canonical model cannot represent
partial validity on a shared axis, and an archive claiming otherwise is
rejected rather than silently reinterpreted.

### Integrity policy

Every member except `checksums.sha256` is checksummed, and **every digest is
verified before any model is constructed**. Missing checksum files, malformed
entries, missing listed members, unlisted extra members and digest mismatches
are all rejected. `ArchiveIntegrityError` and `ArchiveVersionError` were added
as subclasses of `ArchiveError`.

**This is integrity checking, not authenticity.** A verified archive is one
whose bytes are unchanged since it was written; AUCX carries no signature and
makes no claim about who produced it. Signing is explicitly out of scope for
version 1.0.

### Determinism and atomicity

Exports are byte-identical for equivalent experiments given the same
`exported_at`: member order, ZIP timestamps, permission bits, creator system and
compression are all fixed, and JSON is written with sorted keys. Writes go to a
sibling temporary file which is read back and verified in full before it
replaces the destination, so a failure never leaves a partial archive.

### Forward compatibility

`aucx_format_version` is `"1.0"` and is checked on every read. Any other value
is rejected with `ArchiveVersionError`. **Archives are never silently migrated**;
a future version that can read 1.0 will do so through an explicit, documented
path.
