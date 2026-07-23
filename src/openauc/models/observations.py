"""Observational radial signal data (area E), backed by xarray.

The :class:`Observations` object stores the measured radial signal for a set of
scans in one of two explicit modes:

* **Shared** — every scan shares a single radius axis. The dataset has a 1-D
  ``radius`` coordinate and ``signal`` with dims ``(scan, radius)``.
* **Per-scan** — each scan carries its own radius vector. Vectors are stored in
  padded 2-D arrays with dims ``(scan, point)`` alongside an **authoritative
  boolean validity mask**. Shorter scans are padded with ``NaN`` *and*
  ``mask=False``; a value is a real observation **iff** its mask entry is
  ``True``. Padding is never presented as measured data, and nothing is
  interpolated or resampled.

Construction validates geometry and finiteness and raises
:class:`~openauc.exceptions.ObservationError` on any malformed input, so an
invalid :class:`Observations` cannot exist.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import xarray as xr
from numpy.typing import NDArray

from openauc.exceptions import ObservationError
from openauc.models.enums import RadiusAxisMode, Unit

__all__ = ["Observations"]

_MODE_ATTR = "mode"
_SIGNAL_UNIT_ATTR = "signal_unit"
_RADIUS_UNIT_ATTR = "radius_unit"


def _unique_or_raise(scan_ids: Sequence[str]) -> None:
    seen: set[str] = set()
    for scan_id in scan_ids:
        if not scan_id or not scan_id.strip():
            raise ObservationError("scan_id must be a non-empty string")
        if scan_id in seen:
            raise ObservationError(f"duplicate scan_id in observations: {scan_id!r}")
        seen.add(scan_id)


class Observations:
    """xarray-backed radial signal store (shared or per-scan radius axes).

    Prefer the :meth:`from_shared_axis` and :meth:`from_per_scan` factories.
    The constructor accepts a pre-built :class:`xarray.Dataset` and validates it,
    which supports round-tripping and defensive checks on hand-built datasets.
    """

    __slots__ = ("_dataset",)

    def __init__(self, dataset: xr.Dataset) -> None:
        self._validate_dataset(dataset)
        self._dataset = dataset

    # -- construction --------------------------------------------------------

    @classmethod
    def from_shared_axis(
        cls,
        *,
        radius: Sequence[float] | NDArray[np.float64],
        signal: Sequence[Sequence[float]] | NDArray[np.float64],
        scan_ids: Sequence[str],
        signal_unit: Unit = Unit.UNKNOWN,
        radius_unit: Unit = Unit.CENTIMETRE,
    ) -> Observations:
        """Build shared-axis observations from one radius axis and a 2-D signal.

        Args:
            radius: 1-D shared radius axis of length ``m``.
            signal: 2-D signal of shape ``(n_scans, m)``.
            scan_ids: ``n_scans`` unique, non-empty identifiers.
            signal_unit: Declared signal unit (retained, not converted).
            radius_unit: Declared radius unit (default centimetres).
        """
        radius_arr = np.asarray(radius, dtype=float)
        signal_arr = np.asarray(signal, dtype=float)
        if radius_arr.ndim != 1:
            raise ObservationError("shared radius axis must be 1-D")
        if signal_arr.ndim != 2:
            raise ObservationError("signal must be 2-D with dims (scan, radius)")
        n_scans, n_radius = signal_arr.shape
        if radius_arr.shape[0] != n_radius:
            raise ObservationError(
                "radius length must match the signal's radius dimension"
            )
        if len(scan_ids) != n_scans:
            raise ObservationError(
                "number of scan_ids must match the signal's scan dimension"
            )
        _unique_or_raise(scan_ids)
        if not bool(np.all(np.isfinite(radius_arr))):
            raise ObservationError("radius contains non-finite values")
        if not bool(np.all(np.isfinite(signal_arr))):
            raise ObservationError("signal contains non-finite values")
        dataset = xr.Dataset(
            data_vars={"signal": (("scan", "radius"), signal_arr)},
            coords={
                "scan_id": ("scan", list(scan_ids)),
                "radius": ("radius", radius_arr),
            },
            attrs={
                _MODE_ATTR: RadiusAxisMode.SHARED.value,
                _SIGNAL_UNIT_ATTR: Unit(signal_unit).value,
                _RADIUS_UNIT_ATTR: Unit(radius_unit).value,
            },
        )
        return cls(dataset)

    @classmethod
    def from_per_scan(
        cls,
        *,
        radii: Sequence[Sequence[float] | NDArray[np.float64]],
        signals: Sequence[Sequence[float] | NDArray[np.float64]],
        scan_ids: Sequence[str],
        signal_unit: Unit = Unit.UNKNOWN,
        radius_unit: Unit = Unit.CENTIMETRE,
    ) -> Observations:
        """Build per-scan observations, padding to a rectangle with a mask.

        Each scan's radius/signal vectors may differ in length. They are stored
        in ``(scan, point)`` arrays padded with ``NaN``; the accompanying mask
        marks the real observations. No interpolation is performed.
        """
        n_scans = len(scan_ids)
        if len(radii) != n_scans or len(signals) != n_scans:
            raise ObservationError("radii, signals and scan_ids must have equal length")
        _unique_or_raise(scan_ids)

        radius_rows = [np.asarray(r, dtype=float) for r in radii]
        signal_rows = [np.asarray(s, dtype=float) for s in signals]
        lengths: list[int] = []
        for i, (r, s) in enumerate(zip(radius_rows, signal_rows, strict=True)):
            if r.ndim != 1 or s.ndim != 1:
                raise ObservationError(f"scan {i}: radius and signal must be 1-D")
            if r.shape[0] != s.shape[0]:
                raise ObservationError(
                    f"scan {i}: radius and signal lengths differ "
                    f"({r.shape[0]} vs {s.shape[0]})"
                )
            if not bool(np.all(np.isfinite(r))):
                raise ObservationError(f"scan {i}: radius contains non-finite values")
            if not bool(np.all(np.isfinite(s))):
                raise ObservationError(f"scan {i}: signal contains non-finite values")
            lengths.append(int(r.shape[0]))

        max_len = max(lengths) if lengths else 0
        radius_arr = np.full((n_scans, max_len), np.nan, dtype=float)
        signal_arr = np.full((n_scans, max_len), np.nan, dtype=float)
        mask_arr = np.zeros((n_scans, max_len), dtype=bool)
        for i, (r, s) in enumerate(zip(radius_rows, signal_rows, strict=True)):
            length = lengths[i]
            radius_arr[i, :length] = r
            signal_arr[i, :length] = s
            mask_arr[i, :length] = True

        dataset = xr.Dataset(
            data_vars={
                "radius": (("scan", "point"), radius_arr),
                "signal": (("scan", "point"), signal_arr),
                "mask": (("scan", "point"), mask_arr),
            },
            coords={"scan_id": ("scan", list(scan_ids))},
            attrs={
                _MODE_ATTR: RadiusAxisMode.PER_SCAN.value,
                _SIGNAL_UNIT_ATTR: Unit(signal_unit).value,
                _RADIUS_UNIT_ATTR: Unit(radius_unit).value,
            },
        )
        return cls(dataset)

    # -- validation ----------------------------------------------------------

    @staticmethod
    def _validate_dataset(dataset: xr.Dataset) -> None:
        mode_value = dataset.attrs.get(_MODE_ATTR)
        try:
            mode = RadiusAxisMode(str(mode_value))
        except ValueError as exc:
            raise ObservationError(
                f"dataset has missing or invalid mode attribute: {mode_value!r}"
            ) from exc
        if "scan_id" not in dataset.coords:
            raise ObservationError("dataset must carry a 'scan_id' coordinate")
        scan_ids = [str(x) for x in dataset["scan_id"].to_numpy().tolist()]
        _unique_or_raise(scan_ids)

        if mode is RadiusAxisMode.SHARED:
            Observations._validate_shared(dataset)
        else:
            Observations._validate_per_scan(dataset)

    @staticmethod
    def _validate_shared(dataset: xr.Dataset) -> None:
        if "radius" not in dataset.coords:
            raise ObservationError("shared-mode dataset needs a 'radius' coordinate")
        if "signal" not in dataset.data_vars:
            raise ObservationError("shared-mode dataset needs a 'signal' variable")
        if dataset["signal"].dims != ("scan", "radius"):
            raise ObservationError("signal must have dims (scan, radius)")
        if not bool(np.all(np.isfinite(dataset["radius"].to_numpy()))):
            raise ObservationError("radius contains non-finite values")
        if not bool(np.all(np.isfinite(dataset["signal"].to_numpy()))):
            raise ObservationError("signal contains non-finite values")

    @staticmethod
    def _validate_per_scan(dataset: xr.Dataset) -> None:
        for name in ("radius", "signal", "mask"):
            if name not in dataset.data_vars:
                raise ObservationError(f"per-scan dataset needs a '{name}' variable")
            if dataset[name].dims != ("scan", "point"):
                raise ObservationError(f"{name} must have dims (scan, point)")
        mask = dataset["mask"].to_numpy()
        if mask.dtype != np.bool_:
            raise ObservationError("mask must be a boolean array")
        radius = dataset["radius"].to_numpy()
        signal = dataset["signal"].to_numpy()
        if radius.shape != mask.shape or signal.shape != mask.shape:
            raise ObservationError("radius, signal and mask must share the same shape")
        # Every masked-in position must be a real, finite observation.
        if not bool(np.all(np.isfinite(radius[mask]))):
            raise ObservationError(
                "a masked-in radius position is non-finite (padding marked valid)"
            )
        if not bool(np.all(np.isfinite(signal[mask]))):
            raise ObservationError(
                "a masked-in signal position is non-finite (padding marked valid)"
            )

    # -- accessors -----------------------------------------------------------

    @property
    def dataset(self) -> xr.Dataset:
        """The backing :class:`xarray.Dataset`. Treat as immutable."""
        return self._dataset

    @property
    def mode(self) -> RadiusAxisMode:
        """Whether the radius axis is shared or per-scan."""
        return RadiusAxisMode(str(self._dataset.attrs[_MODE_ATTR]))

    @property
    def signal_unit(self) -> Unit:
        """The retained signal unit."""
        return Unit(str(self._dataset.attrs[_SIGNAL_UNIT_ATTR]))

    @property
    def radius_unit(self) -> Unit:
        """The retained radius unit."""
        return Unit(str(self._dataset.attrs[_RADIUS_UNIT_ATTR]))

    @property
    def scan_ids(self) -> tuple[str, ...]:
        """Ordered scan identifiers along the scan dimension."""
        return tuple(str(x) for x in self._dataset["scan_id"].to_numpy().tolist())

    @property
    def n_scans(self) -> int:
        """Number of scans."""
        return int(self._dataset.sizes["scan"])

    def points_per_scan(self) -> tuple[int, ...]:
        """Count of real observations per scan (mask sum, or width if shared)."""
        if self.mode is RadiusAxisMode.SHARED:
            width = int(self._dataset.sizes["radius"])
            return tuple(width for _ in range(self.n_scans))
        mask = self._dataset["mask"].to_numpy()
        return tuple(int(row.sum()) for row in mask)

    def valid_radius_values(self) -> NDArray[np.float64]:
        """All real radius observations, flattened (padding excluded)."""
        if self.mode is RadiusAxisMode.SHARED:
            return np.asarray(self._dataset["radius"].to_numpy(), dtype=float)
        radius = self._dataset["radius"].to_numpy()
        mask = self._dataset["mask"].to_numpy()
        return np.asarray(radius[mask], dtype=float)

    def radius_range(self) -> tuple[float, float] | None:
        """(min, max) over real radius observations, or ``None`` if empty."""
        values = self.valid_radius_values()
        if values.size == 0:
            return None
        return (float(values.min()), float(values.max()))

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain JSON-friendly Python types.

        Per-scan padding is written as ``None`` (JSON ``null``) so it is never
        mistaken for a measured value; the authoritative mask is written too.
        """
        common: dict[str, Any] = {
            _MODE_ATTR: self.mode.value,
            _SIGNAL_UNIT_ATTR: self.signal_unit.value,
            _RADIUS_UNIT_ATTR: self.radius_unit.value,
            "scan_ids": list(self.scan_ids),
        }
        if self.mode is RadiusAxisMode.SHARED:
            common["radius"] = self._dataset["radius"].to_numpy().tolist()
            common["signal"] = self._dataset["signal"].to_numpy().tolist()
            return common
        mask = self._dataset["mask"].to_numpy()
        radius = self._dataset["radius"].to_numpy()
        signal = self._dataset["signal"].to_numpy()
        common["mask"] = [[bool(v) for v in row] for row in mask]
        common["radius"] = _rows_with_nulls(radius, mask)
        common["signal"] = _rows_with_nulls(signal, mask)
        return common

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Observations:
        """Reconstruct from :meth:`to_dict` output."""
        mode = RadiusAxisMode(str(data[_MODE_ATTR]))
        signal_unit = Unit(str(data[_SIGNAL_UNIT_ATTR]))
        radius_unit = Unit(str(data[_RADIUS_UNIT_ATTR]))
        scan_ids = [str(x) for x in data["scan_ids"]]
        if mode is RadiusAxisMode.SHARED:
            return cls.from_shared_axis(
                radius=np.asarray(data["radius"], dtype=float),
                signal=np.asarray(data["signal"], dtype=float),
                scan_ids=scan_ids,
                signal_unit=signal_unit,
                radius_unit=radius_unit,
            )
        mask = data["mask"]
        radii: list[list[float]] = []
        signals: list[list[float]] = []
        for i in range(len(scan_ids)):
            row_mask = [bool(v) for v in mask[i]]
            radius_row = data["radius"][i]
            signal_row = data["signal"][i]
            radii.append(
                [float(radius_row[j]) for j, keep in enumerate(row_mask) if keep]
            )
            signals.append(
                [float(signal_row[j]) for j, keep in enumerate(row_mask) if keep]
            )
        return cls.from_per_scan(
            radii=radii,
            signals=signals,
            scan_ids=scan_ids,
            signal_unit=signal_unit,
            radius_unit=radius_unit,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Observations):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __hash__(self) -> int:  # pragma: no cover - not used as a key
        return hash(tuple(self.scan_ids))

    def __repr__(self) -> str:
        return (
            f"Observations(mode={self.mode.value!r}, n_scans={self.n_scans}, "
            f"signal_unit={self.signal_unit.value!r})"
        )


def _rows_with_nulls(
    values: NDArray[np.float64], mask: NDArray[np.bool_]
) -> list[list[float | None]]:
    """Render a padded array as rows, writing ``None`` where the mask is False."""
    rendered: list[list[float | None]] = []
    for value_row, mask_row in zip(values, mask, strict=True):
        rendered.append(
            [
                float(v) if keep else None
                for v, keep in zip(value_row, mask_row, strict=True)
            ]
        )
    return rendered
