# openauc-io development rules

## Project purpose

`openauc-io` is an open-source Python toolkit for ingesting, representing,
structurally validating, plotting, generating, converting, and archiving
analytical ultracentrifugation (AUC) data.

`openauc` is **AUC data infrastructure, not scientific-analysis software**.

Naming: the project/package is `openauc-io` / `openauc`. "OpenAUC" in the
existing documentation refers to an external AUC data format that this project
does not read; do not conflate the two.

Scientific correctness, preservation of experimental meaning, provenance,
determinism, and archival compatibility take priority over feature count.

## Repository layout

- `src/openauc/` — Python package.
- `tests/` — pytest suite.
- `docs/` — MkDocs documentation.
- `docs/decisions/` — architectural decision records (ADRs).
- `development-log/` — historical milestone records.
- `schemas/` — versioned schemas.
- `examples/` — example data and usage.
- `scripts/` — repository tooling, including `release_check.py` and
  `verify_artifacts.py`.
- `pyproject.toml` — package, dependency, lint, type-checking, test, and
  coverage configuration.
- `uv.lock` — locked development environment.

Use `uv` for environment and command execution unless a task specifically
requires otherwise.

## Scientific boundaries

These are permanent non-goals (see `docs/concepts/scientific-boundaries.md`
and the "Never" section of `docs/project/roadmap.md`), not deferred work.
Only an explicit human-authorized architectural decision could change them.

`openauc` does not perform:

- sedimentation fitting;
- molecular-weight estimation;
- meniscus detection;
- convection assessment;
- scientific quality control;
- automatic unit conversion;
- physically validated sedimentation simulation;
- Lamm-equation simulation or fitting.

Additional rules:

- Scientific suitability is permanently `NOT_ASSESSED`.
- Structural validity must never be presented as scientific validity.
- Analysis readiness means required information is present; it does not mean
  an experiment is scientifically suitable.
- Synthetic data must remain explicitly illustrative unless a future,
  explicitly authorized project changes that scope.
- Vendor/instrument readers may only be implemented from documented,
  non-reverse-engineered specifications.
- Do not infer scientific conclusions from metadata, validation results, or
  plotting output.
- Do not silently interpolate, regrid, smooth, normalize, baseline-correct,
  sort, resample, convert units, or otherwise transform stored experimental
  observations.
- If a future task introduces a data transformation, it must be explicit,
  opt-in, documented, and provenance-carrying.

Before changing a scientific claim or boundary, read:

- `docs/concepts/scientific-boundaries.md`
- `docs/project/limitations.md`
- relevant ADRs under `docs/decisions/`

## Data and archival guarantees

Preserve the guarantees already made by the repository.

In particular:

- preserve source provenance;
- preserve checksum and integrity verification;
- preserve deterministic behavior where promised;
- preserve missing/unknown/not-applicable value semantics;
- preserve shared and per-scan radial-axis meaning;
- never introduce silent interpolation to reconcile radius grids;
- preserve backwards compatibility with published AUCX versions unless a task
  explicitly authorizes and documents a breaking change;
- reject unsupported or corrupt archive states clearly rather than guessing.

Changes to AUCX versioning, canonical model semantics, integrity guarantees, or
public serialization formats are high-consequence changes. Inspect the relevant
ADR and compatibility tests before modifying them.

## Engineering requirements

The authoritative configuration lives in `pyproject.toml`.

Current expectations include:

- supported Python versions: 3.11, 3.12, and 3.13;
- Ruff linting;
- Ruff formatting;
- strict mypy;
- pytest;
- the configured coverage floor;
- strict MkDocs builds.

Do not:

- reduce or bypass the coverage floor simply to make a change pass;
- weaken, delete, skip, or rewrite tests merely to accommodate an
  implementation;
- add `# noqa`, `type: ignore`, broad exclusions, or disabled rules merely to
  silence legitimate new findings;
- change dependencies unless the task requires it;
- refactor unrelated code as part of a focused feature or fix.

Add or update tests for new behavior and bug fixes.

Prefer the simplest implementation that meets the current requirement. Do not
introduce speculative abstractions, generic frameworks, configuration layers,
or extensibility points without a demonstrated need.

## Efficient verification

During implementation, run the smallest relevant checks first.

Examples:

    uv run pytest tests/path/to/relevant_tests.py
    uv run ruff check path/to/changed_code.py
    uv run mypy

Before declaring substantial implementation work complete, run:

    uv run python scripts/release_check.py

Before committing, also run:

    git diff --check

For documentation-only work, targeted documentation tests and:

    uv run mkdocs build --strict

may be used during iteration. The full release check is still appropriate
before a consequential documentation/release change is considered complete.

If a gate fails, investigate the failure rather than weakening the gate.

## Development style

This is currently a **single-developer scientific Python project**. Keep the
workflow proportionate to that reality.

- Inspect existing code, tests, documentation, and relevant ADRs before
  changing public APIs or persisted formats.
- Make focused changes.
- Keep unrelated refactoring out of feature work.
- Update tests and documentation when behavior changes.
- Use commits as useful checkpoints, not as ceremony.
- A coherent feature normally needs one feature branch, not a hierarchy of
  process branches.
- Do not create issues, branches, pull requests, ADRs, hooks, agents, skills,
  workflows, or documentation merely because the mechanism exists.
- Add process only when it addresses a concrete technical, scientific,
  archival, release, or maintenance risk.

Pull requests are useful for CI validation and preserving a reviewable history,
but this repository does not require enterprise-style approval ceremony for
routine solo development.

## Developer preferences

- Solo developer; prioritise building the MVP. Prefer simple solutions over
  speculative architecture.
- Avoid unnecessary Git and CI ceremony.
- Use the most economical suitable model and effort.
- Keep documentation scientifically and technically useful.
- Do not add coding-agent attribution (trailers, "generated by" footers,
  session URLs) to commits, PR descriptions, or project documentation.
- Use the maintainer's public name and GitHub noreply email for authored
  metadata; do not expose private personal information.
- Say when `/clear` or `/compact` would help (see "Context management").

## Git and release safety

Routine local Git operations and feature branches are allowed when useful.

Do not, unless the current task explicitly authorizes it:

- rewrite published Git history;
- force-push shared branches;
- create, move, or delete release tags;
- create or publish GitHub Releases;
- publish to PyPI or TestPyPI;
- create PyPI credentials or API tokens;
- modify release/publishing workflows;
- make an unplanned breaking change to a published format or public API.

When a task explicitly includes opening or merging a pull request, perform that
task without inventing additional approval steps.

Release publication remains a deliberate human-authorized action.

## Architecture decisions

Do not create an ADR for ordinary implementation details.

Use or amend an ADR when a decision is durable and consequential, such as:

- canonical data-model semantics;
- public serialization or archive compatibility;
- persisted format versioning;
- parser/plugin contracts exposed to third parties;
- irreversible public API decisions;
- changes to scientific boundaries or transformation policy.

Existing ADRs live in `docs/decisions/`.

## Claude Code usage

Use Claude Code features selectively rather than automatically.

### Planning

Use Plan Mode for changes with meaningful design risk, especially:

- canonical model changes;
- AUCX format/version changes;
- public API changes;
- parser architecture;
- provenance or integrity behavior;
- scientific-boundary changes.

For small, well-scoped fixes, proceed directly after inspecting the relevant
code and tests.

### Subagents

Use subagents only when work is genuinely parallel, benefits from isolated
context, or requires independent investigation.

Do not spawn agents for simple repository inspection, single-file edits,
routine test runs, or tasks that can be completed directly.

### Skills, hooks, and MCP

Only introduce a project Skill, hook, or MCP integration after a repeated
workflow or external-system need has been demonstrated.

Do not add automation simply because Claude Code supports it.

### Context management

Proactively tell the user when context management would help.

Recommend:

- `/clear` after a completed milestone, merged feature, or other clean task
  boundary before starting materially different work;
- `/compact` when continuing the same substantial task and accumulated context
  remains useful but the conversation is becoming large;
- neither command for short or coherent work that is progressing normally.

Do not recommend `/compact` merely because time has passed. Do not recommend
`/clear` while important unresolved reasoning from the current task is still
needed.

## Autonomous-task safety

When executing an autonomous or backlog task:

- work only on the named task and its acceptance criteria;
- do not begin the next backlog item automatically;
- if implementation requires a consequential architectural decision not
  covered by the task, surface the decision before committing to it;
- if a documented scientific boundary would be crossed, stop that part of the
  implementation and report it;
- if repeated focused repair attempts are not resolving the same failure,
  stop thrashing, summarize what has been learned, and propose the next
  diagnostic step;
- never publish a release as an incidental side effect of another task.

## Review before completion

Before declaring consequential work complete:

- review the complete diff;
- check for scope creep;
- check backwards compatibility where relevant;
- look for weakened tests or quality gates;
- look for altered scientific claims or boundaries;
- confirm acceptance criteria are demonstrated by tests or other evidence;
- check that documentation matches implementation;
- report meaningful residual risks and uncertainties.

Keep completion reports concise:

1. what changed;
2. verification performed and results;
3. important decisions;
4. residual risks or uncertainties;
5. current Git state.

## Source of truth

Do not duplicate large sections of project documentation in this file.

Consult these documents when relevant:

- `README.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `docs/concepts/scientific-boundaries.md`
- `docs/project/limitations.md`
- `docs/project/roadmap.md`
- `docs/project/release-checklist.md`
- relevant ADRs in `docs/decisions/`
- relevant historical entries in `development-log/`

When this file conflicts with an authoritative project specification or
published format contract, surface the conflict rather than silently choosing
one.
