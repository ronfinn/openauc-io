# Format specifications

Open specifications authored by this project:

- **[AUCX](aucx.md)** — the versioned zip-of-parts archival container
  (`docs/decisions/ADR-0003`). JSON metadata plus NumPy `.npy` arrays, with
  SHA-256 integrity checking.
- **[Experiment manifest](manifest-v1.md)** — JSON (canonical) and YAML
  (authoring) schema.
- **[Generic delimited](generic-delimited.md)** — long and wide CSV/TSV.

Third-party format:

- **[Beckman XL-I `.ip1`](ip1.md)** — one narrow, documented interference scan
  layout. Not general Beckman support.

This project does **not** reverse-engineer third-party instrument formats; the
`.ip1` reader follows the manufacturer's published manual.
