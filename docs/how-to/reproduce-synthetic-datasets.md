# Reproduce synthetic datasets

**Goal:** get byte-identical generated data again, later or elsewhere.

## What determines the output

Everything is a pure function of the `SyntheticExperimentConfig` — including the
`seed`. There is no hidden state.

```python
from openauc.synthetic import SyntheticExperimentConfig, generate_experiment

config = SyntheticExperimentConfig(
    scenario="moving-boundary", n_scans=20, n_points=300, seed=42
)
a = generate_experiment(config)
b = generate_experiment(config)
assert a.to_dict() == b.to_dict()
```

## Record the configuration, not the file

```python
import json

Path("config.json").write_text(json.dumps(config.model_dump(mode="json"), indent=2))

# later
restored = SyntheticExperimentConfig.model_validate(
    json.loads(Path("config.json").read_text())
)
assert generate_experiment(restored).to_dict() == a.to_dict()
```

The config is frozen with `extra="forbid"`, so a stale field name fails loudly
rather than being ignored.

## Byte-identical archives

`to_dict()` equality is not byte equality — an AUCX archive records its export
time. Pin it:

```python
from datetime import UTC, datetime

fixed = datetime(2026, 1, 1, tzinfo=UTC)
first = a.export("a.aucx", exported_at=fixed)
second = b.export("b.aucx", exported_at=fixed)
assert first.read_bytes() == second.read_bytes()
```

Omit `exported_at` in normal use; pin it in tests and fixtures.

## The global random state is safe

Noise is drawn from `numpy.random.default_rng(config.seed)` — a local generator.
**NumPy's global random state is never read or written**, so generating data
cannot perturb anything else in your process, and nothing else can perturb your
generated data.

```python
import numpy as np

np.random.seed(1234)
before = np.random.get_state()
generate_experiment(config)
assert np.array_equal(np.random.get_state()[1], before[1])  # untouched
```

## With `noise_level=0`

The seed does not affect the data at all — the curves are deterministic
functions of the configuration:

```python
x = generate_experiment(SyntheticExperimentConfig(seed=1, noise_level=0.0))
y = generate_experiment(SyntheticExperimentConfig(seed=999, noise_level=0.0))
assert x.to_dict()["observations"] == y.to_dict()["observations"]
assert x.to_dict()["provenance"] != y.to_dict()["provenance"]  # seed recorded
```

The seed is still recorded in provenance, honestly.

## From the CLI

```bash
uv run openauc generate demo.aucx --format aucx \
  --scenario moving-boundary --scans 20 --points 300 --seed 42
```

Re-running with identical options reproduces the same experiment. The archive
bytes differ only because the export timestamp differs; the model does not.

## When reproduction fails

| Symptom | Cause |
|---------|-------|
| Different data, same seed | A config field changed — diff the two configs |
| Different data, no config change | An openauc version change; check `openauc version` |
| Same model, different archive bytes | `exported_at` was not pinned |

## Next step

- [Generate synthetic data](../tutorials/generate-synthetic-data.md)
- [Synthetic data concepts](../concepts/synthetic-data.md)
