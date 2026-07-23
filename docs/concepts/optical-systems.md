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
> system is implemented or validated. Phase 2 implements the representation
> only. No parser exists yet.

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

## Phase 2 limitation: one signal unit per observation set

`Observations` carries a single `signal_unit` for the whole set. Heterogeneous
signal units across scans in one set are not modelled in this phase, though each
scan retains its own `optical_system`. This is noted in the Phase 2 development
log as a known limitation.
