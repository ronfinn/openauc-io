# Beckman XL-I interference scan files (`.ip1`) — narrow reader

`openauc` reads **one documented layout** of Beckman Coulter XL-I interference
scan file. This is a deliberately narrow reader, **not** general Beckman
support, and it carries **no manufacturer endorsement**.

Header meanings follow the manufacturer's *ProteomeLab XL-A/XL-I Instructions
For Use*, PN LXLAI-IM-10AB, February 2014. The reader was checked against the
public SEDFIT IgG example dataset (226 scans; not redistributed here).

## Supported layout

| Part | Required form |
|------|---------------|
| File name | digits plus `.ip1`, case-insensitive (`00001.ip1`, `00001.IP1`) |
| Encoding | ASCII text; CRLF or LF line ends |
| Line 1 | `cm/pixel: <positive number>, <user comment>` |
| Line 2 | exactly 8 whitespace-separated tokens (see below) |
| Remaining lines | exactly two finite numbers per line, at least one line |

One trailing whitespace-only line is accepted (the public files end with one);
any other blank line is an error. Load a single file or a directory of `.ip1`
files, with no manifest:

```python
import openauc

experiment = openauc.load("path/to/scans/")  # or a single .ip1 file
experiment = openauc.load("path/to/scans/", format="ip1")
```

Detection is conservative: a `.ip1` file, or a directory containing `.ip1`
files, is claimed only when no manifest is supplied or adjacent. A directory
holding other XL-A/XL-I scan names (`.ra1`, `.wa1`, `.ip2`, …) is rejected, not
partly read. Absorbance, `.ra*`, `.wa*` and any other variant are **unsupported**.

## Header fields

| Source | Handling |
|--------|----------|
| file name | scan number kept as the scan id (`00001`); scans ordered by number |
| token 2 | cell number, `ScanMetadata.cell` |
| token 3 | temperature, `degC` |
| token 4 | rotor speed, `rpm` |
| token 5 | total seconds, `ScanMetadata.elapsed_time` (`s`) |
| token 1 (`P`) | raw only |
| token 6 | integrated ω²t, raw only |
| token 7 | raw only. **Read as `675` in the public data; the manual states 665 nm.** The recorded value is kept and *not* mapped to a wavelength |
| token 8 | replicate count, raw only |
| `cm/pixel` | raw only (no canonical field) |
| user comment | raw only; text after the first comma, surrounding whitespace trimmed |

Raw values are kept as scan annotations: `ip1:cm_per_pixel=…`,
`ip1:comment=…` and `ip1:header_tokens=[…]` (all eight tokens, verbatim text).
The comment is never used as a sample: a comment of `Sample` creates no
`SampleMetadata`, and no sample link, timestamp or experiment type is inferred.

**Where units come from.** The files contain no units. Temperature (`degC`),
rotor speed (`rpm`) and elapsed time (`s`) are the units the manual documents;
they are applied by the reader and listed in the import provenance
assumptions. They are not read from the file text.

## Observations

Column 1 is read as the recorded radius (cm) and column 2 as the recorded
interference signal. These column semantics are less explicitly specified than
the header, so they are part of the **narrow supported contract** rather than an
independently verified fact. The signal unit is **not documented** and is
recorded as `unknown`.

Values are parsed exactly as written. Nothing is interpolated, regridded,
sorted, smoothed, normalised or baseline-corrected, and radius is never
reconstructed from `cm/pixel`. If every scan recorded bit-identical radii the
experiment uses one shared radius axis; otherwise each scan keeps its own
(per-scan axis). Grids are never reconciled.

## Failure behaviour

A wrong token count, non-numeric or non-finite number, non-positive `cm/pixel`,
non-integer cell, negative speed or time, missing data rows, a blank interior
line, non-ASCII bytes, an unsupported file name or a duplicate scan number
raises an error naming the file. Nothing is repaired.

## Not known from these files

Wavelength, channel, sample, instrument identity, acquisition timestamps, signal
unit and the meaning of the user comment. Structural validation of the loaded
experiment says nothing about scientific validity.
