# Development Log 0006 — AUCX archive (Phase 6)

- **Date:** 2026-07-25
- **Branch:** `feat/validation-and-summaries` (continuous alpha build)
- **Status:** Phase 6 complete. AUCX export and import, with integrity
  verification. Resolves Q1 and Q5, and closes the Phase 3 checksum deferral.
- **Author:** Ron Finn

## 1. Objective

Export a canonical experiment to a durable, inspectable archive and read it back
losslessly, with checksums and provenance — without introducing a heavy
dependency or a format that loses dtype, shape or the validity mask.

## 2. Accepted decisions

**Container:** ZIP of parts. **Metadata:** JSON. **Arrays:** NumPy `.npy`,
always loaded with `allow_pickle=False`. Parquet, CSV and NetCDF rejected for
version 1.0 (see the ADR-0003 Phase 6 amendment for the reasoning — briefly: CSV
loses dtype and cannot carry the mask; Parquet and NetCDF each add a substantial
dependency for what is already a small dense array).

**Version:** `aucx_format_version: "1.0"`, checked on every read. Any other
value is rejected with `ArchiveVersionError`. Archives are never silently
migrated.

**A mask is written in both radius modes.** Shared mode has no mask in the
model, because every stored value is real; writing an all-true one means a
reader never has to infer it, and both modes have identical part lists. A shared
archive whose mask is not all-true is **rejected** rather than reinterpreted —
the canonical model cannot represent partial validity on a shared axis, and
quietly dropping points would be exactly the silent data loss this project
forbids.

**Import provenance and the export record are kept apart.** The restored
experiment carries the archive's stored *import* provenance unchanged, so
`restored.to_dict() == original.to_dict()`. The export event is reached via
`inspect_aucx`, not grafted onto the model: the experiment's provenance is about
where the data came from, not about the archive that happens to carry it.

## 3. Structure

```text
manifest.json          format version, export record, array shapes and dtypes
experiment.json        metadata, instrument, samples, scans
provenance.json        {"import": ImportProvenance|null, "export": AUCXExport}
arrays/radius.npy      1-D (shared) or 2-D NaN-padded (per-scan)
arrays/signal.npy      always 2-D (scan, point)
arrays/mask.npy        always 2-D boolean
checksums.sha256       SHA-256 of every other member
```

`manifest.json` lists payload members in `parts`; a member that is neither
listed nor `manifest.json`/`checksums.sha256` is rejected, and a listed part
that is absent is rejected.

## 4. Source checksums — closing the deferral

Phase 3 deferred checksum computation, which is why `source_checksum_absent`
fired on every import. That is now resolved.

A single `sha256` field could not honestly describe an import that reads *two*
files, so `ImportProvenance` gained an additive, typed
`source_checksums: tuple[SourceChecksum, ...]`. Each entry names its `role`
(`manifest`, `data_file`), filename, algorithm, digest and byte size. The
existing `sha256` field is retained and mirrors the `data_file` entry, so
nothing that read it before breaks.

**Consequence, deliberate:** imported experiments no longer emit
`source_checksum_absent`, and `ExperimentSummary.checksum_available` is now true
for them. Four Phase 3/4 tests asserted the old behaviour and were updated to
assert the new. The `readiness_rich` fixture now validates with **zero**
findings.

## 5. Integrity policy

Every member except `checksums.sha256` is checksummed. On load, in order: the
checksum file must exist; its lines must parse (64 lowercase hex, two spaces,
member name, no repeats); every listed member must be present; every digest must
match; and no unlisted member may exist. **All of this completes before any model
is constructed** — nothing is reported valid before verification succeeds.

Added `ArchiveIntegrityError` and `ArchiveVersionError` as subclasses of
`ArchiveError`, so catching the base still catches everything.

**Integrity is not authenticity.** A verified archive is one whose bytes are
unchanged since writing. AUCX carries no signature and makes no claim about who
produced it; the docs say so explicitly, and signing is out of scope for 1.0.

## 6. Determinism and atomicity

Byte-identical exports for equivalent experiments given the same `exported_at`:
fixed member order, ZIP timestamp `1980-01-01`, permission bits `0644`, creator
system `0`, fixed deflate level, and JSON with sorted keys and fixed separators.
`exported_at` defaults to the current UTC time; tests pass a fixed value.

Writes go to a sibling temporary file, which is **read back and verified in
full** before `os.replace` moves it into place; the temporary file is removed on
any failure. An existing destination is never overwritten without
`overwrite=True`.

## 7. Safety

Rejected on read: absolute member paths, `..` traversal, backslash names,
duplicate members, encrypted members, members over 512 MiB (or 2 GiB total)
before allocation, object arrays and pickled payloads, wrong dimensionality,
shape or dtype including a non-boolean mask, shapes disagreeing with the
manifest, and scan counts disagreeing with the stored identifiers. Archives are
never extracted to disk. Low-level ZIP/JSON/NumPy failures are converted to
`ArchiveError` naming the archive and the failing member.

## 8. Public API

```python
openauc.export_aucx(experiment, path, *, overwrite=False, exported_at=None)
experiment.export(path, *, overwrite=False, exported_at=None)
openauc.load("experiment.aucx")          # dispatches on suffix
openauc.load(path, format="aucx")        # or explicitly
openauc.inspect_aucx(path) -> AUCXInfo   # verifies; raises on problems
openauc.validate_aucx(path) -> ArchiveValidationReport   # never raises
```

`load()` dispatches to the archive reader before the manifest/table machinery,
on either the `.aucx` suffix or an explicit `format="aucx"`. Generic CSV/TSV
loading is untouched.

AUCX is registered as an **archive format** rather than a `Parser`: the parser
interface is built around a delimited `Table` and detection confidence, neither
of which applies to a whole-file container. `registry.register_archive_format`
keeps it visible in `available_formats()` without distorting the ABC.

## 9. Tests

52 new tests (`tests/unit/test_aucx.py`, `tests/integration/test_aucx_imported.py`):
shared and per-scan round-trips; metadata, unit and status preservation
including all four `ValueStatus` kinds; provenance and source checksums;
dtype/shape preservation; empty and fully masked scans; determinism with a fixed
timestamp; a different timestamp changing only the timestamped part; overwrite
refusal and `overwrite=True`; atomic-failure leaving no temporary file;
unsupported version; missing checksum file; missing listed member; malformed
checksum entries (three shapes); empty checksum file; unlisted extra member;
duplicate members; four unsafe member paths; corrupt JSON; corrupt `.npy`;
object arrays; shape mismatch; non-boolean mask; partial shared mask; non-ZIP
input; missing file; error messages naming the archive and member; CSV/TSV →
AUCX → model over six fixtures; `openauc.load` dispatch three ways; re-export
stability; and the full model API on a restored experiment.

## 10. Known limitations

- One experiment per archive.
- No compression tuning, streaming or partial reads; archives are read whole
  into memory, bounded by the size limits above.
- No encryption or signatures — integrity only.
- The 512 MiB/2 GiB limits are constants, not yet configurable.
- Re-exporting a loaded archive reproduces it byte-for-byte only when the same
  `exported_at` is supplied; the default (now) naturally differs.

## 11. Rejected alternatives

- **Parquet / NetCDF / CSV for arrays** — dependency weight or lossiness; see §2.
- **Implementing AUCX as a `Parser`** — the ABC assumes a delimited table and
  confidence detection; forcing a container through it would have distorted both.
- **Grafting the export record onto the restored experiment's provenance** —
  would break round-trip equality and conflate two different questions.
- **Extracting archives to a temporary directory** — unnecessary, and it widens
  the attack surface for hostile paths.
- **Reusing `sha256` for multiple source files** — dishonest; a digest with no
  stated subject. Replaced by typed per-source entries.

## 12. Next steps

Phase 7: the practical CLI (`version`, `formats`, `inspect`, `validate`,
`convert`) over these APIs, with documented exit codes.
