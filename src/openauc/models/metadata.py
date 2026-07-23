"""Shared metadata primitives: the :class:`Quantity` value type and helpers.

``Quantity`` is the model's primitive for a scientific scalar. It retains the
declared unit, records where the value came from, and represents the
present/missing/unknown/not-applicable distinction explicitly. It never infers a
unit from a value and never converts.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from openauc.models.enums import (
    ExperimentType,
    Unit,
    ValueProvenance,
    ValueStatus,
)

__all__ = [
    "ExperimentMetadata",
    "Quantity",
    "reject_negative",
    "require_unit",
]


class Quantity(BaseModel):
    """A scientific scalar with a retained unit, status and provenance.

    Attributes:
        value: The numeric value, or ``None`` when the status is not
            ``PRESENT``. A present value must be finite (never NaN/inf).
        unit: The declared unit. Use ``Unit.OTHER`` with ``unit_label`` for
            open-ended units (e.g. concentration) and ``Unit.UNKNOWN`` when the
            unit is not known. The model never infers this.
        unit_label: Verbatim source unit text, retained when ``unit`` is
            ``OTHER`` or ``UNKNOWN``.
        status: Explicit presence semantics (present/missing/unknown/
            not-applicable).
        provenance: Where the value came from (supplied/converted/inferred/
            user-confirmed/unknown).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None = None
    unit: Unit = Unit.UNKNOWN
    unit_label: str | None = None
    status: ValueStatus = ValueStatus.PRESENT
    provenance: ValueProvenance = ValueProvenance.SUPPLIED

    @model_validator(mode="after")
    def _check_value_status(self) -> Quantity:
        if self.status is ValueStatus.PRESENT:
            if self.value is None:
                raise ValueError("a PRESENT quantity requires a numeric value")
            if not math.isfinite(self.value):
                raise ValueError("quantity value must be finite (not NaN or infinity)")
        elif self.value is not None:
            raise ValueError(
                f"a {self.status.value} quantity must not carry a numeric value"
            )
        return self

    @property
    def is_present(self) -> bool:
        """True only when a real numeric value is carried."""
        return self.status is ValueStatus.PRESENT

    @classmethod
    def of(
        cls,
        value: float,
        unit: Unit,
        *,
        unit_label: str | None = None,
        provenance: ValueProvenance = ValueProvenance.SUPPLIED,
    ) -> Quantity:
        """Build a PRESENT quantity carrying ``value`` in ``unit``."""
        return cls(
            value=value,
            unit=unit,
            unit_label=unit_label,
            status=ValueStatus.PRESENT,
            provenance=provenance,
        )

    @classmethod
    def missing(
        cls, provenance: ValueProvenance = ValueProvenance.SUPPLIED
    ) -> Quantity:
        """A value the source did not provide."""
        return cls(value=None, status=ValueStatus.MISSING, provenance=provenance)

    @classmethod
    def unknown(cls, provenance: ValueProvenance = ValueProvenance.UNKNOWN) -> Quantity:
        """A value the source explicitly marks as unknown."""
        return cls(value=None, status=ValueStatus.UNKNOWN, provenance=provenance)

    @classmethod
    def not_applicable(
        cls, provenance: ValueProvenance = ValueProvenance.SUPPLIED
    ) -> Quantity:
        """A value that does not apply to this experiment."""
        return cls(value=None, status=ValueStatus.NOT_APPLICABLE, provenance=provenance)


class ExperimentMetadata(BaseModel):
    """Experiment identity (area A).

    Only ``experiment_id`` is required. Every other field is optional and, when
    absent, is left as ``None`` (structurally absent) rather than given a
    default value. ``experiment_type`` defaults to ``UNKNOWN`` — an explicit
    "not stated", never an inferred type.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment_id: str
    name: str | None = None
    description: str | None = None
    experiment_type: ExperimentType = ExperimentType.UNKNOWN
    acquired_at: datetime | None = None
    operator: str | None = None
    notes: str | None = None

    @field_validator("experiment_id")
    @classmethod
    def _non_empty_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("experiment_id must be a non-empty string")
        return value


def reject_negative(quantity: Quantity | None, name: str) -> Quantity | None:
    """Raise ``ValueError`` if a present quantity carries a negative value."""
    if quantity is not None and quantity.value is not None and quantity.value < 0:
        raise ValueError(f"{name} must be non-negative, got {quantity.value}")
    return quantity


def require_unit(
    quantity: Quantity | None, name: str, allowed: Iterable[Unit]
) -> Quantity | None:
    """Raise ``ValueError`` if a present quantity uses an unexpected unit.

    ``Unit.UNKNOWN`` is always accepted so that declared-but-unknown units are
    never rejected. This checks representational consistency only; it performs
    no conversion.
    """
    allowed_set = set(allowed)
    if (
        quantity is not None
        and quantity.status is ValueStatus.PRESENT
        and quantity.unit is not Unit.UNKNOWN
        and quantity.unit not in allowed_set
    ):
        expected = ", ".join(sorted(u.value for u in allowed_set))
        raise ValueError(
            f"{name} has unexpected unit {quantity.unit.value}; "
            f"expected one of [{expected}] or unknown"
        )
    return quantity
