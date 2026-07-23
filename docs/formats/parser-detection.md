# Parser selection and detection

The ingestion layer selects a parser deterministically and refuses to guess when
the outcome is ambiguous. See [ADR-0004](../decisions/ADR-0004-parser-plugin-registry.md).

## Selection precedence

1. **Explicit override** — `openauc.load(path, format="generic-long")`.
2. **Manifest-declared format** — the manifest's `format` field.
3. **Detection** — used only when neither is supplied (the manifest omits
   `format`).

An explicit or declared format goes straight to parsing, which yields precise
structural errors (e.g. missing required columns) if the file does not match.

## Confidence-based detection

Each parser exposes a `detect()` method returning a `DetectionResult`:

- `parser_id`
- `confidence` in the range `0.0`–`1.0`
- `evidence` (why it is/ isn't confident)
- `warnings`

`detect_parser()` picks the highest-confidence parser subject to two guards:

- **Minimum confidence** (`0.5`): if no parser clears it, `UnsupportedFormatError`.
- **Tie margin** (`0.15`): if two viable parsers are within this margin,
  `AmbiguousFormatError`.

`generic-long` is confident when the required columns (`scan`, `radius_cm`,
`signal`) are present. `generic-wide` requires a manifest column mapping, so it is
not detected from data alone.

## Delimiter detection

Comma and tab are supported. The delimiter is resolved deterministically:

1. an explicit manifest `delimiter`, if given (verified against the data);
2. otherwise, the delimiters under which the table has a **consistent field
   count** (≥ 2 columns, equal across all rows) are computed;
3. if exactly one is consistent, it is used;
4. if both are, the file **suffix** (`.csv` → comma, `.tsv` → tab) breaks the tie;
5. otherwise `AmbiguousFormatError` is raised.

The file extension alone is never trusted, and arbitrary delimiter guessing is
not supported in this phase.

## Discovering formats

```python
import openauc

for info in openauc.available_formats():
    print(info.format_id, "-", info.name, info.suffixes, info.layouts)
```

`available_formats()` reports only the parsers actually registered, so it never
overclaims support.

## Errors

| Exception | When |
|-----------|------|
| `UnsupportedFormatError` | no parser is confident enough, or an unknown `format=` id |
| `AmbiguousFormatError` | tied detection, ambiguous delimiter, or two manifests present |
| `ManifestError` | invalid/unsafe manifest, bad schema version, unsafe path |
| `ParseError` | malformed data: missing columns, non-finite/non-numeric values |
| `DataConflictError` | duplicate observations, or table/manifest metadata disagreement |
