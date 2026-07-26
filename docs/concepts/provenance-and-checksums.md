# Provenance and checksums

Provenance records **where data came from and what was done to it**. It is a
representation, not an audit claim, and nothing in it is inferred.

## What is recorded on import

`openauc.load` attaches an `ImportProvenance` to every imported experiment:

```python
p = experiment.provenance
p.source_path, p.source_filename
p.parser_name, p.parser_version      # e.g. 'generic-long', '0.1.0a1'
p.imported_at                        # UTC timestamp
p.sha256                             # digest of the primary data file
p.source_checksums                   # one typed entry per source file
p.warnings, p.assumptions
```

## Per-source checksums

A manifest-driven import reads **at least two files**, so a single digest could
not honestly say what it covered. Each source is recorded separately:

```python
for entry in experiment.provenance.source_checksums:
    print(entry.role, entry.filename, entry.value[:12], entry.byte_size)
# manifest   manifest.json  f0094387c0e3 1165
# data_file  scans.csv      e3d909e5d628  251
```

| Field | Meaning |
|-------|---------|
| `role` | What the file was to the import: `manifest`, `data_file` |
| `filename` | The file's name |
| `algorithm` | `"sha256"` |
| `value` | 64 lowercase hex characters |
| `byte_size` | Size in bytes, or `None` |

`ImportProvenance.sha256` is retained and mirrors the `data_file` entry, for the
common single-file case.

## Value-level provenance

Separately from the file level, each `Quantity` records where its value came
from via `ValueProvenance`: `SUPPLIED`, `CONVERTED`, `INFERRED`,
`USER_CONFIRMED`, `UNKNOWN`.

`CONVERTED` exists for a future in which explicit conversions are introduced.
**Nothing in openauc converts anything today**, so no value is ever tagged
`CONVERTED` by the library itself.

## Generated data

A synthetic experiment records what the generator actually did, and **invents no
source**:

```python
p = generated.provenance
p.parser_name       # 'openauc.synthetic'
p.source_path       # None — nothing was read from disk
p.sha256            # None
p.transformations   # ('generated scenario=moving-boundary',)
p.assumptions       # the synthetic disclaimer, seed, noise level
```

## Archive provenance

An AUCX archive keeps two records apart in `provenance.json`:

- **`import`** — the experiment's own `ImportProvenance`, unchanged. It travels
  with the model, so a round trip preserves it and
  `restored.to_dict() == original.to_dict()`.
- **`export`** — the AUCX export event: format version, software name and
  version, export timestamp, checksum algorithm.

The export record is reached with `openauc.inspect_aucx(path)`, deliberately
**not** grafted onto the restored experiment. The experiment's provenance is
about where the *data* came from, not about the archive that happens to carry
it.

```python
info = openauc.inspect_aucx("demo.aucx")
info.export.software, info.export.software_version, info.export.exported_at
```

## Archive checksums

Every archive member except `checksums.sha256` is checksummed. The file is a
classic digest listing, sorted by member name:

```text
<64 lowercase hex digits><two spaces><member name>
```

On load, in order: the file must exist; every line must parse; every listed
member must be present; **every digest must match**; and no unlisted member may
exist. All of this completes **before any model is constructed**.

## Integrity is not authenticity

!!! warning
    A verified checksum shows the **bytes are unchanged** since they were
    written or read. It proves nothing about **who** produced them.

    AUCX carries no signature, and signing is out of scope for version 1.0.
    Do not treat a passing archive as evidence of origin, authorship or
    approval.

The same applies to source checksums: they let you detect that a source file
changed after import, nothing more.

## What provenance is not

- Not a lab notebook. It records what openauc did, not what you did.
- Not tamper-proof. Anyone who can rewrite an archive can rewrite its checksums;
  what they cannot do is change one member and leave the digests consistent
  *by accident*.
- Not inferred. If openauc did not observe something, it is absent rather than
  guessed.

## Next step

- [AUCX format](../formats/aucx.md)
- [Verify an AUCX archive](../how-to/verify-an-aucx-archive.md)
