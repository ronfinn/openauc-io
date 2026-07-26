# Security

--8<-- "SECURITY.md"

## What openauc does defensively

### Archives

Reading an `.aucx` file rejects, before allocating anything:

- absolute member paths, `..` traversal and backslash-separated names;
- duplicate member names;
- encrypted members;
- members declaring more than 512 MiB, or 2 GiB in total.

Arrays are loaded with `allow_pickle=False` and object arrays are rejected, so
**reading an archive can never execute code**. Archives are never extracted to
disk.

### Manifests

`data_file` must be a safe relative path. Absolute paths, `..` and drive-letter
forms are rejected, so a manifest cannot reach outside its own directory.

### Checksums

Every archive member except the checksum file is checksummed, and **every digest
is verified before any model is constructed**.

!!! warning "Integrity, not authenticity"
    A verified archive is one whose **bytes are unchanged** since it was
    written. SHA-256 here proves nothing about **who** wrote it. AUCX carries no
    signature, and signing is out of scope for version 1.0.

    Do not treat a passing archive as evidence of origin, authorship or
    approval.

## Reporting a problem

Use the process in `SECURITY.md` above. Please include the openauc version
(`openauc version`), the platform, and a **synthetic** reproduction — never
attach real or confidential experimental data.
