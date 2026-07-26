# Handle missing and unknown metadata

**Goal:** keep the four kinds of absence distinct, and know which formats
preserve them.

## The four states

The model never replaces an unknown value with a default.

| Meaning | Representation |
|---------|----------------|
| A real value is present | `Quantity.of(value, unit)` → `PRESENT` |
| The source did not provide it | `Quantity.missing()` → `MISSING` |
| The source explicitly says unknown | `Quantity.unknown()` → `UNKNOWN` |
| It does not apply to this experiment | `Quantity.not_applicable()` → `NOT_APPLICABLE` |

Plus a fifth, structural kind: the **field itself is `None`** — absent from the
model entirely.

```python
from openauc.models import Quantity, ValueStatus

Quantity.unknown().status  # ValueStatus.UNKNOWN — not MISSING
Quantity.not_applicable().value  # None
Quantity.of(20.0, Unit.DEGREE_CELSIUS).is_present  # True
```

A `PRESENT` quantity must carry a finite value; every other status must carry
`None`. Enforced at construction.

## Counting them

```python
summary = experiment.summary_data()
presence = {(e.component, e.field): e for e in summary.metadata_presence}
t = presence[("scan", "temperature")]
t.present, t.missing, t.unknown, t.not_applicable, t.absent
```

All five survive into `summary.to_dict()` and therefore into
`openauc inspect --json`.

## Which formats preserve what

| Format | `PRESENT` | `MISSING` | `UNKNOWN` | `NOT_APPLICABLE` | field absent |
|--------|-----------|-----------|-----------|------------------|--------------|
| In-memory model | ✅ | ✅ | ✅ | ✅ | ✅ |
| **AUCX** | ✅ | ✅ | ✅ | ✅ | ✅ |
| Generic CSV/TSV | ✅ | ✅ | ❌ collapses | ❌ collapses | ✅ |

!!! warning "Generic delimited cannot express 'explicitly unknown'"
    A CSV has no syntax for it, and openauc will not invent a private
    convention. When writing, an optional column is emitted **only when every
    scan has that value `PRESENT`**; otherwise the column is omitted and
    reloads as absent.

    **AUCX is the exact-preservation format.** Use it whenever the distinction
    matters.

Demonstrated:

```python
from openauc.synthetic import (
    SyntheticExperimentConfig,
    generate_experiment,
    write_generic_long,
    write_aucx,
)

sparse = generate_experiment(
    SyntheticExperimentConfig(scenario="sparse-metadata", n_scans=6)
)
from_csv = openauc.load(write_generic_long(sparse, "out/long"))
from_aucx = openauc.load(write_aucx(sparse, "out/sparse.aucx"))

original = {s.elapsed_time.status for s in sparse.scans}
assert ValueStatus.UNKNOWN in original
assert {s.elapsed_time.status for s in from_aucx.scans} == original  # exact
assert ValueStatus.UNKNOWN not in {s.elapsed_time.status for s in from_csv.scans}
```

## How absence is reported

Absent metadata is **reported, never required**. It produces warnings or
informational findings and never makes an experiment invalid:

```python
report = experiment.validate()
[i.code for i in report.warnings]
# ['rotor_speed_absent', 'temperature_absent', 'no_samples', ...]
```

A dataset carrying only an identifier, a radius vector and a signal vector is
archivable and structurally valid.

## Choosing a state when building experiments

- The instrument recorded nothing → `Quantity.missing()`
- The source file explicitly says "unknown" → `Quantity.unknown()`
- The quantity is meaningless for this run → `Quantity.not_applicable()`
- You never modelled the field → leave it `None`

Never substitute a plausible number for an absent one. That is inference, and
openauc does not do it.

## Next step

- [Missing, unknown and not-applicable](../concepts/missing-and-unknown-values.md)
- [Create a manifest](create-a-manifest.md)
