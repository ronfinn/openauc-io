"""AUCX archives: round-trips, determinism, integrity and rejection paths.

Every archive here is built by the library or hand-crafted in the test from
synthetic data; no external or real instrument data is involved.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

import openauc
from openauc.exceptions import (
    ArchiveError,
    ArchiveIntegrityError,
    ArchiveVersionError,
)
from openauc.formats.aucx import (
    AUCX_FORMAT_VERSION,
    CHECKSUM_MEMBER,
    EXPERIMENT_MEMBER,
    MANIFEST_MEMBER,
    MASK_MEMBER,
    PROVENANCE_MEMBER,
    RADIUS_MEMBER,
    SIGNAL_MEMBER,
    export_aucx,
    inspect_aucx,
    read_aucx,
    validate_aucx,
)
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    ExperimentType,
    ImportProvenance,
    InstrumentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    RadiusAxisMode,
    SampleMetadata,
    ScanMetadata,
    SourceChecksum,
    Unit,
)

FIXED_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _scan(scan_id: str, index: int, *, elapsed: float | None = None) -> ScanMetadata:
    return ScanMetadata(
        scan_id=scan_id,
        index=index,
        elapsed_time=(
            Quantity.of(elapsed, Unit.SECOND)
            if elapsed is not None
            else Quantity.missing()
        ),
        cell="1",
        channel="A",
        wavelength=Quantity.of(280.0, Unit.NANOMETRE),
        optical_system=OpticalSystem.ABSORBANCE,
        rotor_speed=Quantity.of(45000.0, Unit.RPM),
        temperature=Quantity.unknown(),
    )


def _shared_experiment() -> AUCExperiment:
    return AUCExperiment(
        metadata=ExperimentMetadata(
            experiment_id="exp-shared",
            name="Shared axis",
            experiment_type=ExperimentType.SEDIMENTATION_VELOCITY,
            operator="synthetic",
        ),
        scans=(_scan("a", 0, elapsed=0.0), _scan("b", 1, elapsed=600.0)),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1, 6.2],
            signal=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
        samples=(
            SampleMetadata(
                sample_id="s1",
                buffer_description="synthetic buffer",
                density=Quantity.of(1.0, Unit.OTHER, unit_label="g/mL"),
                partial_specific_volume=Quantity.not_applicable(),
            ),
        ),
        instrument=InstrumentMetadata(
            manufacturer="synthetic", optical_system=OpticalSystem.ABSORBANCE
        ),
        provenance=ImportProvenance(
            source_filename="scans.csv",
            sha256="a" * 64,
            source_checksums=(
                SourceChecksum(
                    role="data_file", filename="scans.csv", value="a" * 64, byte_size=12
                ),
                SourceChecksum(
                    role="manifest",
                    filename="manifest.json",
                    value="b" * 64,
                    byte_size=34,
                ),
            ),
            parser_name="generic-long",
            assumptions=("unit interpretation",),
        ),
    )


def _per_scan_experiment() -> AUCExperiment:
    return AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="exp-ragged"),
        scans=(_scan("a", 0, elapsed=0.0), _scan("b", 1), _scan("c", 2)),
        observations=Observations.from_per_scan(
            radii=[[6.0, 6.1, 6.2], [6.0, 6.05], []],
            signals=[[0.1, 0.2, 0.3], [0.4, 0.5], []],
            scan_ids=["a", "b", "c"],
            signal_unit=Unit.FRINGE,
        ),
    )


def _export(experiment: AUCExperiment, tmp_path: Path, name: str = "e.aucx") -> Path:
    return export_aucx(experiment, tmp_path / name, exported_at=FIXED_TIME)


def _rebuild(source: Path, target: Path, members: dict[str, bytes | None]) -> Path:
    """Rewrite an archive with ``members`` replacing or removing entries."""
    with zipfile.ZipFile(source) as original:
        existing = {name: original.read(name) for name in original.namelist()}
    existing.update({k: v for k, v in members.items() if v is not None})
    for key, value in members.items():
        if value is None:
            existing.pop(key, None)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as rebuilt:
        for name, payload in existing.items():
            rebuilt.writestr(name, payload)
    return target


# --------------------------------------------------------------------------- #
# Round-trips
# --------------------------------------------------------------------------- #


def test_shared_radius_round_trip(tmp_path: Path) -> None:
    original = _shared_experiment()
    restored = read_aucx(_export(original, tmp_path))
    assert restored.to_dict() == original.to_dict()
    assert restored.observations.mode is RadiusAxisMode.SHARED
    assert restored.observations.scan_ids == ("a", "b")


def test_per_scan_radius_round_trip(tmp_path: Path) -> None:
    original = _per_scan_experiment()
    restored = read_aucx(_export(original, tmp_path))
    assert restored.to_dict() == original.to_dict()
    assert restored.observations.mode is RadiusAxisMode.PER_SCAN
    assert restored.observations.points_per_scan() == (3, 2, 0)
    for scan_id in original.observations.scan_ids:
        before = original.observations.scan_vectors(scan_id)
        after = restored.observations.scan_vectors(scan_id)
        assert np.array_equal(before[0], after[0])
        assert np.array_equal(before[1], after[1])


def test_metadata_units_and_statuses_are_preserved(tmp_path: Path) -> None:
    original = _shared_experiment()
    restored = read_aucx(_export(original, tmp_path))
    assert restored.metadata == original.metadata
    assert restored.instrument == original.instrument
    assert restored.samples == original.samples
    assert restored.scans == original.scans
    # The three kinds of absence survive distinctly.
    assert restored.scans[0].temperature is not None
    assert restored.scans[0].temperature.status.value == "unknown"
    assert restored.scans[1].elapsed_time.status.value == "present"
    assert restored.samples[0].partial_specific_volume is not None
    assert restored.samples[0].partial_specific_volume.status.value == "not_applicable"
    assert restored.samples[0].viscosity is None
    assert restored.observations.signal_unit is Unit.ABSORBANCE_UNIT
    assert restored.observations.radius_unit is Unit.CENTIMETRE


def test_provenance_and_source_checksums_are_preserved(tmp_path: Path) -> None:
    original = _shared_experiment()
    restored = read_aucx(_export(original, tmp_path))
    assert restored.provenance == original.provenance
    assert restored.provenance is not None
    roles = {c.role for c in restored.provenance.source_checksums}
    assert roles == {"data_file", "manifest"}


def test_dtype_and_shape_are_preserved(tmp_path: Path) -> None:
    original = _per_scan_experiment()
    path = _export(original, tmp_path)
    with zipfile.ZipFile(path) as archive:
        radius = np.load(io.BytesIO(archive.read(RADIUS_MEMBER)), allow_pickle=False)
        mask = np.load(io.BytesIO(archive.read(MASK_MEMBER)), allow_pickle=False)
    assert radius.dtype == np.float64
    assert mask.dtype == np.bool_
    assert radius.ndim == 2
    assert mask.shape == radius.shape


def test_empty_and_fully_masked_scans_round_trip(tmp_path: Path) -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="empty-scans"),
        scans=(_scan("a", 0), _scan("b", 1)),
        observations=Observations.from_per_scan(
            radii=[[], []], signals=[[], []], scan_ids=["a", "b"]
        ),
    )
    restored = read_aucx(_export(experiment, tmp_path))
    assert restored.to_dict() == experiment.to_dict()
    assert restored.observations.points_per_scan() == (0, 0)


def test_restored_experiment_supports_the_full_model_api(tmp_path: Path) -> None:
    restored = read_aucx(_export(_shared_experiment(), tmp_path))
    assert restored.validate_structure().is_valid
    assert restored.validate().is_valid
    assert restored.assess_readiness().scientific_suitability.status.value == (
        "not_assessed"
    )
    assert restored.summary_data().n_scans == 2
    assert "no assessment of scientific validity" in restored.summary().lower()


# --------------------------------------------------------------------------- #
# Determinism, overwrite and atomicity
# --------------------------------------------------------------------------- #


def test_export_is_byte_identical_for_equivalent_experiments(tmp_path: Path) -> None:
    first = export_aucx(
        _shared_experiment(), tmp_path / "a.aucx", exported_at=FIXED_TIME
    )
    second = export_aucx(
        _shared_experiment(), tmp_path / "b.aucx", exported_at=FIXED_TIME
    )
    assert first.read_bytes() == second.read_bytes()


def test_zip_metadata_is_normalised(tmp_path: Path) -> None:
    with zipfile.ZipFile(_export(_shared_experiment(), tmp_path)) as archive:
        infos = archive.infolist()
    assert [i.filename for i in infos] == [
        MANIFEST_MEMBER,
        EXPERIMENT_MEMBER,
        PROVENANCE_MEMBER,
        RADIUS_MEMBER,
        SIGNAL_MEMBER,
        MASK_MEMBER,
        CHECKSUM_MEMBER,
    ]
    for info in infos:
        assert info.date_time == (1980, 1, 1, 0, 0, 0)
        assert info.external_attr == 0o644 << 16
        assert info.create_system == 0
        assert info.compress_type == zipfile.ZIP_DEFLATED


def test_a_different_export_time_changes_only_the_timestamped_parts(
    tmp_path: Path,
) -> None:
    first = _export(_shared_experiment(), tmp_path, "a.aucx")
    second = export_aucx(
        _shared_experiment(),
        tmp_path / "b.aucx",
        exported_at=datetime(2027, 6, 1, tzinfo=UTC),
    )
    assert first.read_bytes() != second.read_bytes()
    with zipfile.ZipFile(first) as a, zipfile.ZipFile(second) as b:
        assert a.read(EXPERIMENT_MEMBER) == b.read(EXPERIMENT_MEMBER)
        assert a.read(SIGNAL_MEMBER) == b.read(SIGNAL_MEMBER)
        assert a.read(MANIFEST_MEMBER) != b.read(MANIFEST_MEMBER)


def test_export_refuses_to_overwrite_by_default(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    before = path.read_bytes()
    with pytest.raises(ArchiveError, match="refusing to overwrite"):
        export_aucx(_shared_experiment(), path, exported_at=FIXED_TIME)
    assert path.read_bytes() == before


def test_export_overwrites_when_asked(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    replacement = export_aucx(
        _per_scan_experiment(), path, overwrite=True, exported_at=FIXED_TIME
    )
    assert replacement == path
    assert read_aucx(path).metadata.experiment_id == "exp-ragged"


def test_a_failed_export_leaves_no_temporary_file(tmp_path: Path) -> None:
    target = tmp_path / "broken.aucx"
    with pytest.raises(ArchiveError):
        export_aucx(_shared_experiment(), target / "nested" / "x.aucx")
    assert list(tmp_path.glob(".aucx-*")) == []
    assert not target.exists()


def test_export_to_a_missing_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError, match="destination directory does not exist"):
        export_aucx(_shared_experiment(), tmp_path / "absent" / "x.aucx")


# --------------------------------------------------------------------------- #
# Inspection and validation
# --------------------------------------------------------------------------- #


def test_inspect_reports_declared_facts(tmp_path: Path) -> None:
    info = inspect_aucx(_export(_shared_experiment(), tmp_path))
    assert info.aucx_format_version == AUCX_FORMAT_VERSION
    assert info.checksum_verified
    assert info.radius_axis_mode is RadiusAxisMode.SHARED
    assert info.n_scans == 2
    assert info.n_points == 3
    assert info.scan_ids == ("a", "b")
    assert info.signal_unit is Unit.ABSORBANCE_UNIT
    assert info.experiment_id == "exp-shared"
    assert info.export.exported_at == FIXED_TIME
    assert info.export.software == "openauc"
    assert info.export.software_version == openauc.__version__
    assert CHECKSUM_MEMBER in info.members
    assert json.loads(json.dumps(info.to_dict()))["n_scans"] == 2


def test_validate_reports_a_good_archive_without_raising(tmp_path: Path) -> None:
    report = validate_aucx(_export(_shared_experiment(), tmp_path))
    assert report.is_valid
    assert report.issues == ()
    assert report.info is not None
    assert "OK" in str(report)
    assert json.loads(json.dumps(report.to_dict()))["is_valid"] is True


def test_validate_reports_problems_instead_of_raising(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "broken.aucx", {EXPERIMENT_MEMBER: b"{ nope"})
    report = validate_aucx(broken)
    assert not report.is_valid
    assert report.issues[0].code == "checksum_verification_failed"
    assert "FAILED" in str(report)


# --------------------------------------------------------------------------- #
# Integrity and rejection paths
# --------------------------------------------------------------------------- #


def test_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    with zipfile.ZipFile(path) as archive:
        experiment_bytes = archive.read(EXPERIMENT_MEMBER)
    tampered = experiment_bytes.replace(b"exp-shared", b"exp-forged")
    broken = _rebuild(path, tmp_path / "t.aucx", {EXPERIMENT_MEMBER: tampered})
    with pytest.raises(ArchiveIntegrityError, match="checksum mismatch"):
        read_aucx(broken)


def test_missing_checksum_file_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {CHECKSUM_MEMBER: None})
    with pytest.raises(ArchiveIntegrityError, match=r"no checksums\.sha256"):
        read_aucx(broken)


def test_missing_listed_member_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {SIGNAL_MEMBER: None})
    with pytest.raises(ArchiveIntegrityError, match="missing from the archive"):
        read_aucx(broken)


@pytest.mark.parametrize(
    "line",
    [
        b"not-a-checksum-line\n",
        b"deadbeef  manifest.json\n",
        b"z" * 64 + b"  manifest.json\n",
    ],
)
def test_malformed_checksum_entries_are_rejected(tmp_path: Path, line: bytes) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {CHECKSUM_MEMBER: line})
    with pytest.raises(ArchiveIntegrityError):
        read_aucx(broken)


def test_empty_checksum_file_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {CHECKSUM_MEMBER: b"\n"})
    with pytest.raises(ArchiveIntegrityError, match="lists no members"):
        read_aucx(broken)


def test_unlisted_extra_member_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {"extra.txt": b"surprise"})
    with pytest.raises(ArchiveIntegrityError, match="does not list"):
        read_aucx(broken)


@pytest.mark.filterwarnings("ignore:Duplicate name:UserWarning")
def test_duplicate_member_names_are_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    duplicated = tmp_path / "dup.aucx"
    with zipfile.ZipFile(path) as original:
        payloads = [(n, original.read(n)) for n in original.namelist()]
    with zipfile.ZipFile(duplicated, "w", zipfile.ZIP_DEFLATED) as rebuilt:
        for name, payload in payloads:
            rebuilt.writestr(name, payload)
        rebuilt.writestr(EXPERIMENT_MEMBER, b"{}")
    with pytest.raises(ArchiveError, match="duplicate member"):
        read_aucx(duplicated)


@pytest.mark.parametrize(
    "unsafe", ["/etc/passwd", "../escape.json", "sub\\dir.json", "nested/../../x.json"]
)
def test_unsafe_member_paths_are_rejected(tmp_path: Path, unsafe: str) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {unsafe: b"payload"})
    with pytest.raises(ArchiveError):
        read_aucx(broken)


def test_unsupported_format_version_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read(MANIFEST_MEMBER))
        checksums = archive.read(CHECKSUM_MEMBER).decode()
    manifest["aucx_format_version"] = "2.0"
    new_manifest = (
        json.dumps(manifest, sort_keys=True, indent=2, separators=(",", ": ")) + "\n"
    ).encode()
    digest = hashlib.sha256(new_manifest).hexdigest()
    lines = [
        f"{digest}  {MANIFEST_MEMBER}" if MANIFEST_MEMBER in line else line
        for line in checksums.splitlines()
    ]
    broken = _rebuild(
        path,
        tmp_path / "t.aucx",
        {
            MANIFEST_MEMBER: new_manifest,
            CHECKSUM_MEMBER: ("\n".join(lines) + "\n").encode(),
        },
    )
    with pytest.raises(ArchiveVersionError, match="unsupported AUCX format version"):
        read_aucx(broken)
    assert not validate_aucx(broken).is_valid


def test_corrupt_npy_payload_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    with zipfile.ZipFile(path) as archive:
        checksums = archive.read(CHECKSUM_MEMBER).decode()
    junk = b"not an npy file"
    digest = hashlib.sha256(junk).hexdigest()
    lines = [
        f"{digest}  {SIGNAL_MEMBER}" if SIGNAL_MEMBER in line else line
        for line in checksums.splitlines()
    ]
    broken = _rebuild(
        path,
        tmp_path / "t.aucx",
        {SIGNAL_MEMBER: junk, CHECKSUM_MEMBER: ("\n".join(lines) + "\n").encode()},
    )
    with pytest.raises(ArchiveError, match=r"not a readable \.npy array"):
        read_aucx(broken)


def _rechecksummed(source: Path, target: Path, replacements: dict[str, bytes]) -> Path:
    """Replace members and rewrite checksums so only the target check can fail."""
    with zipfile.ZipFile(source) as original:
        payloads = {n: original.read(n) for n in original.namelist()}
    payloads.update(replacements)
    lines = [
        f"{hashlib.sha256(payload).hexdigest()}  {name}"
        for name, payload in sorted(payloads.items())
        if name != CHECKSUM_MEMBER
    ]
    payloads[CHECKSUM_MEMBER] = ("\n".join(lines) + "\n").encode()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as rebuilt:
        for name, payload in payloads.items():
            rebuilt.writestr(name, payload)
    return target


def test_object_arrays_are_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    buffer = io.BytesIO()
    np.save(buffer, np.array([{"a": 1}], dtype=object), allow_pickle=True)
    broken = _rechecksummed(
        path, tmp_path / "t.aucx", {SIGNAL_MEMBER: buffer.getvalue()}
    )
    with pytest.raises(ArchiveError, match="pickled arrays are rejected"):
        read_aucx(broken)


def test_shape_mismatch_against_the_manifest_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    buffer = io.BytesIO()
    np.save(buffer, np.zeros((5, 9), dtype=np.float64), allow_pickle=False)
    broken = _rechecksummed(
        path, tmp_path / "t.aucx", {SIGNAL_MEMBER: buffer.getvalue()}
    )
    with pytest.raises(ArchiveError, match="declares signal shape"):
        read_aucx(broken)


def test_incorrect_mask_dtype_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read(MANIFEST_MEMBER))
    buffer = io.BytesIO()
    np.save(buffer, np.ones((2, 3), dtype=np.int8), allow_pickle=False)
    manifest["observations"]["arrays"]["mask"]["dtype"] = "int8"
    broken = _rechecksummed(
        path,
        tmp_path / "t.aucx",
        {
            MASK_MEMBER: buffer.getvalue(),
            MANIFEST_MEMBER: (
                json.dumps(manifest, sort_keys=True, indent=2, separators=(",", ": "))
                + "\n"
            ).encode(),
        },
    )
    with pytest.raises(ArchiveError, match="expected a boolean array"):
        read_aucx(broken)


def test_shared_archive_with_a_partial_mask_is_rejected(tmp_path: Path) -> None:
    """The canonical model cannot represent partial validity on a shared axis."""
    path = _export(_shared_experiment(), tmp_path)
    buffer = io.BytesIO()
    mask = np.ones((2, 3), dtype=np.bool_)
    mask[1, 2] = False
    np.save(buffer, mask, allow_pickle=False)
    broken = _rechecksummed(path, tmp_path / "t.aucx", {MASK_MEMBER: buffer.getvalue()})
    with pytest.raises(ArchiveError, match="all-true mask"):
        read_aucx(broken)


def test_corrupt_json_member_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rechecksummed(
        path, tmp_path / "t.aucx", {EXPERIMENT_MEMBER: b"{not json"}
    )
    with pytest.raises(ArchiveError, match="not valid JSON"):
        read_aucx(broken)


def test_manifest_omitting_a_required_part_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read(MANIFEST_MEMBER))
    manifest["parts"] = [p for p in manifest["parts"] if p != MASK_MEMBER]
    broken = _rechecksummed(
        path,
        tmp_path / "t.aucx",
        {
            MANIFEST_MEMBER: (
                json.dumps(manifest, sort_keys=True, indent=2, separators=(",", ": "))
                + "\n"
            ).encode()
        },
    )
    with pytest.raises(ArchiveError, match="omits required member"):
        read_aucx(broken)


def test_a_non_zip_file_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "fake.aucx"
    target.write_bytes(b"definitely not a zip")
    with pytest.raises(ArchiveError, match="not a readable ZIP archive"):
        read_aucx(target)
    assert not validate_aucx(target).is_valid


def test_a_missing_archive_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError, match="does not exist"):
        read_aucx(tmp_path / "absent.aucx")


def test_errors_name_the_archive_and_the_problem(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "named.aucx", {SIGNAL_MEMBER: b"tampered"})
    with pytest.raises(ArchiveIntegrityError) as caught:
        read_aucx(broken)
    message = str(caught.value)
    assert "named.aucx" in message
    assert SIGNAL_MEMBER in message
    assert "recorded" in message and "computed" in message


# --------------------------------------------------------------------------- #
# Remaining defensive paths
# --------------------------------------------------------------------------- #


def _manifest_bytes(manifest: dict[str, object]) -> bytes:
    return (
        json.dumps(manifest, sort_keys=True, indent=2, separators=(",", ": ")) + "\n"
    ).encode()


def _with_manifest(source: Path, target: Path, mutate: object) -> Path:
    with zipfile.ZipFile(source) as archive:
        manifest = json.loads(archive.read(MANIFEST_MEMBER))
    assert callable(mutate)
    mutate(manifest)
    return _rechecksummed(source, target, {MANIFEST_MEMBER: _manifest_bytes(manifest)})


def test_non_utf8_checksum_file_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {CHECKSUM_MEMBER: b"\xff\xfe\x00bad"})
    with pytest.raises(ArchiveIntegrityError, match="not valid UTF-8"):
        read_aucx(broken)


def test_checksum_file_omitting_the_manifest_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    with zipfile.ZipFile(path) as archive:
        lines = archive.read(CHECKSUM_MEMBER).decode().splitlines()
    kept = [line for line in lines if MANIFEST_MEMBER not in line]
    broken = _rebuild(
        path, tmp_path / "t.aucx", {CHECKSUM_MEMBER: ("\n".join(kept) + "\n").encode()}
    )
    with pytest.raises(ArchiveIntegrityError, match=r"does not list manifest\.json"):
        read_aucx(broken)


def test_a_directory_entry_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rebuild(path, tmp_path / "t.aucx", {"arrays/": b""})
    with pytest.raises(ArchiveError, match="unexpected directory entry"):
        read_aucx(broken)


def test_a_directory_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError, match="not a file"):
        read_aucx(tmp_path)


def test_an_empty_zip_is_rejected(tmp_path: Path) -> None:
    empty = tmp_path / "empty.aucx"
    with zipfile.ZipFile(empty, "w"):
        pass
    with pytest.raises(ArchiveError, match="contains no members"):
        read_aucx(empty)


def test_an_oversized_member_is_rejected_before_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import openauc.formats.aucx as aucx_module

    path = _export(_shared_experiment(), tmp_path)
    monkeypatch.setattr(aucx_module, "MAX_MEMBER_BYTES", 8)
    with pytest.raises(ArchiveError, match="above the 8-byte limit"):
        read_aucx(path)


def test_an_oversized_total_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import openauc.formats.aucx as aucx_module

    path = _export(_shared_experiment(), tmp_path)
    monkeypatch.setattr(aucx_module, "MAX_TOTAL_BYTES", 64)
    with pytest.raises(ArchiveError, match="uncompressed"):
        read_aucx(path)


def test_a_manifest_that_is_not_an_object_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rechecksummed(path, tmp_path / "t.aucx", {MANIFEST_MEMBER: b"[1, 2]\n"})
    with pytest.raises(ArchiveError, match="must contain a JSON object"):
        read_aucx(broken)


def test_a_manifest_without_a_version_is_rejected(tmp_path: Path) -> None:
    broken = _with_manifest(
        _export(_shared_experiment(), tmp_path),
        tmp_path / "t.aucx",
        lambda m: m.pop("aucx_format_version"),
    )
    with pytest.raises(ArchiveVersionError, match="does not declare"):
        read_aucx(broken)


def test_a_manifest_with_non_list_parts_is_rejected(tmp_path: Path) -> None:
    broken = _with_manifest(
        _export(_shared_experiment(), tmp_path),
        tmp_path / "t.aucx",
        lambda m: m.__setitem__("parts", "experiment.json"),
    )
    with pytest.raises(ArchiveError, match="must be a list of names"):
        read_aucx(broken)


def test_a_manifest_without_observations_is_rejected(tmp_path: Path) -> None:
    broken = _with_manifest(
        _export(_shared_experiment(), tmp_path),
        tmp_path / "t.aucx",
        lambda m: m.pop("observations"),
    )
    with pytest.raises(ArchiveError, match="no 'observations' block"):
        read_aucx(broken)


def test_a_manifest_missing_an_observations_key_is_rejected(tmp_path: Path) -> None:
    broken = _with_manifest(
        _export(_shared_experiment(), tmp_path),
        tmp_path / "t.aucx",
        lambda m: m["observations"].pop("radius_unit"),
    )
    with pytest.raises(ArchiveError, match="incomplete or invalid"):
        read_aucx(broken)


def test_a_scan_id_count_disagreement_is_rejected(tmp_path: Path) -> None:
    broken = _with_manifest(
        _export(_shared_experiment(), tmp_path),
        tmp_path / "t.aucx",
        lambda m: m["observations"].__setitem__("scan_ids", ["a"]),
    )
    with pytest.raises(ArchiveError, match="scan id"):
        read_aucx(broken)


def test_a_one_dimensional_signal_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    buffer = io.BytesIO()
    np.save(buffer, np.zeros(3, dtype=np.float64), allow_pickle=False)
    broken = _with_manifest(
        _rechecksummed(path, tmp_path / "s.aucx", {SIGNAL_MEMBER: buffer.getvalue()}),
        tmp_path / "t.aucx",
        lambda m: m["observations"]["arrays"]["signal"].__setitem__("shape", [3]),
    )
    with pytest.raises(ArchiveError, match="signal must be 2-D"):
        read_aucx(broken)


def test_a_two_dimensional_shared_radius_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    buffer = io.BytesIO()
    np.save(buffer, np.zeros((2, 3), dtype=np.float64), allow_pickle=False)
    broken = _with_manifest(
        _rechecksummed(path, tmp_path / "s.aucx", {RADIUS_MEMBER: buffer.getvalue()}),
        tmp_path / "t.aucx",
        lambda m: m["observations"]["arrays"]["radius"].__setitem__("shape", [2, 3]),
    )
    with pytest.raises(ArchiveError, match="shared radius axis must be 1-D"):
        read_aucx(broken)


def test_a_per_scan_radius_shape_disagreement_is_rejected(tmp_path: Path) -> None:
    path = _export(_per_scan_experiment(), tmp_path)
    buffer = io.BytesIO()
    np.save(buffer, np.zeros((3, 2), dtype=np.float64), allow_pickle=False)
    broken = _with_manifest(
        _rechecksummed(path, tmp_path / "s.aucx", {RADIUS_MEMBER: buffer.getvalue()}),
        tmp_path / "t.aucx",
        lambda m: m["observations"]["arrays"]["radius"].__setitem__("shape", [3, 2]),
    )
    with pytest.raises(ArchiveError, match="does not match signal shape"):
        read_aucx(broken)


def test_invalid_stored_observations_are_reported_as_archive_errors(
    tmp_path: Path,
) -> None:
    """A non-finite value that the model would reject surfaces as ArchiveError."""
    path = _export(_shared_experiment(), tmp_path)
    buffer = io.BytesIO()
    np.save(buffer, np.array([6.0, np.nan, 6.2]), allow_pickle=False)
    broken = _rechecksummed(
        path, tmp_path / "t.aucx", {RADIUS_MEMBER: buffer.getvalue()}
    )
    with pytest.raises(ArchiveError, match="not a valid shared-axis set"):
        read_aucx(broken)


def test_unrebuildable_metadata_is_reported_as_an_archive_error(
    tmp_path: Path,
) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rechecksummed(
        path, tmp_path / "t.aucx", {EXPERIMENT_MEMBER: b'{"metadata": {}}\n'}
    )
    with pytest.raises(ArchiveError, match="could not be rebuilt"):
        read_aucx(broken)


def test_provenance_without_an_export_record_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rechecksummed(
        path, tmp_path / "t.aucx", {PROVENANCE_MEMBER: b'{"import": null}\n'}
    )
    with pytest.raises(ArchiveError, match="no 'export' object"):
        inspect_aucx(broken)


def test_an_invalid_export_record_is_rejected(tmp_path: Path) -> None:
    path = _export(_shared_experiment(), tmp_path)
    broken = _rechecksummed(
        path,
        tmp_path / "t.aucx",
        {PROVENANCE_MEMBER: b'{"import": null, "export": {"bogus": 1}}\n'},
    )
    with pytest.raises(ArchiveError, match="export provenance is invalid"):
        inspect_aucx(broken)


def test_an_invalid_radius_mode_is_rejected(tmp_path: Path) -> None:
    broken = _with_manifest(
        _export(_shared_experiment(), tmp_path),
        tmp_path / "t.aucx",
        lambda m: m["observations"].__setitem__("mode", "sideways"),
    )
    with pytest.raises(ArchiveError):
        read_aucx(broken)
