# Units

The model **retains declared units** and never infers a unit from a value or
converts silently. Units are represented by the `Unit` enum and carried on the
`Quantity` value type.

## Canonical units

| Physical quantity | Canonical unit | `Unit` member |
|-------------------|----------------|---------------|
| Radius | centimetres | `CENTIMETRE` (`cm`) |
| Elapsed time | seconds | `SECOND` (`s`) |
| Rotor speed | revolutions per minute | `RPM` (`rpm`) |
| Temperature | degrees Celsius | `DEGREE_CELSIUS` (`degC`) |
| Wavelength | nanometres | `NANOMETRE` (`nm`) |
| Sedimentation coefficient | seconds | `SECOND` (`s`) |
| Diffusion coefficient | cm² s⁻¹ | `SQUARE_CENTIMETRE_PER_SECOND` (`cm2/s`) |
| Absorbance signal | absorbance units | `ABSORBANCE_UNIT` (`AU`) |
| Interference signal | fringes | `FRINGE` (`fringe`) |
| Fluorescence signal | declared instrument or calibrated units | `INSTRUMENT_UNIT` / `CALIBRATED_UNIT` |
| Intensity signal | declared instrument or calibrated units | `INSTRUMENT_UNIT` / `CALIBRATED_UNIT` |

Open-ended units (for example concentration in `mg/mL`) use `Unit.OTHER` with
the verbatim text retained in `Quantity.unit_label`. When a unit is genuinely
not known, use `Unit.UNKNOWN`.

## Unit behaviour (Phase 2 policy)

- Retain the original declared unit.
- Represent unknown units explicitly (`Unit.UNKNOWN`), never guess.
- Do **not** infer units from numerical values.
- Do **not** silently convert values.
- Conversions, when later introduced, must be explicit and recorded in
  provenance (`ValueProvenance.CONVERTED`).
- No unit-library dependency (e.g. Pint) is added in this phase. Any future
  adoption will be recorded in an ADR amendment.

## Consistency checks, not conversions

Metadata fields perform light **representational** checks: a present rotor-speed
quantity, for instance, must use `RPM` or `UNKNOWN` — it is never converted to
`RPM`. `Unit.UNKNOWN` is always accepted so declared-but-unknown units are never
rejected.

```python
from openauc.models import Quantity, Unit, ValueProvenance

Quantity.of(50000.0, Unit.RPM)                       # present, supplied
Quantity.of(0.5, Unit.OTHER, unit_label="mg/mL")     # open-ended unit retained
Quantity.of(4.3, Unit.SECOND, provenance=ValueProvenance.CONVERTED)  # tagged
```
