# Development Log 0011 — Post-Phase-9 release hardening and documentation audit

- **Date:** 2026-08-10
- **Branch:** `docs/post-phase9-refresh` (from `main` after PR #22 and PR #23)
- **Status:** Documentation consistency work. **Nothing published, tagged or
  released.** `0.1.0a1` remains prepared and unpublished.
- **Author:** Ron Finn

## 1. Objective

Two things after Phase 9: record why the artifact verifier's unit tests no
longer read the repository's `dist/`, and bring the documentation back into
agreement with what the repository actually does now.

No package code changes here.

## 2. The artifact-test isolation correction (PR #23)

The verifier's positive-path test ran `scripts/verify_artifacts.py` against the
repository-level `dist/`. That made a unit test depend on mutable developer
state: a `dist/` holding a stale build alongside the current one contains two
wheels and two sdists, the verifier correctly reported that, and the pytest
suite failed even though both the source tree and the current release build were
fine.

The fix builds a minimal wheel/sdist pair under `tmp_path` instead. The version
and the required wheel entries are read from the same sources the verifier
itself reads, so the fixture cannot drift from what it verifies, and the
positive path now genuinely executes on every run rather than skipping when
`dist/` is absent. Negative cases were added for a missing `py.typed`, a corrupt
wheel, and the two-versions-in-one-`dist` state that caused the original
failure. `GITHUB_REF` is stripped from the verifier's environment so the tag
check cannot make the tests environment-dependent.

**Artifact verification itself is unchanged and remains strict.** Exactly one
wheel and exactly one sdist is the intended contract for a release build, not a
rough heuristic to be relaxed because a developer's `dist/` is untidy. The
correct response to a stale `dist/` is `rm -rf dist` before `uv build`, which
the release checklist and the contributing page both now state explicitly.

The two layers are distinct, and the distinction is the point:

| Layer | What it exercises | Where |
|-------|-------------------|-------|
| Unit | Verifier *behaviour*, deterministically | temporary fixtures under `tmp_path` |
| Integration | Real built artifacts | **Release dry run** workflow: `uv build` → `twine check --strict` → verifier → clean-venv wheel smoke test |

This is release hardening, a follow-up to Phase 9. It is not a new phase and
introduces no capability.

## 3. The documentation audit

Corrected:

- **`docs/project/limitations.md` — the coverage claim.** It still said coverage
  was informational with no `fail_under` gate in CI. Phase 9 set
  `fail_under = 93` under `[tool.coverage.report]`, and `--cov=openauc` is
  already in `addopts`, so every `pytest` run — CI included — enforces it. The
  rewritten entry states the floor accurately *and* what it does not mean: it is
  global, deliberately below the measured figure, has no per-file component, and
  certifies nothing about scientific correctness. The measured percentage is
  recorded in logs and pull requests, not pinned in long-lived documentation
  where it becomes false on the next commit.
- The same section gained the verifier's exact-one-wheel/exact-one-sdist
  requirement, the `release_check.py` boundary (source gates only), and the
  dry run's single-platform scope.
- **`docs/project/roadmap.md` — "Six are resolved"** while Q1–Q7 were all marked
  resolved. Now "All seven are resolved". Added a next-milestone section naming
  the first public alpha release as what comes before larger model or
  vendor-format work, and a sentence classifying post-Phase-9 release hardening
  as follow-up rather than a phase.
- **`README.md` — Development.** The individual commands are kept; the
  consolidated `uv run python scripts/release_check.py` is now discoverable
  alongside them, with an explicit statement that it builds, tags, releases and
  publishes nothing, and a link to the release checklist. No release section was
  added — the README stays user-oriented.
- **`docs/project/contributing.md`.** The release-checkpoint block now begins
  with `rm -rf dist` and ends with `twine check --strict`, explains why the
  verifier's strictness is intentional, and separates deterministic unit testing
  from real-artifact integration testing.

Audited and left alone because they were already correct: the release checklist,
the project index, `CHANGELOG.md`, `CITATION.cff`, the installation page's
"not published to PyPI" warning, and `docs/concepts/scientific-boundaries.md`.

## 4. What was deliberately not changed

- **The release boundary.** No version bump, no changelog date, no CITATION
  change, no tag, no release, no PyPI claim anywhere. `0.1.0a1` is prepared and
  unpublished, and the documentation continues to say so as a point in time
  rather than a permanent property.
- **Scientific boundaries.** No sedimentation fitting, molecular-weight
  estimation, meniscus detection, convection assessment, scientific quality
  control, unit conversion or physically validated Lamm-equation simulation.
  Scientific suitability remains `NOT_ASSESSED`. Synthetic data remains
  illustrative, not simulation. Vendor readers remain deferred pending
  documented, non-reverse-engineered specifications.
- **Genuine limitations.** Model, format, plotting, AUCX, CLI and synthetic-data
  limitations were left intact; only the stale tooling claims moved.
- **Historical logs.** Logs 0001–0010 record what was true when they were
  written, including their test counts and coverage figures. They are history,
  not a dashboard, and were not retrofitted.

## 5. Known limitations

- The audit is a point-in-time sweep. Nothing tests that documentation prose
  keeps agreeing with `pyproject.toml`; the coverage floor could be changed
  without the limitations page following it.
- The distinction in §2 is documented in the contributing page and here, not
  enforced: a future test could again reach for the repository's `dist/`.

## 6. Rejected alternatives

- **Relaxing the verifier to tolerate several versions in `dist/`.** Rejected:
  ambiguity about which artifact is being released is exactly what the check
  exists to prevent. The developer workflow bends, not the release contract.
- **Quoting the measured coverage percentage in the limitations page.**
  Rejected: it is volatile, and a figure that drifts silently is worse than no
  figure. The floor is durable; the measurement belongs in logs.
- **A README release section.** Rejected: the README is for users. Maintainers
  get one command and one link.
- **A "Phase 10" heading for this work.** Rejected: it delivers no capability.

## 7. Next steps

- Publishing `0.1.0a1` — tag, GitHub release, PyPI — remains the immediate
  milestone and a deliberate manual decision. The
  [release checklist](../docs/project/release-checklist.md) is the procedure.
- Deferred capabilities are unchanged: sample-to-scan linkage, heterogeneous
  per-scan signal units, an `acquired_at` manifest field, entry-point parser
  discovery, and vendor-format readers behind documented specifications.
