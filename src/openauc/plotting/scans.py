"""Basic radial scan plots over the canonical model.

Two rules govern this module:

* **Nothing is interpolated, resampled or reordered.** Each scan is drawn from
  its own stored vectors, in stored order. In per-scan-axis mode every scan
  keeps its own radius axis; the scans are simply overlaid on shared display
  axes. No scan is ever placed onto another scan's grid — ADR-0002 requires any
  such regridding to be an explicit, opt-in, recorded transformation, and this
  module performs none.
* **A plot is a rendering, not an interpretation.** Axis labels report the
  declared units verbatim, an undeclared unit is labelled as undeclared, and
  nothing is fitted, smoothed, baseline-corrected or annotated with derived
  quantities.

``matplotlib.pyplot`` is deliberately **not** used. Figures are built from
:class:`matplotlib.figure.Figure` directly, so plotting needs no interactive
backend, works headless, and leaves no figures in pyplot's global registry.
Callers who want an interactive window simply pass their own ``ax``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from openauc.exceptions import PlottingError
from openauc.models.enums import Unit, ValueStatus

if TYPE_CHECKING:
    import numpy as np
    from matplotlib.axes import Axes
    from numpy.typing import NDArray

    from openauc.models.experiment import AUCExperiment
    from openauc.models.scan import ScanMetadata

__all__ = ["plot_scan", "plot_scans"]

#: Default sequential colormap. Perceptually uniform, so scan order reads as a
#: progression. This is a display choice only; it asserts nothing about the data.
DEFAULT_COLORMAP = "viridis"

_UNDECLARED = "unit not declared"


def _axis_label(quantity: str, unit: Unit) -> str:
    """``'radius (cm)'``, or an explicit statement that the unit is undeclared."""
    if unit is Unit.UNKNOWN:
        return f"{quantity} ({_UNDECLARED})"
    return f"{quantity} ({unit.value})"


def _scan_label(scan_id: str, scan: ScanMetadata | None, *, show_elapsed: bool) -> str:
    """Legend entry: the scan identifier, plus its elapsed time when present."""
    if not show_elapsed or scan is None:
        return scan_id
    elapsed = scan.elapsed_time
    if elapsed.status is not ValueStatus.PRESENT or elapsed.value is None:
        return scan_id
    unit = _UNDECLARED if elapsed.unit is Unit.UNKNOWN else elapsed.unit.value
    return f"{scan_id} (t = {elapsed.value:g} {unit})"


def _new_axes() -> Axes:
    """A fresh Axes on a standalone Figure, without touching pyplot."""
    from matplotlib.figure import Figure

    figure = Figure()
    return figure.add_subplot(111)


def _resolve_scan_ids(
    experiment: AUCExperiment, scan_ids: Sequence[str] | None
) -> tuple[str, ...]:
    """Validate the requested selection against the observations."""
    available = experiment.observations.scan_ids
    if scan_ids is None:
        return available
    requested = tuple(scan_ids)
    unknown = [scan_id for scan_id in requested if scan_id not in available]
    if unknown:
        raise PlottingError(
            f"no observations for scan id(s) {unknown}; available: {list(available)}"
        )
    return requested


def _metadata_by_id(experiment: AUCExperiment) -> dict[str, ScanMetadata]:
    """Scan metadata keyed by identifier.

    Built from the metadata records rather than assuming they correspond to the
    observations: an experiment whose correspondence is broken is still
    inspectable, and plotting is an inspection tool. Duplicate identifiers keep
    the first record, matching the order the model stores them in.
    """
    by_id: dict[str, ScanMetadata] = {}
    for scan in experiment.scans:
        by_id.setdefault(scan.scan_id, scan)
    return by_id


def _colours(count: int, colormap: str) -> list[tuple[float, float, float, float]]:
    from matplotlib import colormaps

    cmap = colormaps[colormap]
    if count == 1:
        return [cmap(0.5)]
    return [cmap(index / (count - 1)) for index in range(count)]


def plot_scans(
    experiment: AUCExperiment,
    *,
    ax: Axes | None = None,
    scan_ids: Sequence[str] | None = None,
    title: str | None = None,
    legend: bool = True,
    label_elapsed: bool = True,
    colormap: str = DEFAULT_COLORMAP,
    linewidth: float = 1.0,
    marker: str | None = None,
) -> Axes:
    """Overlay the radial scans of ``experiment`` on one set of axes.

    Each scan is drawn from its own stored ``(radius, signal)`` vectors, in
    stored order. Scans carrying no observations are skipped. Nothing is
    interpolated, resampled, sorted or smoothed.

    Args:
        experiment: The experiment to draw.
        ax: Axes to draw on. When omitted a new standalone figure is created
            (reachable as ``returned_axes.figure``); pyplot is never used.
        scan_ids: Restrict to these scans, in the order given. Defaults to every
            scan, in stored order.
        title: Axes title. Defaults to the experiment identifier and name.
        legend: Draw a legend when at least one scan was plotted.
        label_elapsed: Append each scan's elapsed time to its legend entry when
            the value is present.
        colormap: Named matplotlib colormap used to colour scans by their order.
        linewidth: Line width for each scan.
        marker: Optional matplotlib marker for individual observations.

    Returns:
        The axes drawn on.

    Raises:
        PlottingError: if a requested scan identifier is absent, or if no
            selected scan carries any observation to draw.
    """
    selected = _resolve_scan_ids(experiment, scan_ids)
    observations = experiment.observations
    by_id = _metadata_by_id(experiment)

    drawable: list[tuple[str, NDArray[np.float64], NDArray[np.float64]]] = []
    for scan_id in selected:
        radius, signal = observations.scan_vectors(scan_id)
        if radius.size:
            drawable.append((scan_id, radius, signal))

    if not drawable:
        raise PlottingError("no scan in the selection carries any observation to plot")

    axes = _new_axes() if ax is None else ax
    for colour, (scan_id, radius, signal) in zip(
        _colours(len(drawable), colormap), drawable, strict=True
    ):
        axes.plot(
            radius,
            signal,
            color=colour,
            linewidth=linewidth,
            marker=marker,
            label=_scan_label(scan_id, by_id.get(scan_id), show_elapsed=label_elapsed),
        )

    axes.set_xlabel(_axis_label("radius", observations.radius_unit))
    axes.set_ylabel(_axis_label("signal", observations.signal_unit))
    axes.set_title(title if title is not None else _default_title(experiment))
    if legend:
        axes.legend(loc="best", fontsize="small")
    return axes


def plot_scan(
    experiment: AUCExperiment,
    scan_id: str,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    legend: bool = False,
    label_elapsed: bool = True,
    colormap: str = DEFAULT_COLORMAP,
    linewidth: float = 1.0,
    marker: str | None = None,
) -> Axes:
    """Draw a single radial scan. See :func:`plot_scans` for the shared rules."""
    return plot_scans(
        experiment,
        ax=ax,
        scan_ids=(scan_id,),
        title=title,
        legend=legend,
        label_elapsed=label_elapsed,
        colormap=colormap,
        linewidth=linewidth,
        marker=marker,
    )


def _default_title(experiment: AUCExperiment) -> str:
    metadata = experiment.metadata
    if metadata.name:
        return f"{metadata.experiment_id} - {metadata.name}"
    return metadata.experiment_id
