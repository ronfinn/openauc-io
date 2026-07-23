"""Edge cases: defensive dataset validation and summary branches."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from openauc.exceptions import ObservationError
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    InstrumentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    RadiusAxisMode,
    ScanMetadata,
    Unit,
    ValueStatus,
)


def test_dataset_with_invalid_mode_attr_raises() -> None:
    dataset = xr.Dataset(
        data_vars={"signal": (("scan", "radius"), np.array([[0.1]]))},
        coords={"scan_id": ("scan", ["a"]), "radius": ("radius", [6.0])},
        attrs={"mode": "not-a-mode", "signal_unit": "AU", "radius_unit": "cm"},
    )
    with pytest.raises(ObservationError, match="missing or invalid mode"):
        Observations(dataset)


def test_dataset_missing_scan_id_coord_raises() -> None:
    dataset = xr.Dataset(
        data_vars={"signal": (("scan", "radius"), np.array([[0.1]]))},
        coords={"radius": ("radius", [6.0])},
        attrs={
            "mode": RadiusAxisMode.SHARED.value,
            "signal_unit": "AU",
            "radius_unit": "cm",
        },
    )
    with pytest.raises(ObservationError, match="scan_id"):
        Observations(dataset)


def test_shared_dataset_missing_radius_coord_raises() -> None:
    dataset = xr.Dataset(
        data_vars={"signal": (("scan", "radius"), np.array([[0.1]]))},
        coords={"scan_id": ("scan", ["a"])},
        attrs={
            "mode": RadiusAxisMode.SHARED.value,
            "signal_unit": "AU",
            "radius_unit": "cm",
        },
    )
    with pytest.raises(ObservationError, match="radius"):
        Observations(dataset)


def test_per_scan_dataset_missing_variable_raises() -> None:
    dataset = xr.Dataset(
        data_vars={
            "radius": (("scan", "point"), np.array([[6.0]])),
            "signal": (("scan", "point"), np.array([[0.1]])),
        },
        coords={"scan_id": ("scan", ["a"])},
        attrs={
            "mode": RadiusAxisMode.PER_SCAN.value,
            "signal_unit": "AU",
            "radius_unit": "cm",
        },
    )
    with pytest.raises(ObservationError, match="mask"):
        Observations(dataset)


def test_observations_repr() -> None:
    obs = Observations.from_shared_axis(
        radius=[6.0], signal=[[0.1]], scan_ids=["a"], signal_unit=Unit.ABSORBANCE_UNIT
    )
    text = repr(obs)
    assert "Observations(" in text
    assert "shared" in text


def test_summary_handles_empty_observations_and_unknown_time() -> None:
    # A per-scan experiment with a single empty scan: no radius range, and an
    # UNKNOWN elapsed time so the summary reports 'unknown'.
    scan = ScanMetadata(
        scan_id="a",
        index=0,
        elapsed_time=Quantity(value=None, status=ValueStatus.UNKNOWN),
        optical_system=OpticalSystem.UNKNOWN,
    )
    observations = Observations.from_per_scan(radii=[[]], signals=[[]], scan_ids=["a"])
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(scan,),
        observations=observations,
        instrument=InstrumentMetadata(optical_system=OpticalSystem.INTERFERENCE),
    )
    summary = experiment.summary()
    assert "Radius range: n/a" in summary
    assert "Elapsed time: unknown" in summary
    # Instrument optical system participates in the distinct-systems set.
    assert "interference" in summary
    assert "Provenance: not recorded" in summary
