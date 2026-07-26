# `openauc formats`

List every format this build can read, with its stable identifier, suffixes,
layouts and limitations.

## Syntax

```bash
openauc formats [--json]
```

## Options

| Option | Meaning |
|--------|---------|
| `--json` | Emit machine-readable JSON instead of text |

## Example

```bash
uv run openauc formats
```

```text
aucx  AUCX archive
  suffixes:    .aucx
  layouts:     zip-of-parts (JSON metadata + NumPy .npy arrays)
  limitations: format version 1.0 only; archives are never migrated silently
               every checksum is verified before a model is built
               checksums establish integrity, not authenticity
  docs:        docs/formats/aucx.md
generic-long  Generic long-format delimited
  suffixes:    .csv, .tsv
  layouts:     long
  limitations: one signal unit per file; no vendor-specific columns; requires a manifest for experiment identity
  docs:        docs/formats/generic-delimited.md
generic-wide  Generic wide-format delimited
  suffixes:    .csv, .tsv
  layouts:     wide
  limitations: scans must share one radius axis; requires a manifest column mapping
  docs:        docs/formats/generic-delimited.md
```

## JSON output

```bash
uv run openauc formats --json | jq -r '.formats[] | "\(.format_id): \(.name)"'
```

```text
aucx: AUCX archive
generic-long: Generic long-format delimited
generic-wide: Generic wide-format delimited
```

Each entry carries `format_id`, `name`, `suffixes`, `layouts`, `limitations`
and `doc_reference`.

## Exit codes

| Code | When |
|------|------|
| 0 | Always |

## Notes

The `format_id` values are stable and are what you pass to
`openauc.load(path, format=...)` or a manifest's `"format"` field.

**No vendor or instrument formats are listed, because none are implemented.**
