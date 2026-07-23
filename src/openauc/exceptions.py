"""Exception hierarchy for openauc.

A single, shallow hierarchy so callers can catch ``OpenAUCError`` broadly or
individual subclasses narrowly. These are declarations only; the phases that
raise them add the behaviour.
"""

from __future__ import annotations

__all__ = [
    "ArchiveError",
    "FormatError",
    "OpenAUCError",
    "ValidationError",
]


class OpenAUCError(Exception):
    """Base class for all errors raised by openauc."""


class ValidationError(OpenAUCError):
    """Raised when data or metadata fails structural validation."""


class FormatError(OpenAUCError):
    """Raised when input cannot be read as its declared format."""


class ArchiveError(OpenAUCError):
    """Raised when reading or writing an AUCX archive fails."""
