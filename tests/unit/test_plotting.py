"""Scan plotting: fidelity, both axis modes, labelling and error handling.

No pyplot, no backend, no display: figures are built directly so these tests run
headless.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from openauc.exceptions import PlottingError
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    ScanMetadata,
    Unit,
)
from openauc.plotting import DEFAULT_COLORMAP, plot_scan, plot_scans


def _scan(scan_id: str, index: int, *, elapsed: float | None = None) -> ScanMetadata:
    return ScanMetadata(
        scan_id=scan_id,
        index=index,
        elapsed_time=(
            Quantity.of(elapsed, Unit.SECOND)
            if elapsed is not None
            else Quantity.missing()
        ),
        optical_system=OpticalSystem.ABSORBANCE,
    )


def _shared_experiment(*, signal_unit: Unit = Unit.ABSORBANCE_UNIT) -> AUCExperiment:
    return AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="exp-1", name="Shared"),
        scans=(_scan("a", 0, elapsed=0.0), _scan("b", 1, elapsed=600.0)),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1, 6.2],
            signal=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            scan_ids=["a", "b"],
            signal_unit=signal_unit,
        ),
    )


def _per_scan_experiment() -> AUCExperiment:
    return AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="exp-2"),
        scans=(_scan("a", 0), _scan("b", 1), _scan("c", 2)),
        observations=Observations.from_per_scan(
            radii=[[6.0, 6.1, 6.2], [6.0, 6.05], []],
            signals=[[0.1, 0.2, 0.3], [0.4, 0.5], []],
            scan_ids=["a", "b", "c"],
            signal_unit=Unit.FRINGE,
        ),
    )


# --------------------------------------------------------------------------- #
# Data fidelity — the load-bearing property
# --------------------------------------------------------------------------- #


def test_plotted_data_matches_the_stored_vectors_exactly() -> None:
    experiment = _shared_experiment()
    axes = plot_scans(experiment)
    assert len(axes.lines) == 2
    for line, scan_id in zip(axes.lines, ["a", "b"], strict=True):
        radius, signal = experiment.observations.scan_vectors(scan_id)
        assert np.array_equal(line.get_xdata(), radius)
        assert np.array_equal(line.get_ydata(), signal)


def test_per_scan_axes_are_never_placed_on_a_common_grid() -> None:
    """Ragged scans keep their own radius vectors; nothing is interpolated."""
    experiment = _per_scan_experiment()
    axes = plot_scans(experiment)
    # Scan "c" carries no observations and is skipped.
    assert [line.get_label() for line in axes.lines] == ["a", "b"]
    assert list(axes.lines[0].get_xdata()) == [6.0, 6.1, 6.2]
    assert list(axes.lines[1].get_xdata()) == [6.0, 6.05]
    # Differing lengths survive: no resampling onto a shared axis.
    assert len(axes.lines[0].get_xdata()) != len(axes.lines[1].get_xdata())


def test_stored_order_is_preserved_and_never_sorted() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="descending"),
        scans=(_scan("a", 0),),
        observations=Observations.from_shared_axis(
            radius=[6.2, 6.0, 6.1],
            signal=[[0.3, 0.1, 0.2]],
            scan_ids=["a"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    line = plot_scans(experiment).lines[0]
    assert list(line.get_xdata()) == [6.2, 6.0, 6.1]
    assert list(line.get_ydata()) == [0.3, 0.1, 0.2]


# --------------------------------------------------------------------------- #
# Figure construction — no pyplot, no backend
# --------------------------------------------------------------------------- #


def test_a_standalone_figure_is_created_without_pyplot() -> None:
    axes = plot_scans(_shared_experiment())
    assert isinstance(axes, Axes)
    assert isinstance(axes.figure, Figure)
    # pyplot must not have been used, so no figure is registered globally.
    import sys

    if "matplotlib.pyplot" in sys.modules:
        import matplotlib.pyplot as plt

        assert plt.get_fignums() == []


def test_supplied_axes_are_reused_and_accumulate_lines() -> None:
    figure = Figure()
    axes = figure.add_subplot(111)
    returned = plot_scans(_shared_experiment(), ax=axes)
    assert returned is axes
    plot_scans(_per_scan_experiment(), ax=axes)
    assert len(axes.lines) == 4


def test_figure_can_be_saved_headless(tmp_path: Path) -> None:
    axes = plot_scans(_shared_experiment())
    figure = axes.figure
    assert isinstance(figure, Figure)
    target = tmp_path / "scans.png"
    figure.savefig(target)
    assert target.stat().st_size > 0


# --------------------------------------------------------------------------- #
# Labelling — declared units reported verbatim
# --------------------------------------------------------------------------- #


def test_axis_labels_report_declared_units() -> None:
    axes = plot_scans(_shared_experiment())
    assert axes.get_xlabel() == "radius (cm)"
    assert axes.get_ylabel() == "signal (AU)"


def test_undeclared_signal_unit_is_labelled_as_undeclared() -> None:
    axes = plot_scans(_shared_experiment(signal_unit=Unit.UNKNOWN))
    assert axes.get_ylabel() == "signal (unit not declared)"
    assert "unknown" not in axes.get_ylabel()


def test_title_defaults_to_identity_and_can_be_overridden() -> None:
    assert plot_scans(_shared_experiment()).get_title() == "exp-1 - Shared"
    assert plot_scans(_per_scan_experiment()).get_title() == "exp-2"
    assert plot_scans(_shared_experiment(), title="Custom").get_title() == "Custom"


def _legend_labels(axes: Axes) -> list[str]:
    legend = axes.get_legend()
    assert legend is not None, "expected a legend to have been drawn"
    return [text.get_text() for text in legend.get_texts()]


def test_legend_labels_include_elapsed_time_when_present() -> None:
    assert _legend_labels(plot_scans(_shared_experiment())) == [
        "a (t = 0 s)",
        "b (t = 600 s)",
    ]


def test_absent_elapsed_time_falls_back_to_the_scan_id() -> None:
    assert _legend_labels(plot_scans(_per_scan_experiment())) == ["a", "b"]


def test_elapsed_labelling_can_be_disabled_and_legend_suppressed() -> None:
    axes = plot_scans(_shared_experiment(), label_elapsed=False)
    assert [line.get_label() for line in axes.lines] == ["a", "b"]
    assert plot_scans(_shared_experiment(), legend=False).get_legend() is None


def test_scan_without_metadata_still_plots_with_its_identifier() -> None:
    """Plotting is an inspection tool; broken correspondence must not stop it."""
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="mismatch"),
        scans=(_scan("a", 0, elapsed=0.0),),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1],
            signal=[[0.1, 0.2], [0.3, 0.4]],
            scan_ids=["a", "orphan"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    assert not experiment.validate_structure().is_valid  # count mismatch
    axes = plot_scans(experiment)
    assert [line.get_label() for line in axes.lines] == ["a (t = 0 s)", "orphan"]


# --------------------------------------------------------------------------- #
# Selection, colouring and the single-scan helper
# --------------------------------------------------------------------------- #


def test_selection_restricts_and_orders_the_plotted_scans() -> None:
    axes = plot_scans(_shared_experiment(), scan_ids=["b", "a"])
    assert [line.get_label() for line in axes.lines] == ["b (t = 600 s)", "a (t = 0 s)"]


def test_unknown_requested_scan_raises() -> None:
    with pytest.raises(PlottingError, match="no observations for scan id"):
        plot_scans(_shared_experiment(), scan_ids=["a", "nope"])


def test_experiment_with_nothing_to_draw_raises() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="empty"),
        scans=(_scan("a", 0),),
        observations=Observations.from_per_scan(
            radii=[[]], signals=[[]], scan_ids=["a"]
        ),
    )
    with pytest.raises(PlottingError, match="carries any observation"):
        plot_scans(experiment)


def test_scans_are_coloured_distinctly_by_order() -> None:
    axes = plot_scans(_shared_experiment())
    colours = [line.get_color() for line in axes.lines]
    assert colours[0] != colours[1]
    single = plot_scans(_shared_experiment(), scan_ids=["a"])
    assert len(single.lines) == 1


def test_colormap_is_configurable() -> None:
    default = plot_scans(_shared_experiment()).lines[0].get_color()
    other = plot_scans(_shared_experiment(), colormap="plasma").lines[0].get_color()
    assert default != other
    assert DEFAULT_COLORMAP == "viridis"


def test_line_style_options_are_applied() -> None:
    axes = plot_scans(_shared_experiment(), linewidth=2.5, marker="o")
    assert axes.lines[0].get_linewidth() == 2.5
    assert axes.lines[0].get_marker() == "o"


def test_plot_scan_draws_exactly_one_scan() -> None:
    axes = plot_scan(_shared_experiment(), "b")
    assert len(axes.lines) == 1
    assert axes.lines[0].get_label() == "b (t = 600 s)"
    assert axes.get_legend() is None
    radius, signal = _shared_experiment().observations.scan_vectors("b")
    assert np.array_equal(axes.lines[0].get_xdata(), radius)
    assert np.array_equal(axes.lines[0].get_ydata(), signal)


def test_plot_scan_rejects_an_unknown_scan() -> None:
    with pytest.raises(PlottingError):
        plot_scan(_shared_experiment(), "zz")


# --------------------------------------------------------------------------- #
# No scientific claim
# --------------------------------------------------------------------------- #


def test_plot_adds_no_derived_or_interpreted_content() -> None:
    """Only the measured series are drawn: no fit, baseline or annotation."""
    experiment = _shared_experiment()
    axes = plot_scans(experiment)
    assert len(axes.lines) == len(experiment.scans)
    assert len(axes.texts) == 0
    assert len(axes.patches) == 0
    assert len(axes.collections) == 0
    for line in axes.lines:
        assert len(line.get_xdata()) == 3  # exactly the stored points, no resampling


# --------------------------------------------------------------------------- #
# Lazy public re-export — plotting must not weigh down the facade
# --------------------------------------------------------------------------- #


def test_api_reexports_the_same_plotting_callables() -> None:
    import openauc.api as api
    import openauc.plotting as plotting

    assert api.plot_scans is plotting.plot_scans
    assert api.plot_scan is plotting.plot_scan
    assert "plot_scans" in api.__all__
    assert "plot_scans" in dir(api)


def test_api_still_rejects_unknown_attributes() -> None:
    import openauc.api as api

    with pytest.raises(AttributeError, match="has no attribute 'nope'"):
        _ = api.nope


def test_importing_the_library_does_not_import_matplotlib() -> None:
    """Ingestion, validation and summaries must not pay matplotlib's cost."""
    import subprocess
    import sys

    probe = "import sys, openauc, openauc.api;print('matplotlib' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "False"
