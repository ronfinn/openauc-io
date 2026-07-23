# ADR-0001 — Python package architecture

- **Status:** Proposed
- **Date:** 2026-07-23
- **Deciders:** Ron Finn
- **Related:** ADR-0002, ADR-0003, ADR-0004; development-log/0001

## Context

`openauc-io` is a new open-source scientific Python library (distribution and
import name `openauc`) targeting Python 3.11, 3.12 and 3.13. It must be
installable, typed, testable, and maintainable by a small team, and it must
present a clear public API distinct from internal implementation details. The
project has fixed several tooling constraints up front: `uv` for environment and
dependency management, `hatchling` as the build backend, an Apache-2.0 licence,
and a src layout.

The library will grow from a narrow first release (tabular import, validation,
plotting, AUCX archival) toward broader format support, so the architecture must
allow subpackages to evolve independently without destabilising the public
surface.

## Decision under consideration

Adopt a **src layout** package built with **hatchling** and managed with **uv**,
structured as:

- A thin public facade in `src/openauc/api.py` re-exporting the supported
  public functions and types. Downstream users import from `openauc` /
  `openauc.api`; internal module paths are not part of the API contract.
- Internal subpackages: `models/`, `formats/` (with `readers/` and `writers/`),
  `validation/`, `plotting/`, `utilities/`, plus `registry.py` (ADR-0004) and
  `exceptions.py` (a single library exception hierarchy).
- A `cli.py` module exposing a Typer application, wired as a console-script
  entry point in Phase 1.
- PEP 561 typing: ship a `py.typed` marker; `mypy` runs in CI.
- Quality tooling: `ruff` (lint + format), `mypy` (type check), `pytest` +
  `pytest-cov` (tests), `pre-commit` (local gate).
- Tests organised as `tests/unit`, `tests/integration`, `tests/cli`, with
  synthetic-only fixtures under `tests/fixtures`.

No packaging files, CI, or code are created in this ADR's originating session;
this ADR records the intended architecture for Phase 1.

## Alternatives considered

- **Flat layout** (package directly at repository root). Rejected: src layout
  prevents accidental imports of the in-tree package instead of the installed
  one, which is the standard recommendation for tested libraries.
- **setuptools / PDM / poetry-core build backends.** Rejected in favour of
  `hatchling`, which is lightweight, standards-based (PEP 517/621), and already
  chosen for the project. `uv` drives the workflow regardless of backend.
- **Exposing subpackage modules directly as the public API** (no facade).
  Rejected: it freezes internal structure into the compatibility contract and
  makes later refactors breaking changes. A curated `api.py` decouples the two.
- **Deferring typing / no `py.typed`.** Rejected: shipping types from day one is
  cheap for a greenfield project and valuable to scientific users in typed
  codebases.

## Consequences

**Positive**

- Clean separation between a small, stable public API and evolving internals.
- Reliable test isolation from the src layout.
- Typed, linted, formatted from the first line of code; low retrofit cost.
- Subpackages map directly onto the roadmap phases, so work parallelises.

**Negative / costs**

- A facade must be maintained deliberately; contributors must remember to export
  new public symbols through `api.py`.
- Slightly more initial ceremony (marker files, tool config) before feature work.

## Unresolved questions

- The exact `pyproject.toml` dependency pins and optional-dependency groups
  (e.g. `docs`, `dev`) are settled in Phase 1, not here.
- Console-script name(s) for the CLI depend on the CLI command surface
  (development-log Q7).
- Documentation tooling (MkDocs-Material vs Sphinx) is out of scope for this ADR
  (development-log Q6).

## References

- PEP 517 / PEP 621 — build-system and project metadata standards.
- PEP 561 — distributing and packaging type information.
- Hatchling and uv official documentation.
- The Python Packaging User Guide, "src layout vs flat layout".
