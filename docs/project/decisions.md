# Architecture decisions

Every load-bearing choice is recorded as an Architecture Decision Record in
[`docs/decisions/`](https://github.com/ronfinn/openauc-io/tree/main/docs/decisions),
amended rather than rewritten as implementation proceeded.

| ADR | Subject | Status |
|-----|---------|--------|
| [ADR-0001](https://github.com/ronfinn/openauc-io/blob/main/docs/decisions/ADR-0001-python-package-architecture.md) | Python package architecture | Accepted (amended with the as-built layout) |
| [ADR-0002](https://github.com/ronfinn/openauc-io/blob/main/docs/decisions/ADR-0002-canonical-data-model.md) | Canonical in-memory data model | Accepted (amended for Phase 2 and Phase 4) |
| [ADR-0003](https://github.com/ronfinn/openauc-io/blob/main/docs/decisions/ADR-0003-aucx-container-format.md) | AUCX container format | Accepted (amended with the implemented structure) |
| [ADR-0004](https://github.com/ronfinn/openauc-io/blob/main/docs/decisions/ADR-0004-parser-plugin-registry.md) | Parser plugin registry | Accepted |

## What each settled

### ADR-0001 — package architecture

src layout, hatchling, uv, a curated `api.py` facade, PEP 561 typing, and the
`tests/unit` / `tests/integration` / `tests/cli` split with synthetic-only
fixtures. The Phase 4 amendment records the as-built layout: the registry lives
under `formats/`, validation and readiness under `models/`, and the top-level
`validation/` package stays **reserved** for future scientific quality control.

### ADR-0002 — canonical data model

pydantic v2 for metadata, xarray for the numeric layer, and — the load-bearing
choice — **both** radius-axis regimes supported explicitly with **no silent
interpolation**. Per-scan axes use padded arrays with an authoritative validity
mask.

Any future operation that places per-scan data onto a common grid must be an
explicit, opt-in transformation recording its interpolation choice. No such
operation exists today, which is why
[wide export refuses ragged data](../how-to/per-scan-radius-axes.md).

The Phase 4 amendment resolves Q3 and records the validation-tier model.

### ADR-0003 — AUCX

A zip of parts rather than a single binary file: no compiled backend, and
inspectable with ordinary tools. The Phase 6 amendment records NumPy `.npy` for
arrays and JSON for metadata, and confirms SHA-256 — with per-source checksum
entries, because one digest could not honestly describe a two-file import.

### ADR-0004 — parser registry

Decorator registration with confidence-based detection, a minimum confidence and
a tie margin, so ambiguity raises rather than guesses. AUCX is registered as an
**archive format** rather than a `Parser`, because the parser interface assumes
a delimited table.

## Development logs

Each phase has a log recording accepted decisions, rejected alternatives,
limitations and next steps —
[`development-log/`](https://github.com/ronfinn/openauc-io/tree/main/development-log).
They are the record of *why*, where the ADRs record *what*.

## Next step

- [Contributing](contributing.md)
