"""Sample metadata (area C).

Only ``sample_id`` is required. Physico-chemical quantities (concentration,
density, viscosity, partial specific volume) are optional and retain their
declared units. No analysis-level requirements are imposed on archival metadata,
and no scientific ranges are enforced beyond the finiteness that every
:class:`~openauc.models.metadata.Quantity` already guarantees.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from openauc.models.metadata import Quantity

__all__ = ["SampleMetadata"]


class SampleMetadata(BaseModel):
    """Sample and buffer metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sample_id: str
    description: str | None = None
    buffer_description: str | None = None
    concentration: Quantity | None = None
    density: Quantity | None = None
    viscosity: Quantity | None = None
    partial_specific_volume: Quantity | None = None
    notes: str | None = None

    @field_validator("sample_id")
    @classmethod
    def _non_empty_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sample_id must be a non-empty string")
        return value
