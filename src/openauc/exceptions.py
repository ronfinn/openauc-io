"""Exception hierarchy for openauc.

A single, shallow hierarchy so callers can catch ``OpenAUCError`` broadly or
individual subclasses narrowly. These are declarations only; the phases that
raise them add the behaviour.
"""

from __future__ import annotations

__all__ = [
    "AmbiguousFormatError",
    "ArchiveError",
    "ArchiveIntegrityError",
    "ArchiveVersionError",
    "DataConflictError",
    "FormatError",
    "ManifestError",
    "ObservationError",
    "OpenAUCError",
    "ParseError",
    "PlottingError",
    "StructuralValidationError",
    "UnsupportedFormatError",
    "ValidationError",
]


class OpenAUCError(Exception):
    """Base class for all errors raised by openauc."""


class ValidationError(OpenAUCError):
    """Raised when data or metadata fails structural validation."""


class StructuralValidationError(ValidationError):
    """Raised when a structural-validation report contains errors.

    Produced by :meth:`ValidationReport.raise_if_invalid`. Structural
    validation is a data-representation check only; it makes no judgement about
    scientific validity or suitability for analysis.
    """


class ObservationError(OpenAUCError):
    """Raised when observational (radius/signal/mask) arrays are malformed.

    Examples: non-finite radius or signal, mismatched array shapes, or a
    per-scan validity mask that is inconsistent with its data.
    """


class FormatError(OpenAUCError):
    """Raised when input cannot be read as its declared format."""


class UnsupportedFormatError(FormatError):
    """Raised when no registered parser can handle the input.

    Also raised when an explicitly requested format identifier is not
    registered.
    """


class AmbiguousFormatError(FormatError):
    """Raised when input cannot be resolved to a single parser or manifest.

    Examples: two parsers report materially similar detection confidence; a
    directory contains both ``manifest.json`` and ``manifest.yaml`` without an
    explicit choice; or the delimiter cannot be determined unambiguously.
    """


class ParseError(FormatError):
    """Raised when a data file is structurally malformed for its format.

    Examples: missing required columns, non-numeric or non-finite radius or
    signal values, or inconsistent field counts.
    """


class ManifestError(OpenAUCError):
    """Raised when an experiment manifest is invalid or unsafe.

    Examples: unknown schema version, a data path that escapes the experiment
    directory, or a manifest that fails schema validation.
    """


class DataConflictError(OpenAUCError):
    """Raised when independent sources disagree.

    Examples: duplicate ``(scan, radius)`` observations, the same metadatum
    supplied with different values in the table and the manifest, or file
    contents that contradict the manifest's declared format.
    """


class ArchiveError(OpenAUCError):
    """Raised when reading or writing an AUCX archive fails.

    Covers container-level problems: an unreadable or unsafe ZIP, a missing or
    unexpected member, malformed JSON or ``.npy`` payloads, and disagreements
    between the manifest and the stored arrays.
    """


class ArchiveIntegrityError(ArchiveError):
    """Raised when an archive's recorded checksums do not verify.

    Integrity only: a passing checksum shows the bytes are unchanged since the
    archive was written. It is **not** a proof of authenticity or origin.
    """


class ArchiveVersionError(ArchiveError):
    """Raised when an archive declares an unsupported format version.

    Archives are never silently migrated across format versions.
    """


class PlottingError(OpenAUCError):
    """Raised when a plot cannot be drawn from the supplied experiment.

    Examples: a requested scan identifier is not present in the observations,
    or no selected scan carries any observation to draw.
    """
