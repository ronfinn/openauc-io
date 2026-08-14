# Export and reload AUCX

**Goal:** archive an experiment losslessly and read it back with confidence.

**Prerequisites:** [Installation](../getting-started/installation.md).

Runnable version:
[`examples/05_aucx_roundtrip.py`](https://github.com/ronfinn/openauc-io/blob/main/examples/05_aucx_roundtrip.py).

## Export

```python
import openauc

experiment = openauc.load("examples/data/demo_experiment")
path = experiment.export("demo.aucx")
```

Or the function form:

```python
path = openauc.export_aucx(experiment, "demo.aucx")
```

From the shell:

```bash
uv run openauc convert examples/data/demo_experiment demo.aucx
```

## Reload

```python
restored = openauc.load("demo.aucx")
assert restored.to_dict() == experiment.to_dict()
```

The round trip is **exact**: both radius modes, masks, dtypes, array shapes,
scan order, declared units, and all four value statuses
(`PRESENT`/`MISSING`/`UNKNOWN`/`NOT_APPLICABLE`).

## What is inside

```text
manifest.json          format version, export record, array shapes and dtypes
experiment.json        metadata, instrument, samples, scans
provenance.json        inherited import provenance + the export record
arrays/radius.npy      radius values
arrays/signal.npy      signal values, always 2-D (scan, point)
arrays/mask.npy        authoritative boolean validity mask, always 2-D
checksums.sha256       SHA-256 of every other member
```

It is an ordinary ZIP — `unzip -l demo.aucx` works. Numeric data is stored as
`.npy` so dtype, shape and the mask survive exactly, with no tabular
re-encoding and no heavy dependency.

## Inspect an archive

```python
info = openauc.inspect_aucx("demo.aucx")
info.aucx_format_version  # '1.0'
info.radius_axis_mode  # RadiusAxisMode.SHARED
info.n_scans, info.n_points
info.checksum_verified  # True
info.export.exported_at  # when it was written
info.members  # every member name
```

`inspect_aucx` **verifies every checksum** and raises on any problem.

## Validate an archive without raising

```python
report = openauc.validate_aucx("demo.aucx")
report.is_valid  # bool
for issue in report.issues:
    print(issue.code, issue.message)
```

Container-level only. Structural validation of the experiment inside is a
separate question — load it and use `validate()`.

```bash
uv run openauc validate demo.aucx --readiness
```

## Overwrite protection

```python
experiment.export("demo.aucx")  # ArchiveError if it exists
experiment.export("demo.aucx", overwrite=True)  # replaces it
```

Writes are **atomic**: a temporary sibling file is written, read back and
verified in full, and only then moved into place. A failure never leaves a
partial archive at the destination.

## Deterministic export

Two exports of equivalent experiments with the same `exported_at` are
**byte-identical**:

```python
from datetime import UTC, datetime

fixed = datetime(2026, 1, 1, tzinfo=UTC)
a = experiment.export("a.aucx", exported_at=fixed)
b = experiment.export("b.aucx", exported_at=fixed)
assert a.read_bytes() == b.read_bytes()
```

Achieved by fixing member order, ZIP timestamps, permission bits, creator
system and compression, and writing JSON with sorted keys. Omit `exported_at`
and the current UTC time is used, which is what a normal export wants.

## Integrity, not authenticity

!!! warning
    A verified archive is one whose **bytes are unchanged** since it was
    written. SHA-256 here proves nothing about *who* wrote it. AUCX carries no
    signature, and signing is out of scope for version 1.0.

## Common failure modes

| Error | Cause |
|-------|-------|
| `ArchiveIntegrityError: checksum mismatch for ...` | The archive was modified or is corrupt |
| `ArchiveIntegrityError: ... lists ..., which is missing` | A member was removed |
| `ArchiveVersionError: unsupported AUCX format version` | Written by a newer build — archives are never migrated silently |
| `ArchiveError: ... is not a readable ZIP archive` | Not an archive, or truncated |
| `ArchiveError: refusing to overwrite existing file` | Pass `overwrite=True` / `--overwrite` |

More: [Verify an AUCX archive](../how-to/verify-an-aucx-archive.md).

## Next step

- [AUCX format specification](../formats/aucx.md)
- [Provenance and checksums](../concepts/provenance-and-checksums.md)
