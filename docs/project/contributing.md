# Contributing

--8<-- "CONTRIBUTING.md"

## Development logs

Every substantial capability lands with a numbered log in
[`development-log/`](https://github.com/ronfinn/openauc-io/tree/main/development-log)
recording accepted decisions, **rejected alternatives**, limitations and next
steps. If you add a capability, add a log.

## Quality gates

Run before opening a pull request, from the repository root:

```bash
uv sync --all-groups
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
uv run mkdocs build --strict
```

`scripts/release_check.py` (above) runs all five in one command, to completion
rather than stopping at the first failure. It builds, tags, releases and
publishes nothing.

Before a release checkpoint, also build and verify real artifacts:

```bash
rm -rf dist
uv build
uv run python scripts/verify_artifacts.py
uvx twine check --strict dist/*
git diff --check
```

Empty `dist/` first. `verify_artifacts.py` requires **exactly one** wheel and
**exactly one** sdist — that strictness is the point, and a `dist/` still
holding an older build will (correctly) fail it.

Coverage is measured on every `pytest` run and enforced against the
`fail_under` floor in `pyproject.toml`. The floor guards against a collapse in
coverage; it is not a per-module quality guarantee. The full procedure is the
[release checklist](release-checklist.md).

### Unit tests versus real artifacts

Two different things are being tested, and they are kept apart deliberately:

- **Unit tests** for the artifact verifier build a minimal wheel/sdist pair in a
  temporary directory, so they are deterministic and never depend on whatever
  happens to sit in the repository's `dist/`. Running the suite does not require
  a build, and a stale local `dist/` cannot break it.
- **Integration** is the **Release dry run** workflow, which builds real
  artifacts, runs `twine check --strict` and the verifier over them, and installs
  the real wheel *alone* into a clean virtual environment to smoke-test the
  console script. It has no path to PyPI.

Publishing lives in a separate workflow, `.github/workflows/publish.yml`, which
runs *only* when a GitHub Release is published and uploads over PyPI Trusted
Publishing (OIDC) — there is no PyPI token in this repository. Its build job
runs project code but holds no credential; its publish job holds the OIDC
identity but runs no project code. Neither workflow ever creates a tag or a
GitHub Release. See the [release checklist](release-checklist.md).

Typing is `strict`. **Do not weaken typing, validation or tests to make a check
pass** — narrow types with assertions instead.

## Documentation

The site is MkDocs Material. Preview it locally:

```bash
uv run mkdocs serve
```

Then open <http://127.0.0.1:8000/>.

Documentation is part of the deliverable, not an afterthought. A capability
without a how-to page and a docstring is not finished.

### Documentation rules

- Never claim vendor-format compatibility, scientific analysis, physical
  simulation, unit conversion, PyPI availability or scientific validation.
- Keep **representation**, **structural validation**, **analysis readiness** and
  **scientific suitability** distinct, using the vocabulary in the ADRs.
- Give concrete examples, never bare `path/to/file` placeholders.
- State the directory a command runs from.
- Do not document an API or option without testing it.

## Test data

**Synthetic only.** No real or confidential instrument data is ever committed. A
release-readiness test enforces this.

For substantial fixtures use the [synthetic
generator](../tutorials/generate-synthetic-data.md) rather than hand-writing
CSV.

## Extending parsers

The registry is decorator-based; see
[Parser detection](../formats/parser-detection.md) and ADR-0004. A parser must
never guess: ambiguity raises rather than picking.
