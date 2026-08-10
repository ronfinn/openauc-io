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

Before a release checkpoint, also:

```bash
uv build
uv run python scripts/verify_artifacts.py
git diff --check
```

Coverage is measured on every `pytest` run and enforced against the
`fail_under` floor in `pyproject.toml`. The full procedure is the
[release checklist](release-checklist.md).

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
