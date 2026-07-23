"""Exception hierarchy for openauc.

A single, shallow hierarchy so callers can catch ``OpenAUCError`` broadly or
individual subclasses narrowly. These are declarations only; the phases that
raise them add the behaviour.
"""

from __future__ import annotations

__all__ = [
    "ArchiveError",
    "FormatError",
    "ObservationError",
    "OpenAUCError",
    "StructuralValidationError",
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


class ArchiveError(OpenAUCError):
    """Raised when reading or writing an AUCX archive fails."""
