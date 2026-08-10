# Development Log 0010 — Release mechanics (Phase 9)

- **Date:** 2026-08-10
- **Branch:** `chore/phase-9-alpha-release` (from `main` at `b75a7ce`)
- **Status:** Phase 9 complete. **Nothing published, tagged or released.**
- **Author:** Ron Finn

## 1. Objective

Make releasing `0.1.0a1` a repeatable procedure rather than a remembered one —
without releasing it. Everything here is machinery and documentation; the act of
publishing remains deliberate, manual and untaken.

## 2. Baseline

Verified on a clean worktree before any change, on Python 3.13.14: ruff check,
ruff format, strict mypy, MkDocs strict build and `uv build` all pass; 449 tests
pass; coverage is 95.9% over 2668 statements (77 missed) and 684 branches
(58 partial). Re-verified after the change: 466 tests pass, coverage unchanged
at 95.9% — the new tests exercise configuration and workflow files, not package
code, so they add no covered statements.

## 3. The coverage gate

`fail_under = 93` under `[tool.coverage.report]`, with `precision = 1` and
`show_missing`. Because `--cov=openauc` is already in `addopts`, every `pytest`
run enforces it; no CI change was needed.

**Why 93 and not 96.** A gate set at the measured figure converts every ordinary
change into a coverage negotiation, and the usual response is to write a test
that touches a line rather than one that tests behaviour. Set at 93 it catches a
collapse — a module landing untested, coverage silently disabled — which is what
it is for. Raising it is a deliberate act with its own commit, not a side effect.

The deferral recorded in log 0008 §8 is now closed.

## 4. `scripts/release_check.py`

One command running lint, format, types, tests and the strict docs build. It
runs every step to completion rather than stopping at the first failure, prints
a PASS/FAIL summary, and exits non-zero if any failed — a maintainer running it
before a release wants the whole list, not the first item on it.

It builds nothing and publishes nothing.

## 5. `scripts/verify_artifacts.py`

Run after `uv build`. Checks that `dist/` holds exactly one wheel and one sdist;
that both filenames carry the version parsed from `src/openauc/__init__.py`;
that `CITATION.cff` agrees; that the wheel contains every subpackage and the
`py.typed` marker; and — when `GITHUB_REF` names a tag — that the tag is
`v<version>`.

The tag check is the reason this exists as a script rather than a workflow step:
it is the one release check that cannot be run meaningfully before a tag exists,
so it had to be written now and left dormant.

It accumulates failures and reports all of them, for the same reason as §4.

## 6. The dry-run workflow

`.github/workflows/release.yml`, named **Release dry run**. It syncs, runs the
release check suite, builds, runs `twine check --strict`, verifies the artifacts,
installs the wheel *alone* into a fresh virtual environment, runs `openauc
version` and `openauc formats` against it, and uploads the distributions as a
build artifact.

**It cannot publish.** There is no upload step, no release step and no tagging
step; it declares `permissions: contents: read` and requests no `id-token`. A
test asserts each of those absences by name, and a second test asserts that *no*
workflow in the repository publishes anywhere.

It triggers on `workflow_dispatch` and on pull requests that touch the version,
the packaging metadata or the workflow itself — the changes that can break a
build — rather than on every push, which would duplicate CI.

## 7. Documentation

`docs/project/release-checklist.md`: what is automated and what is deliberately
not, the pre-release gates, the release itself, and the post-release steps. It
opens with an admonition that `0.1.0a1` is prepared but unpublished, so the page
cannot be read as a record of a release that happened. Linked from the project
index, the roadmap, both contributing pages and the site navigation.

## 8. Tests

17 new tests in `tests/unit/test_release_mechanics.py`: the coverage gate is
configured and meaningful; coverage is measured on every run; both scripts exist
and compile; the check script names every gate; no script contains an upload or
release command; `verify_artifacts.py` *fails* on a mismatched dist and passes on
a real one; the workflow exists, is read-only, contains none of seven named
publishing mechanisms, and does build, check, verify and smoke-test; no workflow
anywhere publishes; the checklist exists, is navigable and claims no release; the
changelog still marks the alpha unreleased; and **no `v*` tag exists**.

Four existing paths were added to `test_documented_files_exist`.

Two of my own test bugs surfaced and were fixed rather than accommodated:

- `verify_artifacts.py` raised `BadZipFile` on a malformed wheel instead of
  reporting it, so the negative test failed for the wrong reason. The script now
  reports it as a failure. This is a real defect the test caught.
- The claim-checker flagged the checklist's own *denial* ("Nothing has been
  released yet") as if it were a claim — the same trap recorded in log 0009 §8.
  The forbidden phrases are now affirmative forms only.

## 9. Known limitations

- The dry run builds on Linux and Python 3.12 only. The wheel is
  `py3-none-any`, so this is a check of packaging, not of platform support; CI
  still covers 3.11–3.13.
- `verify_artifacts.py` checks wheel *contents* by name, not that each module
  imports from the installed wheel; the smoke-test step covers the import path
  shallowly.
- The coverage floor is global. There is no per-file floor, so a new untested
  module can land while the total stays above 93%.
- Nothing verifies the sdist's contents beyond its name and `twine check`.

## 10. Rejected alternatives

- **A publish workflow with credentials, disabled by a flag.** Rejected: a
  disabled publisher is one edited line away from publishing, and the point of
  this phase was machinery that *cannot* release by accident. The workflow has
  no path to PyPI at all.
- **Trusted publishing configured but unused.** Rejected for now on the same
  grounds — it requires `id-token: write`, which a test currently forbids.
  Adding it belongs to the phase that actually publishes.
- **`fail_under = 96`, the measured figure.** Rejected: see §3.
- **Tagging `v0.1.0a1` locally "to test the tag check".** Rejected: the tag is
  an explicit boundary of this phase. The check reads `GITHUB_REF`, so it can be
  exercised without one.
- **A `release` job inside `ci.yml`.** Rejected: CI runs on every pull request,
  and a build-and-verify pass on every commit is noise. It is its own workflow
  with its own triggers.

## 11. Next steps

- Publishing `0.1.0a1` — tag, GitHub release, PyPI — remains a separate,
  deliberate decision. The checklist is the procedure for it.
- If publishing is adopted, revisit trusted publishing (§10) and the test that
  currently forbids `id-token: write`.
- Deferred capabilities are unchanged: sample-to-scan linkage, heterogeneous
  per-scan signal units, an `acquired_at` manifest field, and entry-point parser
  discovery.
