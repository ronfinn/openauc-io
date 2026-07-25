"""Plotting over experiments imported with openauc.load (synthetic fixtures)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import openauc
from openauc.models import AUCExperiment, RadiusAxisMode
from openauc.plotting import plot_scan, plot_scans

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "generic_delimited"


def _load(name: str) -> AUCExperiment:
    return openauc.load(FIXTURES / name)


@pytest.mark.parametrize("fixture", ["long_csv", "wide_csv", "long_tsv", "wide_tsv"])
def test_imported_experiments_plot_every_scan(fixture: str) -> None:
    experiment = _load(fixture)
    axes = plot_scans(experiment)
    assert len(axes.lines) == len(experiment.scans)
    assert axes.get_xlabel() == "radius (cm)"
    assert axes.get_ylabel() == "signal (AU)"
    assert experiment.metadata.experiment_id in axes.get_title()


@pytest.mark.parametrize("fixture", ["long_csv", "wide_csv", "per_scan"])
def test_plotted_values_equal_the_imported_observations(fixture: str) -> None:
    experiment = _load(fixture)
    axes = plot_scans(experiment)
    plotted = {str(line.get_label()).split(" (")[0]: line for line in axes.lines}
    for scan_id, line in plotted.items():
        radius, signal = experiment.observations.scan_vectors(scan_id)
        assert np.array_equal(line.get_xdata(), radius)
        assert np.array_equal(line.get_ydata(), signal)


def test_ragged_import_keeps_per_scan_axes_distinct() -> None:
    experiment = _load("per_scan")
    assert experiment.observations.mode is RadiusAxisMode.PER_SCAN
    axes = plot_scans(experiment)
    lengths = {len(line.get_xdata()) for line in axes.lines}
    # The fixture's scans differ in length; plotting must not equalise them.
    assert lengths == {2, 3}
    x_sets = [tuple(line.get_xdata()) for line in axes.lines]
    assert x_sets[0] != x_sets[1]


def test_single_scan_plot_from_an_import() -> None:
    experiment = _load("readiness_rich")
    scan_id = experiment.scans[1].scan_id
    axes = plot_scan(experiment, scan_id)
    assert len(axes.lines) == 1
    radius, signal = experiment.observations.scan_vectors(scan_id)
    assert np.array_equal(axes.lines[0].get_xdata(), radius)
    assert np.array_equal(axes.lines[0].get_ydata(), signal)


def test_plotting_is_deterministic_across_reloads() -> None:
    first = plot_scans(_load("long_csv"))
    second = plot_scans(_load("long_csv"))
    assert [str(line.get_label()) for line in first.lines] == [
        str(line.get_label()) for line in second.lines
    ]
    for a, b in zip(first.lines, second.lines, strict=True):
        assert np.array_equal(a.get_xdata(), b.get_xdata())
        assert np.array_equal(a.get_ydata(), b.get_ydata())
        assert a.get_color() == b.get_color()


def test_plotting_does_not_mutate_the_experiment() -> None:
    experiment = _load("long_csv")
    before = experiment.to_dict()
    plot_scans(experiment)
    assert experiment.to_dict() == before
