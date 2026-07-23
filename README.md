# openauc-io

Open-source Python library for importing, validating, standardising, visualising
and archiving analytical ultracentrifugation (AUC) data.

> **Status: pre-alpha (Phase 1 foundation).** Nothing is released yet and no
> scientific functionality is implemented. The current tree is packaging,
> tooling and documentation scaffolding only. APIs will change without notice.

## Scope

`openauc` aims to support historical and modern AUC formats over time. The
**first alpha release** is intentionally narrow and will provide:

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

Not yet published to PyPI. For development:

```bash
git clone https://github.com/ronfinn/openauc-io
cd openauc-io
uv sync
```

## Quickstart

The CLI currently reports the version:

```bash
uv run openauc version
```

The canonical data model (Phase 2) can be constructed in memory. It preserves
raw observations, retains declared units, represents missing/unknown values
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

Structural validation and `summary()` describe data structure only; they make no
claim about scientific validity or suitability for analysis. Reading and writing
files (CSV/TSV, `.aucx`), plotting, and scientific analysis arrive in later
phases — see the roadmap in
[`development-log/0001-project-foundation.md`](development-log/0001-project-foundation.md)
and the concept docs under [`docs/concepts/`](docs/concepts/).

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
- Format specifications: [`docs/formats/`](docs/formats/)
- Concepts: [`docs/concepts/`](docs/concepts/) — [data model](docs/concepts/data-model.md),
  [units](docs/concepts/units.md),
  [missing & unknown values](docs/concepts/missing-and-unknown-values.md),
  [optical systems](docs/concepts/optical-systems.md)
- API reference: [`docs/api.md`](docs/api.md)

## Licence

Apache License 2.0. Copyright 2026 Ron Finn. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).

## Citation

If you use `openauc-io`, please cite it using the metadata in
[CITATION.cff](CITATION.cff).
