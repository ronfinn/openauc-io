"""Observations.scan_vectors / iter_scan_vectors: exact, masked, unordered-safe."""

from __future__ import annotations

import numpy as np
import pytest

from openauc.models import Observations, Unit


def _shared() -> Observations:
    return Observations.from_shared_axis(
        radius=[6.0, 6.1, 6.2],
        signal=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        scan_ids=["a", "b"],
        signal_unit=Unit.ABSORBANCE_UNIT,
    )


def _per_scan() -> Observations:
    return Observations.from_per_scan(
        radii=[[6.0, 6.1, 6.2], [6.0, 6.05], []],
        signals=[[0.1, 0.2, 0.3], [0.4, 0.5], []],
        scan_ids=["a", "b", "c"],
        signal_unit=Unit.FRINGE,
    )


def test_shared_axis_returns_the_shared_radius_for_each_scan() -> None:
    obs = _shared()
    r_a, s_a = obs.scan_vectors("a")
    r_b, s_b = obs.scan_vectors("b")
    assert np.array_equal(r_a, [6.0, 6.1, 6.2])
    assert np.array_equal(r_b, [6.0, 6.1, 6.2])
    assert np.array_equal(s_a, [0.1, 0.2, 0.3])
    assert np.array_equal(s_b, [0.4, 0.5, 0.6])


def test_per_scan_returns_each_scans_own_axis_with_padding_removed() -> None:
    obs = _per_scan()
    r_a, s_a = obs.scan_vectors("a")
    r_b, s_b = obs.scan_vectors("b")
    r_c, s_c = obs.scan_vectors("c")
    assert (r_a.size, r_b.size, r_c.size) == (3, 2, 0)
    assert np.array_equal(r_b, [6.0, 6.05])
    assert np.array_equal(s_b, [0.4, 0.5])
    # Padding is excluded entirely; no NaN leaks out.
    for vector in (r_a, s_a, r_b, s_b, r_c, s_c):
        assert np.all(np.isfinite(vector))
    assert r_c.size == 0 and s_c.size == 0


def test_stored_order_is_never_sorted() -> None:
    """A descending or unordered axis is returned exactly as stored."""
    obs = Observations.from_shared_axis(
        radius=[6.2, 6.0, 6.1],
        signal=[[0.3, 0.1, 0.2]],
        scan_ids=["a"],
    )
    radius, signal = obs.scan_vectors("a")
    assert list(radius) == [6.2, 6.0, 6.1]
    assert list(signal) == [0.3, 0.1, 0.2]


def test_vectors_are_float_arrays_of_equal_length() -> None:
    for obs in (_shared(), _per_scan()):
        for scan_id in obs.scan_ids:
            radius, signal = obs.scan_vectors(scan_id)
            assert radius.dtype == np.float64
            assert signal.dtype == np.float64
            assert radius.shape == signal.shape


def test_unknown_scan_id_raises_key_error() -> None:
    with pytest.raises(KeyError, match="no scan with id 'zz'"):
        _shared().scan_vectors("zz")


def test_iter_scan_vectors_yields_every_scan_in_stored_order() -> None:
    obs = _per_scan()
    yielded = list(obs.iter_scan_vectors())
    assert [scan_id for scan_id, _, _ in yielded] == list(obs.scan_ids)
    assert [radius.size for _, radius, _ in yielded] == list(obs.points_per_scan())


def test_vector_lengths_agree_with_points_per_scan() -> None:
    for obs in (_shared(), _per_scan()):
        sizes = tuple(obs.scan_vectors(s)[0].size for s in obs.scan_ids)
        assert sizes == obs.points_per_scan()


def test_source_checksum_validates_its_digest_and_fields() -> None:
    import pytest as _pytest
    from pydantic import ValidationError

    from openauc.models import ImportProvenance, SourceChecksum

    good = SourceChecksum(role="data_file", filename="a.csv", value="A" * 64)
    assert good.value == "a" * 64  # normalised to lowercase

    with _pytest.raises(ValidationError, match="64 hexadecimal"):
        SourceChecksum(role="data_file", filename="a.csv", value="short")
    with _pytest.raises(ValidationError, match="non-empty"):
        SourceChecksum(role="  ", filename="a.csv", value="a" * 64)
    with _pytest.raises(ValidationError, match="64 hexadecimal"):
        ImportProvenance(sha256="not-a-digest")
