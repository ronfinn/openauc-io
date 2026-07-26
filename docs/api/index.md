# Python API reference

Curated pages for the **public** surface. Internal helpers are deliberately not
documented here: importability is not a contract.

The stable surface is `openauc` and `openauc.api`. Model types are also
importable from `openauc.models`, and the subpackages `openauc.formats`,
`openauc.plotting` and `openauc.synthetic` carry their own facades.

| Page | Covers |
|------|--------|
| [Top-level API](top-level.md) | `load`, `available_formats`, AUCX entry points |
| [Experiments and metadata](experiments.md) | `AUCExperiment` and the metadata models |
| [Observations](observations.md) | The numeric layer and both radius modes |
| [Validation and readiness](validation.md) | Reports, findings, readiness types |
| [Summaries](summaries.md) | `ExperimentSummary` and its components |
| [Plotting](plotting.md) | `plot_scans`, `plot_scan` |
| [Synthetic generation](synthetic.md) | Config, generator and writers |
| [Generic-delimited ingestion](ingestion.md) | Manifest and parser types |
| [AUCX archives](aucx.md) | Archive functions and records |
| [Exceptions](exceptions.md) | The full hierarchy |

## Import conventions

```python
import openauc                       # light: no matplotlib
from openauc.models import ...       # canonical model types
from openauc.plotting import ...     # imports matplotlib on first draw
from openauc.synthetic import ...    # generator
import openauc.api as api            # the curated facade
```

`openauc.api.plot_scans` resolves lazily, so importing the facade does not pull
in matplotlib.

## A note on what these types promise

Nothing in this API assesses scientific validity. `validate()` reports
structural consistency, `assess_readiness()` reports metadata presence, and
`summary_data()` reports counts and ranges. See
[Scientific boundaries](../concepts/scientific-boundaries.md).
