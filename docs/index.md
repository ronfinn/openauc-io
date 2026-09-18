# openauc-io

Open-source Python library for **importing, validating, standardising,
visualising and archiving** analytical ultracentrifugation (AUC) data.

!!! warning "First public alpha — version `0.1.0a1`"
    `0.1.0a1` is the first public alpha, published on
    [PyPI](https://pypi.org/project/openauc/0.1.0a1/) as a pre-release. APIs may
    change without notice. Install it by exact version —
    `python -m pip install "openauc==0.1.0a1"` — or from a clone (see
    [Installation](getting-started/installation.md)).

## What it does

| Capability | Status |
|------------|--------|
| Canonical in-memory experiment model | Implemented |
| Generic long/wide CSV & TSV ingestion via manifests | Implemented |
| Tiered structural validation | Implemented |
| Analysis-readiness reporting | Implemented |
| Structured, JSON-friendly summaries | Implemented |
| Basic scan plotting | Implemented |
| AUCX archival container (`.aucx`) | Implemented |
| Deterministic synthetic data generation | Implemented |
| Command-line interface | Implemented |

## What it does not do

`openauc` performs **no scientific analysis**, and this is permanent, not a
roadmap item:

- no sedimentation-velocity or equilibrium analysis, fitting or modelling;
- no convection, aggregation, meniscus or equilibrium detection;
- no data-quality scoring — scientific suitability is always reported as
  `NOT_ASSESSED`;
- no unit conversion — declared units are retained, never converted;
- no vendor or instrument formats (Beckman XL-A/XL-I, Optima, OpenAUC,
  SEDFIT/SEDPHAT are **not** read).

See [Scientific boundaries](concepts/scientific-boundaries.md) for why.

## Where to start

<div class="grid cards" markdown>

- **New here?** Try it in five minutes with generated data —
  [Five-minute quickstart](getting-started/quickstart.md)

- **Have CSV/TSV data?** —
  [Load generic-long data](tutorials/load-generic-long.md) and
  [Create a manifest](how-to/create-a-manifest.md)

- **Writing Python?** —
  [Complete Python workflow](tutorials/python-workflow.md) and the
  [API reference](api/index.md)

- **Prefer the shell?** —
  [Complete CLI workflow](tutorials/cli-workflow.md) and the
  [CLI reference](cli/index.md)

- **Extending it?** —
  [Architecture decisions](project/decisions.md) and
  [Contributing](project/contributing.md)

</div>

## The vocabulary this project keeps precise

Four ideas are deliberately kept apart throughout the code and these docs:

| Term | Question it answers |
|------|--------------------|
| **Representation** | Can the data be held faithfully, without inference or transformation? |
| **Structural validation** | Are metadata, scans and observations internally consistent? |
| **Analysis readiness** | Is the metadata a future workflow would need actually present? |
| **Scientific suitability** | Is the experiment sound? — **never assessed by this project** |

Confusing them is the single most likely way to misuse this library. See
[Validation tiers](concepts/validation-tiers.md).
