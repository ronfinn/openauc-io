# Contributing to openauc-io

Thanks for your interest in `openauc-io`. This project is in its **pre-alpha
foundation** stage; APIs and structure will change. Contributions, issues and
design discussion are welcome.

## Development setup

Requires [uv](https://docs.astral.sh/uv/) and a supported Python (3.11–3.13).

```bash
git clone https://github.com/ronfinn/openauc-io
cd openauc-io
uv sync
uv run pre-commit install   # optional: run checks on each commit
```

## Running checks

All checks are run in CI across Python 3.11, 3.12 and 3.13. Run them locally
before opening a pull request:

```bash
uv run ruff check .      # lint
uv run ruff format .     # format (use --check to verify only)
uv run mypy              # static type checking (strict)
uv run pytest            # tests with coverage
```

## Project conventions

- **src layout**, packaged with `hatchling`, managed with `uv`.
- **Typed**: the package ships `py.typed`; `mypy` runs in strict mode.
- **Public API**: exported through `openauc/api.py`. Internal module paths are
  not part of the public contract — export new public symbols through the facade.
- **Style**: enforced by `ruff` (lint + format). Do not hand-format around it.

## Architecture Decision Records

Non-trivial design choices are recorded as ADRs in `docs/decisions/`. Propose a
new ADR (status `Proposed`) before implementing a decision it would govern. The
current ADRs are ADR-0001 (package architecture), ADR-0002 (canonical data
model), ADR-0003 (AUCX container) and ADR-0004 (parser plugin registry).

The `development-log/` directory records session-level context and the phased
roadmap.

## Scientific and licensing boundaries

These are binding on all contributions:

- **Independent implementation.** Do not copy source code or reproduce
  proprietary interfaces from SEDFIT, SEDPHAT, UltraScan, GUSSI, AUCAgent or
  other closed or incompatibly licensed software.
- **No fabricated format rules.** Do not invent undocumented behaviour for
  existing third-party formats. Public specifications and literature may be
  cited as references, with provenance kept clear.
- **No silent inference.** Missing required scientific metadata must fail
  validation loudly; radial data must not be silently interpolated or resampled.
- **Honest claims.** Do not claim support for untested formats or scientific
  validation that has not been performed.
- **No bundled third-party binaries.**
- **Test data** must be synthetic or provably redistributable.

By contributing you agree that your contributions are licensed under the
project's Apache License 2.0.
