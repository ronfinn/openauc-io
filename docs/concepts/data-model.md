# The canonical AUC data model

The canonical model is the single in-memory representation every import path
converges on. It is a **data-representation layer**: it preserves what was
supplied and makes no judgement about scientific validity or suitability for
analysis. See [ADR-0002](../decisions/ADR-0002-canonical-data-model.md).

## Two layers

- **Metadata** — pydantic v2 models (frozen, `extra="forbid"`): experiment
  identity, instrument/run, samples, and per-scan metadata.
- **Observations** — an [xarray](https://docs.xarray.dev/)-backed store of the
  numeric radial signal, built on NumPy.

`AUCExperiment` composes the two. It is a **frozen dataclass** (not a pydantic
model) so it can hold the xarray-backed `Observations` without forcing pydantic
to serialise an array layer it does not own.

```python
from openauc.models import (
    AUCExperiment, ExperimentMetadata, ScanMetadata, Observations, Quantity,
    Unit, OpticalSystem,
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
report = experiment.validate_structure()
assert report.is_valid
```

## Model areas

| Area | Model | Required field(s) |
|------|-------|-------------------|
| Experiment identity | `ExperimentMetadata` | `experiment_id` |
| Instrument & run | `InstrumentMetadata` | none (all optional) |
| Sample | `SampleMetadata` | `sample_id` |
| Scan | `ScanMetadata` | `scan_id`, `index`, `elapsed_time` |
| Observations | `Observations` | radius/signal arrays + `scan_ids` |
| Provenance | `ImportProvenance` | none (all optional) |

Nominal rotor speed lives on the instrument; the *actual* per-scan speed and
temperature live on each `ScanMetadata`.

## Radius axes: shared and per-scan

Observations are stored in one of two explicit modes (`RadiusAxisMode`):

- **Shared** — every scan shares one radius axis. The backing dataset has a 1-D
  `radius` coordinate and a `signal` variable with dims `(scan, radius)`.
- **Per-scan** — each scan carries its own radius vector. Vectors are stored in
  **padded 2-D arrays** with dims `(scan, point)` plus an **authoritative
  boolean validity mask**. Shorter scans are padded with `NaN` *and*
  `mask=False`. A value is a real observation **if and only if** its mask entry
  is `True`; padding is never presented as measured data.

Nothing is interpolated or resampled. See
[missing-and-unknown-values](missing-and-unknown-values.md) for why the mask is
authoritative rather than relying on `NaN`.

```python
obs = Observations.from_per_scan(
    radii=[[6.0, 6.1, 6.2], [6.0, 6.05]],   # different lengths
    signals=[[0.1, 0.2, 0.3], [0.4, 0.5]],
    scan_ids=["a", "b"],
    signal_unit=Unit.FRINGE,
)
obs.points_per_scan()      # (3, 2) — real observations per scan
obs.valid_radius_values()  # excludes padding
```

Construction validates geometry and finiteness and raises
`ObservationError` on malformed input, so an invalid `Observations` cannot
exist.

## Validation

`experiment.validate_structure()` returns a `ValidationReport` (it never
raises). It checks representational consistency only — identifier uniqueness,
scan/observation agreement, positive radius values, and well-defined
optical-system/signal-unit combinations. It is **not** scientific quality
control. Field-level invariants (finiteness, non-negative time and wavelength,
valid masks) are enforced earlier, at construction, and raise immediately.

See the source module `openauc.models.validation` and the
[API reference](../api.md).

## Serialisation

- Metadata round-trips through pydantic (`model_dump` / `model_validate`,
  including JSON).
- `Observations.to_dict()` / `from_dict()` round-trips the numeric layer using
  plain Python types; per-scan padding is written as `null` and the mask is
  written explicitly.
- `AUCExperiment.to_dict()` / `from_dict()` round-trips the whole experiment.

This JSON-friendly serialisation is the in-memory foundation the Phase 6 AUCX
archive will build on. **Writing or reading `.aucx` archives is not implemented
in this phase.**
