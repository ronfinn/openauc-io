"""Observations: shared/per-scan axes, masks, non-finite values (3, 4, 9, 11, 12)."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from openauc.exceptions import ObservationError
from openauc.models import Observations, RadiusAxisMode, Unit


def test_shared_axis_mode() -> None:
    obs = Observations.from_shared_axis(
        radius=[6.0, 6.1, 6.2],
        signal=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        scan_ids=["a", "b"],
        signal_unit=Unit.ABSORBANCE_UNIT,
    )
    assert obs.mode is RadiusAxisMode.SHARED
    assert obs.n_scans == 2
    assert obs.scan_ids == ("a", "b")
    assert obs.radius_range() == (6.0, 6.2)
    assert obs.points_per_scan() == (3, 3)


def test_per_scan_axis_mode_pads_and_masks() -> None:
    obs = Observations.from_per_scan(
        radii=[[6.0, 6.1, 6.2], [6.0, 6.05]],
        signals=[[0.1, 0.2, 0.3], [0.4, 0.5]],
        scan_ids=["a", "b"],
        signal_unit=Unit.FRINGE,
    )
    assert obs.mode is RadiusAxisMode.PER_SCAN
    assert obs.n_scans == 2
    # Padding to a rectangle: second scan is shorter than the first.
    assert obs.points_per_scan() == (3, 2)
    mask = obs.dataset["mask"].to_numpy()
    assert mask.shape == (2, 3)
    assert mask[1].tolist() == [True, True, False]
    # The padded cell is NaN (never presented as a measured value).
    radius = obs.dataset["radius"].to_numpy()
    assert np.isnan(radius[1, 2])
    # valid_radius_values excludes padding.
    assert sorted(obs.valid_radius_values().tolist()) == [6.0, 6.0, 6.05, 6.1, 6.2]


def test_shared_axis_rejects_non_finite_signal() -> None:
    with pytest.raises(ObservationError, match="signal contains non-finite"):
        Observations.from_shared_axis(
            radius=[6.0, 6.1],
            signal=[[0.1, float("nan")]],
            scan_ids=["a"],
        )


def test_shared_axis_rejects_non_finite_radius() -> None:
    with pytest.raises(ObservationError, match="radius contains non-finite"):
        Observations.from_shared_axis(
            radius=[6.0, float("inf")],
            signal=[[0.1, 0.2]],
            scan_ids=["a"],
        )


def test_per_scan_rejects_non_finite() -> None:
    with pytest.raises(ObservationError, match="non-finite"):
        Observations.from_per_scan(
            radii=[[6.0, float("nan")]],
            signals=[[0.1, 0.2]],
            scan_ids=["a"],
        )


def test_shared_axis_rejects_length_mismatch() -> None:
    with pytest.raises(ObservationError, match="radius length must match"):
        Observations.from_shared_axis(
            radius=[6.0, 6.1, 6.2],
            signal=[[0.1, 0.2]],
            scan_ids=["a"],
        )


def test_per_scan_rejects_scan_length_mismatch() -> None:
    with pytest.raises(ObservationError, match="lengths differ"):
        Observations.from_per_scan(
            radii=[[6.0, 6.1, 6.2]],
            signals=[[0.1, 0.2]],
            scan_ids=["a"],
        )


def test_duplicate_scan_ids_in_observations_raise() -> None:
    with pytest.raises(ObservationError, match="duplicate scan_id"):
        Observations.from_shared_axis(
            radius=[6.0],
            signal=[[0.1], [0.2]],
            scan_ids=["a", "a"],
        )


def test_valid_hand_built_mask_dataset_is_accepted() -> None:
    dataset = xr.Dataset(
        data_vars={
            "radius": (("scan", "point"), np.array([[6.0, 6.1], [6.0, np.nan]])),
            "signal": (("scan", "point"), np.array([[0.1, 0.2], [0.3, np.nan]])),
            "mask": (("scan", "point"), np.array([[True, True], [True, False]])),
        },
        coords={"scan_id": ("scan", ["a", "b"])},
        attrs={
            "mode": RadiusAxisMode.PER_SCAN.value,
            "signal_unit": Unit.UNKNOWN.value,
            "radius_unit": Unit.CENTIMETRE.value,
        },
    )
    obs = Observations(dataset)
    assert obs.points_per_scan() == (2, 1)


def test_invalid_mask_marks_padding_as_valid() -> None:
    # mask says the NaN cell is a real observation: must be rejected.
    dataset = xr.Dataset(
        data_vars={
            "radius": (("scan", "point"), np.array([[6.0, np.nan]])),
            "signal": (("scan", "point"), np.array([[0.1, np.nan]])),
            "mask": (("scan", "point"), np.array([[True, True]])),
        },
        coords={"scan_id": ("scan", ["a"])},
        attrs={
            "mode": RadiusAxisMode.PER_SCAN.value,
            "signal_unit": Unit.UNKNOWN.value,
            "radius_unit": Unit.CENTIMETRE.value,
        },
    )
    with pytest.raises(ObservationError, match="masked-in"):
        Observations(dataset)


def test_invalid_mask_wrong_dtype() -> None:
    dataset = xr.Dataset(
        data_vars={
            "radius": (("scan", "point"), np.array([[6.0, 6.1]])),
            "signal": (("scan", "point"), np.array([[0.1, 0.2]])),
            "mask": (("scan", "point"), np.array([[1, 0]])),  # int, not bool
        },
        coords={"scan_id": ("scan", ["a"])},
        attrs={
            "mode": RadiusAxisMode.PER_SCAN.value,
            "signal_unit": Unit.UNKNOWN.value,
            "radius_unit": Unit.CENTIMETRE.value,
        },
    )
    with pytest.raises(ObservationError, match="mask must be a boolean array"):
        Observations(dataset)


def test_observations_roundtrip_shared() -> None:
    obs = Observations.from_shared_axis(
        radius=[6.0, 6.1], signal=[[0.1, 0.2]], scan_ids=["a"]
    )
    assert Observations.from_dict(obs.to_dict()) == obs


def test_observations_roundtrip_per_scan_preserves_ragged_lengths() -> None:
    obs = Observations.from_per_scan(
        radii=[[6.0, 6.1, 6.2], [6.0]],
        signals=[[0.1, 0.2, 0.3], [0.4]],
        scan_ids=["a", "b"],
    )
    restored = Observations.from_dict(obs.to_dict())
    assert restored == obs
    assert restored.points_per_scan() == (3, 1)
