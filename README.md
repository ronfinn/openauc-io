# openauc-io

Open-source Python library for importing, validating, standardising, visualising
and archiving analytical ultracentrifugation (AUC) data.

> **Status: pre-alpha (`0.1.0a1`), not published.** APIs may change without
> notice. Implemented: the canonical in-memory data model, generic CSV/TSV
> ingestion, tiered structural validation, analysis-readiness reporting,
> structured summaries, basic scan plotting, the AUCX archival container, and a
> command-line interface. **No scientific AUC analysis is implemented** — no
> sedimentation-velocity or equilibrium analysis, no quality control, no unit
> conversion — and none is planned. Vendor and instrument formats are not
> supported.

## Scope

`openauc` aims to support historical and modern AUC formats over time. The
**first alpha release** is intentionally narrow and provides:

1. Generic long-format CSV/TSV import.
2. Generic wide-format CSV/TSV import.
3. JSON/YAML experiment manifests (JSON canonical; YAML for authoring).
4. A canonical in-memory AUC experiment model.
5. Structural validation.
6. Scan summaries.
7. Basic scan plotting.
8. Export to a versioned `.aucx` archive.
9. Reloading `.aucx` archives.
10. Checksums and provenance.
11. A command-line interface.
12. User and developer documentation.

**This project is not a replacement for SEDFIT, SEDPHAT, UltraScan, GUSSI or
other established AUC analysis software.** It performs no sedimentation
modelling or fitting. It is an independent, clean-room implementation and does
not copy code or interfaces from those tools.

## Requirements

- Python 3.11, 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/) for development

## Install (from source)

Not yet published to PyPI. From a clone:

```bash
git clone https://github.com/ronfinn/openauc-io
cd openauc-io
uv sync                       # development environment
```

Or build and install the wheel into any environment:

```bash
uv build
pip install dist/openauc-0.1.0a1-py3-none-any.whl
```

## Quickstart

End to end — load, describe, validate, plot, archive, reload:

```python
import openauc
from openauc.plotting import plot_scans

experiment = openauc.load("examples/data/demo_experiment")
print(experiment.summary())

report = experiment.validate()
ax = plot_scans(experiment)

experiment.export("experiment.aucx")
restored = openauc.load("experiment.aucx")
assert restored.to_dict() == experiment.to_dict()
```

The same workflow from the shell:

```bash
uv run openauc inspect  examples/data/demo_experiment
uv run openauc validate examples/data/demo_experiment --readiness
uv run openauc convert  examples/data/demo_experiment experiment.aucx
uv run openauc validate experiment.aucx
```

Runnable versions of each step live in [`examples/`](examples/). See
[docs/cli.md](docs/cli.md) for the command reference and exit codes.

Generic delimited (CSV/TSV) experiments are loaded via a manifest:

```python
import openauc

experiment = openauc.load("path/to/experiment")   # a directory with a manifest
print(experiment.summary())
print(experiment.validate_structure())

# Discover the registered parsers:
for info in openauc.available_formats():
    print(info.format_id, "-", info.name)
```

`load` reads generic long- and wide-format CSV/TSV described by a JSON (or YAML)
manifest. It preserves raw values and order, never interpolates or converts
units, represents missing/unknown metadata explicitly, and reports ambiguous or
malformed input with clear errors. See the
[format docs](docs/formats/generic-delimited.md). Vendor formats (Beckman,
Optima, OpenAUC, SEDFIT/SEDPHAT) are **not** supported.

The canonical data model can also be constructed in memory. It preserves raw
observations, retains declared units, represents missing/unknown values
explicitly, and supports both shared and per-scan radius axes — with no silent
interpolation or unit conversion:

```python
from openauc.models import (
    AUCExperiment, ExperimentMetadata, ScanMetadata, Observations,
    Quantity, Unit, OpticalSystem,
)

experiment = AUCExperiment(
    metadata=ExperimentMetadata(experiment_id="exp-1"),
    scans=(
        ScanMetadata(
            scan_id="scan-1", index=0,
            elapsed_time=Quantity.of(0.0, Unit.SECOND),
            optical_system=OpticalSystem.ABSORBANCE,
        ),
    ),
    observations=Observations.from_shared_axis(
        radius=[6.0, 6.1, 6.2],
        signal=[[0.10, 0.20, 0.30]],
        scan_ids=["scan-1"],
        signal_unit=Unit.ABSORBANCE_UNIT,
    ),
)

print(experiment.summary())
report = experiment.validate_structure()   # structural checks only
assert report.is_valid
```

## Validation, readiness and summaries

Validation is **tiered**, and the tiers are answered independently:

```python
report = experiment.validate()              # archival, structural + readiness
summary = experiment.summary_data()         # structured facts, JSON-friendly
assessment = experiment.assess_readiness()  # metadata presence per workflow

assert report.is_valid                      # no ERROR-severity findings
summary.to_dict()["total_valid_observations"]
assessment.sedimentation_velocity.status    # POTENTIALLY_READY | BLOCKED | ...
assessment.scientific_suitability.status    # always NOT_ASSESSED
```

An experiment is **archivally and structurally valid** as long as its scans and
observations correspond unambiguously and are internally consistent. Absent
metadata is *reported*, never required — so a historical dataset with sparse
metadata stays representable — while readiness reports separately whether the
metadata a future workflow would need is present.

`openauc` never describes data as *ready*, *scientifically valid* or *suitable
for analysis*. Scientific suitability is permanently reported as
`NOT_ASSESSED`, and scientific quality control (convection, aggregation,
meniscus, equilibrium) is out of scope by design. See
[validation tiers](docs/concepts/validation-tiers.md) and
[analysis readiness](docs/concepts/analysis-readiness.md).

## Plotting

```python
from openauc.plotting import plot_scans

axes = plot_scans(experiment)          # one line per scan, overlaid
axes.figure.savefig("scans.png")       # works headless; pyplot is not used
```

Each scan is drawn from its own stored vectors, in stored order — nothing is
interpolated, resampled, sorted or smoothed, and per-scan radius axes are never
placed on a common grid. Only the measured series are drawn: no fitting,
baseline correction or derived overlay. matplotlib loads on the first draw, so
`import openauc` stays light. See [plotting](docs/concepts/plotting.md).

## Synthetic data

```python
from openauc.synthetic import SyntheticExperimentConfig, generate_experiment

experiment = generate_experiment(
    SyntheticExperimentConfig(scenario="moving-boundary", n_scans=20, seed=42)
)
```

```bash
openauc generate out/demo --scenario moving-boundary --scans 20 --seed 42
```

Reproducible AUC-*like* datasets for examples, tests and demonstrations, in
eight scenarios covering both radius modes, sparse metadata, mixed optics, empty
scans and deliberate structural faults.

> **Illustrative synthetic data.** The curves are closed-form shapes — **not**
> Lamm-equation solutions, **not** simulations of sedimentation, and carrying no
> physical parameters. Nothing scientific may be inferred from generated data.
> See [synthetic data](docs/concepts/synthetic-data.md).

## AUCX archives

```python
experiment.export("experiment.aucx")            # atomic, deterministic
restored = openauc.load("experiment.aucx")      # every checksum verified first
openauc.inspect_aucx("experiment.aucx")         # what the archive declares
openauc.validate_aucx("experiment.aucx")        # integrity report, never raises
```

`.aucx` is a ZIP of JSON metadata and NumPy `.npy` arrays (format version 1.0),
so dtype, shape, the validity mask and both radius modes survive exactly.
Checksums provide **integrity, not authenticity** — a verified archive is one
whose bytes are unchanged, not one whose origin is proven. See
[AUCX](docs/formats/aucx.md).

Vendor-format readers and any scientific analysis arrive later — see the roadmap in
[`development-log/0001-project-foundation.md`](development-log/0001-project-foundation.md),
the [format docs](docs/formats/) and the concept docs under
[`docs/concepts/`](docs/concepts/).

## Development

```bash
uv sync              # create the environment
uv run ruff check .  # lint
uv run ruff format . # format
uv run mypy          # type-check
uv run pytest        # tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and the Architecture
Decision Records under [`docs/decisions/`](docs/decisions/).

## Documentation

- Architecture Decision Records: [`docs/decisions/`](docs/decisions/)
- Development log: [`development-log/`](development-log/)
- Format specifications: [`docs/formats/`](docs/formats/) —
  [generic delimited](docs/formats/generic-delimited.md),
  [manifest v1](docs/formats/manifest-v1.md),
  [parser detection](docs/formats/parser-detection.md),
  [AUCX](docs/formats/aucx.md)
- Concepts: [`docs/concepts/`](docs/concepts/) — [data model](docs/concepts/data-model.md),
  [units](docs/concepts/units.md),
  [missing & unknown values](docs/concepts/missing-and-unknown-values.md),
  [optical systems](docs/concepts/optical-systems.md),
  [validation tiers](docs/concepts/validation-tiers.md),
  [analysis readiness](docs/concepts/analysis-readiness.md),
  [plotting](docs/concepts/plotting.md),
  [synthetic data](docs/concepts/synthetic-data.md)
- API reference: [`docs/api.md`](docs/api.md)
- Command line: [`docs/cli.md`](docs/cli.md)
- Examples: [`examples/`](examples/)

## Known limitations

- Pre-alpha; APIs may change without notice.
- Generic CSV/TSV and AUCX only. **No vendor or instrument formats** — Beckman
  XL-A/XL-I, Optima, OpenAUC and SEDFIT/SEDPHAT files are not read.
- One signal unit per observation set; no sample-to-scan linkage.
- No unit conversion. Declared units are retained, never converted.
- AUCX holds one experiment per archive, is read whole into memory, and offers
  no encryption or signatures.
- Plotting is single-panel overlay only.
- The CLI has no plotting subcommand and no batch input.

## Scientific non-goals

These are **permanent**, not "not yet":

- no sedimentation-velocity or equilibrium analysis, fitting or modelling;
- no convection, aggregation, meniscus or equilibrium detection;
- no data-quality scoring or scientific-suitability judgement — scientific
  suitability is always reported as `NOT_ASSESSED`;
- no silent inference of missing metadata, and no interpolation, resampling or
  reordering of radial observations.

## Reporting problems

Security issues: see [SECURITY.md](SECURITY.md). Contributions and workflow:
see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Licence

Apache License 2.0. Copyright 2026 Ron Finn. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).

## Citation

If you use `openauc-io`, please cite it using the metadata in
[CITATION.cff](CITATION.cff).
