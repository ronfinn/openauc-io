# Development Log 0009 — Synthetic data generator

- **Date:** 2026-07-26
- **Branch:** `feat/synthetic-data-generator` (from `main` at `4f14ef9`)
- **Status:** Complete. Deterministic illustrative data generation.
- **Author:** Ron Finn

## 1. Objective

Produce reproducible, repository-safe AUC-*like* datasets for examples,
integration tests, demonstrations and performance work — without ever implying
that the output is a simulation.

## 2. The boundary this phase had to hold

Generating curves that *look* like AUC data is the easiest place in this project
to accidentally make a scientific claim. The rule adopted: **the generator
produces closed-form shapes chosen for being smooth, cheap and reproducible.**
They are not Lamm-equation solutions, not simulations of sedimentation, and no
physical parameter is used to produce them or may be inferred from them.

That statement is carried in `metadata.notes` and in the provenance
`assumptions` of every generated experiment, so a dataset cannot be mistaken for
a real measurement later. It is also in the module docstrings, the concept doc
and the CLI help. Two tests enforce it: one forbids affirmative claims
("is scientifically valid", "accurate simulation", "simulates sedimentation",
"derives the molecular weight", …), the other *requires* the disclaimers to be
present.

## 3. Structure

`src/openauc/synthetic/`:

| Module | Contents |
|--------|----------|
| `config.py` | `Scenario`, `MetadataCompleteness`, `SyntheticExperimentConfig` |
| `generators.py` | curve construction, metadata assembly, `generate_experiment` |
| `writers.py` | `write_generic_long`, `write_generic_wide`, `write_aucx` |

## 4. Determinism

Randomness comes from `np.random.default_rng(config.seed)` — a local generator.
**NumPy's global random state is never read or written**, asserted by a test
that seeds the global stream, generates, and confirms the stream still yields
exactly what it would have.

With `noise_level=0` the seed does not affect the data at all: the curves are
deterministic functions of the configuration. The seed is still recorded in
provenance, so two such experiments have identical observations and *different*
provenance. A test asserts both halves rather than pretending the dicts match.

## 5. Scenario decisions

Two scenarios override the configured axis mode because they cannot be expressed
otherwise: `per-scan-radius` by definition, and `empty-scans` because the model
can only represent an empty scan when each scan owns its axis. This is exposed
as `config.effective_radius_axis_mode` rather than silently ignoring the field.

**`mixed-optics` uses `Unit.UNKNOWN`.** An observation set carries one signal
unit, so any concrete unit would contradict at least one declared optical system
and produce `optical_signal_unit_conflict` — an error, which is not what the
scenario exists to test. With `UNKNOWN` it yields `mixed_optical_systems` and
stays structurally valid.

**`invalid-structure` bypasses nothing.** The second scan metadata record
repeats the first identifier, so metadata no longer matches observations. Every
object is one the model permits; the result is exactly `duplicate_scan_id` and
`scan_id_mismatch`, both archival errors. No impossible object is constructed
and no pydantic invariant is circumvented.

## 6. Writers

Manifests are built from the real `GenericManifest` models and archives from the
real AUCX writer, so the writers cannot drift from what the readers expect. Only
the delimited *table* is written here, because the parsers read tables but never
write them.

**A limitation that was documented rather than worked around:** a generic CSV
has no way to say "explicitly unknown" as distinct from "missing". Rather than
invent a convention, an optional column is emitted only when *every* scan has
that value `PRESENT`; otherwise it is omitted and reloads as absent. AUCX
preserves all four statuses exactly, so exact `to_dict()` round-trip equality is
expected for AUCX only. A test asserts both sides of this.

`write_generic_wide` **refuses** a per-scan-axis experiment rather than
resampling onto a common grid, which openauc never does.

## 7. CLI

`openauc generate OUTPUT` with `--scenario`, `--scans`, `--points`, `--seed`,
`--noise`, `--format`, `--overwrite`, `--json`. It reuses the existing exit-code
scheme (2 for unknown scenario/format or invalid config, 3 for existing output)
and the existing single-line error reporting, so it added no new CLI concepts.
The help text leads with the synthetic disclaimer.

## 8. Tests

65 new tests. Determinism (same seed, different seeds, no-noise, global state);
all eight scenarios; both axis modes; all four value statuses; long/wide/AUCX
export and reload; exact dict equality for AUCX; overwrite refusal on all three
writers; twelve invalid configurations; wide refusal; plotting, summary and
readiness compatibility; ten CLI tests; and the claim-honesty checks above.

One moderate performance test (60 scans × 3000 points) is marked `slow`; the
marker is registered in `pyproject.toml` because `--strict-markers` is enabled.
It costs under a second and `-m "not slow"` deselects it.

Three of my own test bugs surfaced and were fixed rather than accommodated: the
global-state test advanced the state itself before comparing, and two
claim-checkers flagged the *denials* of a claim as if they were the claim.

## 9. Known limitations

- Curves are one-dimensional in radius with no diffusive broadening: the
  boundary shifts, nothing spreads.
- Noise is independent Gaussian per point, not an instrument noise model.
- One sample and one cell/channel per generated experiment.
- `invalid-structure` produces one specific finding pair, not a sweep of every
  possible inconsistency.
- Delimited output cannot carry the unknown/missing distinction (see §6).

## 10. Rejected alternatives

- **Solving the Lamm equation.** Rejected outright: it would make the output a
  simulation, which this project does not do and must not appear to do.
- **Inventing a CSV convention for "unknown"** (e.g. a sentinel string).
  Rejected: it would be a private convention the format does not define, and
  readers would have to guess. Omitting the column is honest.
- **Letting `mixed-optics` keep a concrete signal unit.** Rejected: it would
  produce a structural error unrelated to what the scenario tests.
- **Silently ignoring `radius_axis_mode` for scenarios that need per-scan
  axes.** Rejected in favour of an explicit `effective_radius_axis_mode`.

## 11. Next steps

Q6 (documentation tooling: MkDocs-Material vs Sphinx) remains the last
unresolved question from the original seven, and this generator now supplies the
runnable examples such a site would render.
