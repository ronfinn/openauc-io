# Missing, unknown and not-applicable values

The model treats **missing**, **unknown** and **not-applicable** as conceptually
different, and never replaces an unknown scientific value with a default.

## Two levels of absence

**Field level.** Optional metadata fields default to `None`, meaning the datum
is structurally absent from the model (for example `ExperimentMetadata.operator`
when no operator was recorded).

**Value level.** Where the distinction matters scientifically, use a `Quantity`
whose `status` records it explicitly:

| Meaning | `ValueStatus` | `Quantity` constructor |
|---------|---------------|------------------------|
| A real value is present | `PRESENT` | `Quantity.of(value, unit)` |
| The source did not provide it | `MISSING` | `Quantity.missing()` |
| The source explicitly says unknown | `UNKNOWN` | `Quantity.unknown()` |
| It does not apply to this experiment | `NOT_APPLICABLE` | `Quantity.not_applicable()` |

A `PRESENT` quantity must carry a finite value; every other status must carry
`None`. These invariants are enforced at construction.

```python
from openauc.models import Quantity, ValueStatus

Quantity.unknown().status          # ValueStatus.UNKNOWN — not the same as MISSING
Quantity.not_applicable().value    # None
Quantity.of(20.0, Unit.DEGREE_CELSIUS).is_present  # True
```

## Value provenance

Each `Quantity` also records where it came from via `ValueProvenance`
(`SUPPLIED`, `CONVERTED`, `INFERRED`, `USER_CONFIRMED`, `UNKNOWN`). This
per-value tag complements the experiment-level `ImportProvenance` record, which
lists values by category (supplied/converted/inferred/user-confirmed/unknown)
alongside the source, checksum, parser and any transformations, warnings and
assumptions.

Because no parser exists in this phase, provenance is constructed by hand for
synthetic experiments and no checksum is computed. See
[ADR-0002](../decisions/ADR-0002-canonical-data-model.md).

## Observations: the authoritative mask

In per-scan mode, shorter scans are padded with `NaN`. Padding is **not**
identified by testing for `NaN` — a measured signal could itself legitimately be
recorded as `NaN`. Instead a boolean **validity mask** is authoritative: a value
is a real observation if and only if its mask entry is `True`. This keeps
missing positions distinguishable from measured values, and no interpolation is
ever performed to fill them.
