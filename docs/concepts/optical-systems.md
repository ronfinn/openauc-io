# Optical systems

The model can **represent** five optical-system values via the `OpticalSystem`
enum:

| `OpticalSystem` | Typical signal unit(s) |
|-----------------|------------------------|
| `ABSORBANCE` | absorbance units (`AU`) |
| `INTERFERENCE` | fringes |
| `FLUORESCENCE` | declared instrument or calibrated units |
| `INTENSITY` | declared instrument or calibrated units |
| `UNKNOWN` | any (not judged) |

> **Representation is not support.** That the model can *represent* an optical
> system does **not** mean file import or scientific interpretation for that
> system is implemented or validated. Generic CSV/TSV import records whatever
> optical system the manifest declares; no vendor/instrument reader exists, and
> no optical system is scientifically interpreted.

## Where it is recorded

`OpticalSystem` appears on each `ScanMetadata` (the system used for that scan)
and on `InstrumentMetadata` (the run's primary system). Both default to
`UNKNOWN` — an explicit "not stated", never inferred.

## Optical-system / signal-unit consistency

Structural validation reports a **well-defined** incompatibility between a
scan's optical system and the observations' signal unit:

| Optical system | Compatible signal unit(s) |
|----------------|---------------------------|
| `ABSORBANCE` | `ABSORBANCE_UNIT` |
| `INTERFERENCE` | `FRINGE` |
| `FLUORESCENCE` | `INSTRUMENT_UNIT`, `CALIBRATED_UNIT` |
| `INTENSITY` | `INSTRUMENT_UNIT`, `CALIBRATED_UNIT` |

`UNKNOWN` optical systems, and `UNKNOWN`/`OTHER` signal units, are never flagged
— the model does not guess. A clear conflict (e.g. an `ABSORBANCE` scan with a
`FRINGE` signal unit) is reported as a structural error by
`experiment.validate_structure()`.

An undeclared optical system is reported separately as a non-blocking
`optical_system_unknown` warning, and more than one *declared* system in a
single observation set as `mixed_optical_systems`. A mixture of `UNKNOWN` and
one declared system is partial metadata, not a mix, and is not flagged as one.
See [validation tiers](validation-tiers.md).

## Phase 2 limitation: one signal unit per observation set

`Observations` carries a single `signal_unit` for the whole set. Heterogeneous
signal units across scans in one set are not modelled in this phase, though each
scan retains its own `optical_system`. This is noted in the Phase 2 development
log as a known limitation.
