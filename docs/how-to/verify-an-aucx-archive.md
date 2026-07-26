# Verify an AUCX archive

**Goal:** confirm an archive is intact before trusting its contents.

## Quickest check

```bash
uv run openauc validate demo.aucx
echo "exit: $?"
```

```text
archive integrity: OK (demo.aucx)
structural validation: OK (no issues)
```

Integrity is checked **first**. A broken container exits `2` without pretending
to have examined the experiment.

## Python, raising

```python
import openauc

info = openauc.inspect_aucx("demo.aucx")  # raises on any problem
info.checksum_verified  # True
info.aucx_format_version  # '1.0'
info.n_scans, info.n_points
info.members
info.export.exported_at, info.export.software_version
```

## Python, not raising

```python
report = openauc.validate_aucx("demo.aucx")
if not report.is_valid:
    for issue in report.issues:
        print(issue.code, "-", issue.message)
```

Useful when sweeping a directory.

## What is checked

1. The ZIP is readable, with no member using an absolute path, `..` traversal
   or backslashes.
2. No duplicate member names, no encrypted members.
3. No member declares more than 512 MiB, or 2 GiB in total, **before**
   allocating.
4. `checksums.sha256` exists and every line parses.
5. Every listed member is present, and **every digest matches**.
6. No member exists that the checksum file does not list.
7. The manifest declares a supported `aucx_format_version`.
8. Arrays load with `allow_pickle=False`; object arrays are rejected; shapes and
   dtypes agree with the manifest.

**All of this completes before any model is constructed.** Nothing is reported
valid before verification succeeds.

!!! warning "Integrity, not authenticity"
    A verified archive is one whose bytes are unchanged since it was written.
    SHA-256 proves nothing about *who* wrote it. AUCX carries no signature.

## Failure modes

| Error | Cause | Data at risk? |
|-------|-------|---------------|
| `ArchiveIntegrityError: checksum mismatch for 'x'` | Modified or corrupt | Yes — do not trust it; recover from another copy |
| `ArchiveIntegrityError: ... lists 'x', which is missing` | A member was removed | Yes |
| `ArchiveIntegrityError: ... has no checksums.sha256` | Not written by openauc, or stripped | Yes |
| `ArchiveIntegrityError: contains member(s) [...] that checksums.sha256 does not list` | Something was added | Yes |
| `ArchiveVersionError: unsupported AUCX format version '2.0'` | Written by a newer build | No — upgrade openauc; archives are never migrated silently |
| `ArchiveError: ... is not a readable ZIP archive` | Not an archive, or truncated | Yes |
| `ArchiveError: ... contains duplicate member` | Malformed ZIP | Yes |
| `ArchiveError: member name traverses directories` | Hostile or malformed | Yes — do not use it |
| `ArchiveError: ... contains an object array` | Not written by openauc | Yes |

## Sweeping a directory

```python
from pathlib import Path
import openauc

for path in sorted(Path("archives").glob("*.aucx")):
    report = openauc.validate_aucx(path)
    print(f"{'OK  ' if report.is_valid else 'FAIL'} {path.name}")
    for issue in report.issues:
        print("     ", issue.code, "-", issue.message)
```

## Next step

- [AUCX format specification](../formats/aucx.md)
- [Provenance and checksums](../concepts/provenance-and-checksums.md)
