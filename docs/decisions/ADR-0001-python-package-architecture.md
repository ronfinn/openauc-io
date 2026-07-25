# ADR-0001 — Python package architecture

- **Status:** Accepted (amended — see the Phase 4 as-built amendment below)
- **Date:** 2026-07-23 (proposed); amended and accepted 2026-07-25 (Phase 4)
- **Deciders:** Ron Finn
- **Related:** ADR-0002, ADR-0003, ADR-0004; development-log/0001;
  development-log/0004

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

---

## Amendment — as-built architecture (Phase 4, 2026-07-25)

This ADR was written before any code existed and described an intended layout.
The status is changed to **Accepted** only now, and only alongside this
amendment, so that the ADR describes the package that actually exists rather
than one that was planned. The load-bearing decisions — src layout, hatchling,
uv, a curated `api.py` facade, PEP 561 typing, and the `tests/unit`,
`tests/integration`, `tests/cli` split with synthetic-only fixtures — were all
implemented as written and are confirmed.

The following points differ from the original text and are corrected here.

**`registry.py` lives under `formats/`, not at the package root.** The original
sketch placed the parser registry at `src/openauc/registry.py`. It is
implemented as `src/openauc/formats/registry.py`, alongside the parser
interface (`formats/base.py`), the manifest model (`formats/manifest.py`), the
loader (`formats/loader.py`) and the first-party parsers. The registry only ever
serves the ingestion layer, so keeping it inside that layer avoids a top-level
module with a single consumer. ADR-0004 is unaffected.

**Structural validation and readiness live under `models/`, not in a top-level
`validation/` package.** As-built:

| Module | Contents |
|--------|----------|
| `models/validation.py` | `ValidationIssue`, `ValidationReport`, `validate_experiment`, `validate_experiment_structure` |
| `models/checks.py` | the ordered check registry |
| `models/readiness.py` | `ReadinessAssessment`, `AnalysisReadiness`, routing |
| `models/summary.py` | `ExperimentSummary` and its text renderer |

These operate exclusively on the canonical model and are meaningless without it,
so they sit with it. This continues the placement already recorded in the
ADR-0002 Phase 2 amendment.

**The top-level `validation/` package remains reserved.** It is deliberately
unclaimed, for future *scientific* or cross-cutting quality control — the
category that `openauc` does not implement today and that must never be confused
with structural validation or readiness reporting. Nothing in Phase 4 was placed
there.

**`plotting/`, `formats/readers/`, `formats/writers/` and `utilities/` do not
exist yet.** They remain planned:

- `plotting/` — the plotting phase;
- AUCX read/write and checksum/provenance helpers — the AUCX phase;
- a `readers/`/`writers/` split under `formats/` — deferred until there are
  enough parsers to justify it. Two first-party parsers in one module is not yet
  a reason to subdivide.

**Consequence.** The facade cost predicted in the original "Negative / costs"
section is real and recurring: every phase has had to export new public symbols
through both `models/__init__.py` and `api.py`. This has worked, but it is a
manual step that a contributor can forget; the test suite asserting the public
surface is what catches it.
