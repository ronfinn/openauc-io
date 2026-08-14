# Known limitations

Honest, current, and distinct from the [permanent
non-goals](../concepts/scientific-boundaries.md).

## Status

- **First public alpha (`0.1.0a1`), published on PyPI as a pre-release.** APIs
  may change without notice; availability is a packaging fact, not a stability
  guarantee.

## Formats

- **Generic CSV/TSV and AUCX only.** No vendor or instrument formats — Beckman
  XL-A/XL-I, Optima, OpenAUC and SEDFIT/SEDPHAT files are not read.
- Generic delimited output **cannot express `UNKNOWN` as distinct from
  `MISSING`**. AUCX preserves all four statuses exactly.
- No AUCX → CSV direction; it would need a documented lossiness policy.
- Generic-wide requires one shared radius axis, by construction.

## Model

- **One signal unit per observation set.** Heterogeneous per-scan signal units
  are not modelled, which is why more than one declared optical system is
  reported as an anomaly.
- **No sample-to-scan linkage.** `ScanMetadata` carries no `sample_id`, so
  sample metadata is assessed experiment-wide only.
- `ExperimentMetadata.acquired_at` is always `None` on import — the manifest
  schema has no such field.
- No unit conversion anywhere.
- `optical_systems()` includes the instrument's declared system, so a set with
  a declared scan system and an undeclared instrument renders as
  `absorbance, unknown`.

## AUCX

- One experiment per archive.
- Read whole into memory, bounded by 512 MiB per member and 2 GiB total.
- No encryption and **no signatures** — integrity only, never authenticity.
- The size limits are constants, not configurable.

## Plotting

- Single-panel overlay only: no subplot grids, faceting, residual panels or
  time-series projections.
- No downsampling for very large scan sets.
- Styling beyond the exposed options is the caller's job.

## CLI

- No plotting subcommand; plotting stays a Python API.
- One experiment per invocation — no batch or glob input.
- `--json` output is stable per command but not schema-versioned.

## Synthetic data

- Curves are one-dimensional in radius with no diffusive broadening: the
  boundary shifts, nothing spreads.
- Noise is independent Gaussian per point, not an instrument noise model.
- One sample and one cell/channel per generated experiment.
- `invalid-structure` produces one specific finding pair, not a sweep.

## Tooling

- The coverage floor is **global and deliberately below the measured figure**.
  `fail_under` in `pyproject.toml` is enforced by every `pytest` run, including
  CI, but it exists to catch a collapse in coverage — a module landing untested,
  coverage silently switched off — not to certify quality. There is no per-file
  floor, so a new untested module can land while the total stays above the
  floor, and the floor says nothing about whether the covered behaviour is
  scientifically correct.
- Artifact verification is strict by design: `scripts/verify_artifacts.py`
  requires **exactly one** wheel and **exactly one** sdist, so it must be run
  against a freshly emptied `dist/`. Its unit tests use isolated temporary
  fixtures; the real artifacts are exercised by the Release dry-run workflow.
- `scripts/release_check.py` covers the source-tree gates only. It does not
  build, verify artifacts, tag, release or publish.
- The release dry run builds on Linux and one Python version; the wheel is
  `py3-none-any`, so this checks packaging, not platform support.
- Python 3.13 support rests on CI; local development here uses 3.12.

## Next step

- [Roadmap](roadmap.md)
- [Scientific boundaries](../concepts/scientific-boundaries.md)
