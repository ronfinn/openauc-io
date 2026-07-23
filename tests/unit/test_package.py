"""Smoke tests for the Phase 1 package scaffold."""

from __future__ import annotations

import openauc
from openauc import api
from openauc.exceptions import (
    ArchiveError,
    FormatError,
    OpenAUCError,
    ValidationError,
)


def test_version_is_a_nonempty_string() -> None:
    assert isinstance(openauc.__version__, str)
    assert openauc.__version__


def test_api_reexports_version() -> None:
    assert api.__version__ == openauc.__version__


def test_exception_hierarchy() -> None:
    for exc in (ValidationError, FormatError, ArchiveError):
        assert issubclass(exc, OpenAUCError)
