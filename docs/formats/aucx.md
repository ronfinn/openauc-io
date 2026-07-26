# AUCX — the archival container

AUCX (`.aucx`) is this project's own archival format: a ZIP of parts holding
JSON metadata and NumPy `.npy` arrays. It is designed to be **inspectable with
ordinary tools**, to preserve the canonical model exactly, and to be verifiable.

```python
import openauc

experiment = openauc.load("path/to/experiment")  # generic CSV/TSV
experiment.export("experiment.aucx")  # write
restored = openauc.load("experiment.aucx")  # read back
assert restored.to_dict() == experiment.to_dict()
```

Current format version: **1.0**. Only 1.0 is read. An archive declaring any
other version is rejected with `ArchiveVersionError` — **archives are never
silently migrated**.

## Structure

```text
manifest.json          format version, export record, array shapes and dtypes
experiment.json        metadata, instrument, samples, scans
provenance.json        inherited import provenance + the export record
arrays/radius.npy      radius values
arrays/signal.npy      signal values, always 2-D (scan, point)
arrays/mask.npy        authoritative boolean validity mask, always 2-D
checksums.sha256       SHA-256 of every other member
```

`manifest.json` lists the payload members in `parts`. An archive carrying a
member that is neither listed nor `manifest.json`/`checksums.sha256` is
rejected, and a listed part that is absent is rejected.

### Why `.npy`

Numeric data is stored as `.npy` rather than CSV, Parquet or NetCDF so that
**dtype, shape and the validity mask survive exactly**, with no tabular
re-encoding and no heavy archive dependency. Arrays are always loaded with
`allow_pickle=False`, so reading an archive can never execute code.

### Both radius modes

| Mode | `radius.npy` | `signal.npy` | `mask.npy` |
|------|--------------|--------------|------------|
| `shared` | 1-D, length `points` | 2-D `(scans, points)` | 2-D, all true |
| `per_scan` | 2-D `(scans, points)`, NaN-padded | 2-D `(scans, points)` | 2-D, true where real |

A mask is written in **both** modes so a reader never has to infer one. In
shared mode every stored value is a real observation, so the mask must be
all-true; an archive claiming otherwise is rejected, because the canonical model
cannot represent partial validity on a shared axis.

Round-tripping preserves scan identifiers and order, metadata, samples,
instrument metadata, quantities with their units and
present/missing/unknown/not-applicable statuses, provenance, masks, floating
point dtype, and array shapes.

## Checksums

`checksums.sha256` lists every other member, one per line, sorted by member
name:

```text
<64 lowercase hex digits><two spaces><member name>
```

The checksum file does not checksum itself. On load, `openauc`:

1. requires the file to be present — an archive without it is rejected;
2. rejects malformed lines, non-hex digests and repeated member names;
3. rejects listed members that are missing from the archive;
4. rejects archive members that the file does not list;
5. **verifies every listed digest before any model is constructed.**

Nothing is reported as valid before verification succeeds.

> **Integrity, not authenticity.** A verified archive is one whose bytes are
> unchanged since it was written. SHA-256 here proves nothing about *who* wrote
> the archive. It is not a signature.

## Provenance

`provenance.json` keeps two records apart:

- **`import`** — the experiment's own `ImportProvenance`, exactly as it was.
  It travels with the model unchanged, so a round trip preserves it and
  `restored.to_dict() == original.to_dict()`.
- **`export`** — the AUCX export event: format version, software name and
  version, export timestamp, and the checksum algorithm.

The export record is reached with `openauc.inspect_aucx(path)`, not by reading
it off the restored experiment — the experiment's provenance is about where the
*data* came from, not about the archive that happens to carry it.

Source-file checksums are recorded at import time. Because a manifest-driven
import reads more than one file, each is recorded separately:

```python
for entry in experiment.provenance.source_checksums:
    print(entry.role, entry.filename, entry.value)
# manifest   manifest.json  f00943...
# data_file  scans.csv      e3d909...
```

`ImportProvenance.sha256` remains, mirroring the `data_file` entry for the
common single-file case.

## Determinism

Two exports of equivalent experiments with the same `exported_at` are
**byte-identical**. Achieved by fixing member order, ZIP timestamps
(1980-01-01), permission bits (0644), creator system and compression, and by
writing JSON with sorted keys and fixed separators.

```python
experiment.export("a.aucx", exported_at=datetime(2026, 1, 1, tzinfo=UTC))
```

Omit `exported_at` and the current UTC time is used, which is what a normal
export wants; pass a fixed value when byte-for-byte reproducibility matters.

## Atomic writes

An export never leaves a partial archive behind:

1. write to a sibling temporary file;
2. complete every part;
3. **read the finished temporary archive back and verify it in full**;
4. only then move it into place;
5. remove the temporary file if anything failed.

An existing destination is not overwritten unless `overwrite=True`.

## Safety

Reading an archive rejects:

- absolute member paths, `..` traversal, and backslash-separated names;
- duplicate member names;
- encrypted members;
- members declaring more than 512 MiB, or 2 GiB in total, before allocating;
- object arrays and pickled payloads (`allow_pickle=False` throughout);
- arrays of the wrong dimensionality, shape or dtype, including a non-boolean
  mask;
- shapes that disagree with the manifest, or a scan count that disagrees with
  the stored identifiers.

Archives are never extracted to disk, and low-level ZIP, JSON and NumPy failures
are converted to `ArchiveError` with the archive name and the failing member in
the message.

## Inspection and validation

Archive integrity is **separate** from structural and scientific validation:

```python
info = openauc.inspect_aucx("experiment.aucx")  # verifies; raises on problems
info.aucx_format_version, info.radius_axis_mode, info.n_scans, info.export

report = openauc.validate_aucx("experiment.aucx")  # never raises
report.is_valid, report.issues

restored = openauc.load("experiment.aucx")
restored.validate_structure()  # a different question entirely
restored.validate()
restored.assess_readiness()
restored.summary_data()
```

`validate_aucx` reports container problems only: readability, safety, member
agreement and checksums. It says nothing about whether the experiment inside is
structurally consistent, and nothing at all about scientific suitability.

## Exceptions

| Exception | Raised for |
|-----------|-----------|
| `ArchiveError` | unreadable or unsafe ZIP, missing/unexpected member, malformed JSON or `.npy`, shape/dtype disagreement, overwrite refusal |
| `ArchiveIntegrityError` | missing, malformed or mismatched checksums |
| `ArchiveVersionError` | unsupported `aucx_format_version` |

`ArchiveIntegrityError` and `ArchiveVersionError` are subclasses of
`ArchiveError`, so catching the base class catches all three.

## Not included in version 1.0

Compression tuning, partial or streaming reads, multi-experiment archives,
embedded plots or derived data, encryption and signatures. Signatures in
particular are out of scope: this format offers integrity checking only.
