# Development Log 0001 — Project Foundation

- **Date:** 2026-07-23
- **Branch:** `feat/project-foundation`
- **Status:** Phase 0 (foundation docs) complete; Phase 1 (packaging skeleton)
  complete. No scientific/model/parser code written.
- **Author:** Ron Finn

---

## 1. Project objective

`openauc-io` is an open-source Python library (package name `openauc`) for
importing, validating, standardising, visualising and archiving analytical
ultracentrifugation (AUC) data.

The long-term goal is to support historical and modern AUC formats. The **first
alpha release** is deliberately narrow: generic long- and wide-format CSV/TSV
radial-scan data, JSON/YAML experiment manifests, a canonical in-memory
experiment model, structural validation, scan summaries, basic plotting, and a
new versioned archival container called **AUCX** (`.aucx`), plus a command-line
interface and complete documentation.

This project is **not** intended, at this stage, to replace SEDFIT, SEDPHAT,
UltraScan, GUSSI, or any other established AUC analysis software. It performs no
sedimentation modelling or fitting in the first release.

## 2. Current repository state

At the start of this session the repository contained three tracked files and a
single commit (`4faa554 Initial commit`) on `main`:

| File | State |
|------|-------|
| `LICENSE` | Stock, unmodified Apache License 2.0. The copyright line in the appendix is the unfilled placeholder `Copyright [yyyy] [name of copyright owner]`. |
| `README.md` | Two lines: title and the one-sentence project description. |
| `.gitignore` | Standard 218-line GitHub Python template, unmodified. |

The remote branch `feat/project-foundation` existed but was byte-identical to
`main` (an empty placeholder). No `pyproject.toml`, `src/` layout, tests, CI, or
community-health files were present.

There is therefore no legacy code, no prior architecture, and no third-party
code of uncertain provenance to reconcile. The project starts clean.

## 3. Proposed architecture

Target layout (src layout, `hatchling` build backend, `uv` for environment and
dependency management):

```
openauc-io/
├── src/openauc/
│   ├── __init__.py
│   ├── py.typed                 # PEP 561 marker — ship type information
│   ├── api.py                   # top-level public API surface
│   ├── cli.py                   # Typer CLI entry point
│   ├── exceptions.py            # library exception hierarchy
│   ├── registry.py              # parser plugin registry (ADR-0004)
│   ├── models/                  # pydantic + xarray canonical model (ADR-0002)
│   ├── formats/                 # readers/ and writers/ (tabular, manifest, AUCX)
│   ├── validation/              # structural validation
│   ├── plotting/                # matplotlib scan plots
│   └── utilities/               # units, checksums, provenance helpers
├── tests/
│   ├── conftest.py
│   ├── fixtures/                # tiny synthetic CSV/TSV/AUCX only
│   ├── unit/  integration/  cli/
├── schemas/                     # versioned JSON Schema for manifest + AUCX
├── examples/
├── docs/
│   ├── decisions/               # Architecture Decision Records
│   ├── formats/                 # AUCX and manifest specifications
│   └── concepts/                # domain and data-model concepts
├── development-log/
├── .github/                     # workflows, issue/PR templates (Phase 1)
├── pyproject.toml               # (Phase 1)
├── README.md  CHANGELOG.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md
├── SECURITY.md  CITATION.cff  NOTICE  LICENSE
```

The four decisions captured this session are recorded in
`docs/decisions/ADR-0001`..`ADR-0004`. The load-bearing architectural choices:

- **Package architecture** (ADR-0001): src layout, `hatchling`, `uv`, a thin
  `api.py` facade over internal subpackages, PEP 561 typed.
- **Canonical data model** (ADR-0002): pydantic v2 for metadata; `xarray` for
  the numeric `(scan × radius)` signal arrays; support for **both** a shared
  radius axis and per-scan radius axes, with **no silent interpolation**.
- **AUCX container** (ADR-0003): a **zip-of-parts** archive (manifest + data
  parts + checksum manifest), tool-agnostic and inspectable, no compiled
  backend required.
- **Parser plugin registry** (ADR-0004): an internal decorator-based registry
  for first-party formats, with optional `importlib.metadata` entry-point
  discovery for third-party plugins.

## 4. Dependency decisions

### Runtime dependencies

| Dependency | Constraint (indicative) | Why it is required |
|------------|-------------------------|--------------------|
| `pydantic` | `>=2.7,<3` | Metadata models, manifest parsing, structural validation with precise error locations. v2 for performance and strict mode. |
| `numpy` | `>=1.26,<3` | Numeric radial and signal arrays — the substrate everything numeric builds on. 1.26 is the first cp312 wheel line; 2.x permitted. |
| `xarray` | `>=2024.3` | Labelled `(scan × radius)` arrays with per-scan coordinates (time, rpm, temperature, wavelength). The natural in-memory shape for radial-scan data. |
| `pandas` | `>=2.2` | **Tabular import only** (`read_csv`/`read_table`). Not part of the canonical model's public surface. |
| `PyYAML` | `>=6` | YAML authoring path for experiment manifests (JSON remains canonical). Added as a direct consequence of the JSON+YAML manifest decision. |
| `matplotlib` | `>=3.8` | Basic scan plotting. |
| `typer` | `>=0.12` | Command-line interface; pulls `click`. |

### Development dependencies

`pytest>=8`, `pytest-cov`, `ruff>=0.5`, `mypy>=1.10`, `pre-commit`.

### Deliberately deferred (flagged, not adopted)

- A NetCDF/HDF5 backend (`h5netcdf`/`netCDF4`) — **not** required, because
  ADR-0003 selects a zip-of-parts container rather than a single binary file.
- `pyarrow` — only relevant if in-archive data parts use Parquet; the encoding
  of AUCX data parts remains an open question (see §8).

## 5. Licensing considerations

- **Licence:** Apache License 2.0. The `LICENSE` file is present but its
  copyright placeholder is unfilled. The agreed copyright holder is **Ron Finn**.
  Filling the placeholder and adding a `NOTICE` file are **Phase 1** actions and
  were intentionally not performed this session.
- **Provenance:** this is an independently implemented project. No source code,
  format-parsing logic, or GUI layouts are to be copied from SEDFIT, SEDPHAT,
  UltraScan, GUSSI, AUCAgent, or any other closed or incompatibly licensed
  software. Public scientific literature and public format specifications may be
  cited as references, but implementation provenance must remain clear.
- **AUCX authorship:** AUCX is a **new format defined by this project**.
  Specifying its rules is original authorship, not reverse-engineering of a
  third-party format, and therefore does not conflict with the boundary against
  fabricating undocumented rules for *existing* formats.
- **Test fixtures:** all fixtures must be synthetic or provably redistributable.
  No undocumented real instrument dumps are to be committed.
- **No bundled third-party binaries.**

## 6. Scientific boundaries

The following boundaries are binding on all subsequent work:

- No copying of code or proprietary GUI designs from established AUC software.
- No fabrication of undocumented file-format rules for existing formats. The
  first release parses only *generic* CSV/TSV plus the project's own AUCX; no
  XL-A/XL-I, Optima, or other instrument formats are parsed in v1, so no
  reverse-engineering is undertaken.
- No silent inference of missing scientific metadata — missing required
  metadata must fail validation loudly.
- No silent interpolation or resampling of radial data — the canonical model
  preserves the acquired radius axis (or axes) faithfully.
- No claims of support for formats that have not been tested.
- No claims of scientific validation that has not been performed. README,
  CITATION, and documentation must reflect only what has actually been verified.

## 7. Known risks

| # | Category | Risk | Mitigation / where addressed |
|---|----------|------|------------------------------|
| R1 | Scientific | Scans in a set may not share an identical radius axis; a dense `(scan × radius)` array would require interpolation, which would alter data. | ADR-0002: support both shared and per-scan axes; never interpolate silently. |
| R2 | Scientific | Ambiguous or missing units (radius cm, rpm, temperature, wavelength nm, absorbance vs interference fringes). | Require explicit, declared canonical units; reject rather than convert on conflict (open question Q5). |
| R3 | Format | A new versioned format can become unreadable across versions without an explicit version field and migration story. | ADR-0003: mandatory format-version field from v0.1; forward-compatibility policy documented. |
| R4 | Technical | Committing to a compiled NetCDF/HDF5 backend risks wheel-availability friction across 3.11–3.13. | Avoided by choosing a zip-of-parts container (ADR-0003). |
| R5 | Licensing | Unfilled LICENSE copyright; missing NOTICE; risk of provenance contamination. | Fill LICENSE + add NOTICE in Phase 1 (holder: Ron Finn); enforce clean-room provenance. |
| R6 | Scope / comms | Overclaiming format support or scientific validation. | Documentation constrained to verified capabilities only. |

## 8. Unresolved questions

Resolved this session:

- **AUCX container** → zip-of-parts.
- **Radial grids** → support both shared and per-scan axes, no silent interpolation.
- **Manifest format** → JSON canonical, YAML supported for authoring.
- **Copyright holder** → Ron Finn.

Still open (do not block Phase 0; must be resolved before the phases noted):

- **Q1 — In-archive data encoding** (before Phase 6): Parquet, NetCDF, `.npy`,
  or plain CSV for the data parts inside a `.aucx` zip?
- **Q2 — Canonical units** (before Phase 2): which units are mandatory-and-declared,
  and does the model reject rather than convert on mismatch?
- **Q3 — Minimum valid-experiment metadata set** (before Phase 4): what must be
  present for structural validation to pass?
- **Q4 — Optical systems in the v1 model** (before Phase 2): absorbance only, or
  absorbance + interference (+ a fluorescence stub)?
- **Q5 — Provenance record schema** (before Phase 6): exact fields captured, and
  confirmation of SHA-256 as the checksum algorithm (currently assumed).
- **Q6 — Documentation tooling** (before Phase 8): MkDocs-Material vs Sphinx.
- **Q7 — CLI command surface** (before Phase 7): the initial verb set.

## 9. Phased roadmap

- **Phase 0 — Foundation (this session):** development log + four ADR drafts.
  No code.
- **Phase 1 — Packaging skeleton:** `pyproject.toml` (hatchling, deps, tool
  config), community-health files, CI, `NOTICE`, filled `LICENSE`. Still no
  scientific code.
- **Phase 2 — Canonical model:** pydantic metadata + xarray experiment container
  (resolve Q2, Q4).
- **Phase 3 — Tabular ingest:** long- and wide-format CSV/TSV readers + JSON/YAML
  manifest.
- **Phase 4 — Validation & scan summaries** (resolve Q3).
- **Phase 5 — Plotting:** basic matplotlib scan plots.
- **Phase 6 — AUCX:** zip-of-parts export/reload + checksums + provenance
  (resolve Q1, Q5).
- **Phase 7 — CLI:** Typer command surface (resolve Q7).
- **Phase 8 — Docs & alpha release** `0.1.0a1` (resolve Q6).

## 9a. Phase 1 completion record (2026-07-23)

Phase 1 delivered the packaging, tooling and community scaffolding. **No
canonical model or parser was implemented** — the package contains only
importable stubs so the toolchain can be exercised.

**Created**

- `pyproject.toml` — hatchling backend, src layout, dynamic version from
  `src/openauc/__init__.py`, runtime dependencies (pydantic, numpy, xarray,
  pandas, PyYAML, matplotlib, typer), a `dev` dependency group, and tool config
  for ruff, mypy (strict), pytest and coverage. Console script `openauc`.
- Package skeleton: `src/openauc/__init__.py` (version `0.1.0.dev0`), `py.typed`,
  `exceptions.py` (exception hierarchy — declarations only), `api.py` (public
  facade), `cli.py` (Typer app with a `version` command and a root callback).
- Tests: `tests/conftest.py`, `tests/unit/test_package.py`,
  `tests/cli/test_cli.py`, plus `tests/fixtures/README.md`.
- Directory placeholders: `schemas/README.md`, `examples/README.md`,
  `docs/formats/README.md`, `docs/concepts/README.md`.
- Community health: expanded `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md`,
  `CITATION.cff`, `NOTICE`, and filled the `LICENSE` copyright line
  (`Copyright 2026 Ron Finn`).
- GitHub: `.github/workflows/ci.yml` (uv, matrix 3.11/3.12/3.13, ruff + ruff
  format check + mypy + pytest), `.github/dependabot.yml`,
  `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/` (bug, feature,
  config).
- `.pre-commit-config.yaml` (hygiene hooks + ruff/ruff-format).
- `uv.lock` (committed for reproducible CI).

**Checks run locally (Python 3.12.13 via uv):** `uv sync` (ok),
`uv run ruff check .` (all passed), `uv run ruff format --check .` (clean),
`uv run mypy` (no issues, 7 files), `uv run pytest` (5 passed, 89% coverage),
`uv run openauc version` (prints `0.1.0.dev0`), `uv build` (sdist + wheel built).
The 3.13 leg of the matrix has been exercised only in CI configuration, not
locally (3.13 is not installed on this machine).

**Known limitations recorded below in §7a.**

## 7a. Phase 1 known limitations

- **CODE_OF_CONDUCT enforcement contact is a placeholder** (`[INSERT CONTACT
  METHOD]`). A real contact must be set before public launch.
- **Python 3.13 not verified locally** — only 3.11 and 3.12 are installed here;
  3.13 support rests on the CI matrix.
- **Dependabot `uv` ecosystem** is relatively new; if unsupported on the target
  GitHub instance, switch the Python update entry to `pip`.
- **`ruff`/`pre-commit` hook revisions are pinned to current values** and will
  need routine bumping (Dependabot covers actions, not pre-commit revs).
- **No runtime dependency is exercised yet** beyond `typer`; version-pin
  compatibility for numpy/xarray/pandas/matplotlib is asserted by resolution,
  not by use. First real exercise lands in Phase 2/3.
- Coverage is informational (no minimum gate configured); uncovered lines are
  the CLI `main()` entry point and `__main__` guard.

## 10. Recommended next step

Resolve the Phase 1-adjacent decisions that do not depend on unresolved
scientific questions — specifically confirm the copyright/NOTICE text and the
initial `pyproject.toml` dependency pins — then begin **Phase 1 (packaging
skeleton)** on a new branch off `feat/project-foundation`. Phase 2 should not
begin until Q2 and Q4 are answered.
