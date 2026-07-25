# Development Log 0008 — Alpha-release readiness (Phase 8)

- **Date:** 2026-07-25
- **Branch:** `feat/validation-and-summaries` (continuous alpha build)
- **Status:** Phase 8 complete. Version `0.1.0a1` prepared. **Nothing published,
  tagged or released.**
- **Author:** Ron Finn

## 1. Objective

Make the package internally coherent at `0.1.0a1`: a truthful README, runnable
examples, documentation that matches the implementation, and tests that catch
the kinds of drift a release exposes.

## 2. Version

`0.1.0a1` in `src/openauc/__init__.py` (hatch reads it from there) and
`CITATION.cff`. A test asserts the two agree, so they cannot drift apart
silently. Nothing was published to PyPI, no GitHub release was made, and the
repository was not tagged.

## 3. Examples

Six scripts under `examples/`, each standalone and each executed by the test
suite, over a new synthetic fixture `examples/data/demo_experiment` (a four-scan
long-format CSV with a full manifest — instrument, sample and defaults — so the
readiness path reaches `POTENTIALLY_READY`).

The data is generated from an invented sigmoid and is labelled in the manifest
as synthetic and "Not a real experiment", which a test asserts. A second test
scans the example sources for phrases that would imply a scientific conclusion.

## 4. Documentation

README restructured around an end-to-end example — load, summarise, validate,
plot, export, reload — mirrored by the equivalent shell commands. Added install
instructions for both `uv sync` and `pip install` from a built wheel, an AUCX
section, and two new sections:

- **Known limitations** — what is genuinely missing or bounded today.
- **Scientific non-goals** — stated as *permanent*, not "not yet", so no reader
  mistakes them for a roadmap.

New `docs/cli.md`. Indexes updated for `aucx.md`, `plotting.md` and `cli.md`.
The README status banner had drifted twice during the build (it still claimed
plotting, AUCX and the CLI were unimplemented); it is now accurate, and a test
pins the non-claim wording.

## 5. Release-readiness tests

21 tests in `tests/unit/test_release_readiness.py`:

version coherence across package and citation; `pyproject` metadata (name,
licence, `license-files`, `requires-python`, console script, dynamic version);
every documented top-level and `openauc.api` export resolving; every subpackage
facade resolving with no duplicate or dangling names; the exact README
end-to-end sequence executing; all six examples executing with output; example
data declared synthetic; no scientific-claim phrasing in examples; all
documented files existing; **every ADR now Accepted**; README carrying its
non-claim wording and no vendor-support claims; no build products, caches,
`.pyc`, wheels, sdists or egg-info tracked; no credential-like files tracked;
and all committed data files small.

One assertion had to be relaxed honestly: `__all__` ordering is enforced by
ruff's `RUF022`, whose natural sort differs from `str.sort` (it places
`AUCXExport` before `AUCX_FORMAT_ID`). Asserting plain `sorted()` would have
meant fighting the linter, so the tests assert no duplicates and no dangling
names and leave ordering to ruff.

## 6. Wheel verification

`uv build` produces `openauc-0.1.0a1-py3-none-any.whl`. Contents verified to
include every module (`models`, `formats` including `aucx`, `plotting`, `cli`)
and the `py.typed` marker. Installed into an isolated throwaway environment
from the wheel alone, then `openauc version`, `openauc formats` and a full
load → validate → export → reload cycle were run against it.

## 7. Known limitations at `0.1.0a1`

Recorded in the README rather than only here: pre-alpha API stability; generic
CSV/TSV and AUCX only, no vendor formats; one signal unit per observation set;
no sample-to-scan linkage; no unit conversion; one experiment per archive, read
whole into memory, no encryption or signatures; single-panel plotting; no CLI
plotting or batch input.

## 8. Deferred

- Publishing (PyPI, GitHub release, tagging) — deliberately out of scope.
- Documentation tooling (Q6, MkDocs vs Sphinx) — the docs remain plain Markdown;
  no site generator was adopted, so Q6 stays open.
- A coverage gate (`fail_under`) — still not added; CI failure behaviour is
  unchanged.
- Sample-to-scan linkage and heterogeneous per-scan signal units.
- An `acquired_at` field in the manifest schema.

## 9. Next steps

Q6 (documentation tooling) is the remaining open question from the original
seven. After that, the natural next capabilities are vendor-format readers —
each of which needs a documented, non-reverse-engineered specification before
any parsing code is written.
