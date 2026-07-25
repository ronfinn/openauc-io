"""The AUCX archival container: a versioned, inspectable ZIP of parts.

An ``.aucx`` file is a ZIP holding JSON metadata and NumPy ``.npy`` arrays:

.. code-block:: text

    manifest.json          format version, export record, array shapes/dtypes
    experiment.json        metadata, instrument, samples, scans
    provenance.json        inherited import provenance + the export record
    arrays/radius.npy      radius values (1-D shared, or 2-D padded per-scan)
    arrays/signal.npy      signal values, always 2-D (scan, point)
    arrays/mask.npy        authoritative boolean validity mask, always 2-D
    checksums.sha256       SHA-256 of every other member

Numeric data is stored as ``.npy`` so dtype, shape and the validity mask survive
exactly; no tabular re-encoding is involved, and no heavy archive dependency is
introduced. Arrays are always loaded with ``allow_pickle=False``, so reading an
archive can never execute code.

**Checksums establish integrity, not authenticity.** A verified archive is one
whose bytes are unchanged since it was written. It carries no proof of who wrote
it. Nothing is reported as valid before verification succeeds.

Exports are deterministic: fixed member order, normalised ZIP timestamps and
permissions, fixed compression, and JSON written with sorted keys. Two exports
of equivalent experiments with the same ``exported_at`` are byte-identical.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import os
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, ValidationError

from openauc.exceptions import (
    ArchiveError,
    ArchiveIntegrityError,
    ArchiveVersionError,
)
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    ImportProvenance,
    InstrumentMetadata,
    Observations,
    RadiusAxisMode,
    SampleMetadata,
    ScanMetadata,
    Unit,
)

__all__ = [
    "AUCX_FORMAT_ID",
    "AUCX_FORMAT_VERSION",
    "AUCX_SUFFIX",
    "AUCXExport",
    "AUCXInfo",
    "ArchiveIssue",
    "ArchiveValidationReport",
    "export_aucx",
    "inspect_aucx",
    "read_aucx",
    "validate_aucx",
]

AUCX_FORMAT_ID = "aucx"
AUCX_FORMAT_VERSION = "1.0"
AUCX_SUFFIX = ".aucx"

MANIFEST_MEMBER = "manifest.json"
EXPERIMENT_MEMBER = "experiment.json"
PROVENANCE_MEMBER = "provenance.json"
RADIUS_MEMBER = "arrays/radius.npy"
SIGNAL_MEMBER = "arrays/signal.npy"
MASK_MEMBER = "arrays/mask.npy"
CHECKSUM_MEMBER = "checksums.sha256"

#: Members carrying payload, in deterministic write order. ``manifest.json`` is
#: written first and checksummed; ``checksums.sha256`` is written last and is
#: the only member not covered by a checksum.
PAYLOAD_MEMBERS = (
    EXPERIMENT_MEMBER,
    PROVENANCE_MEMBER,
    RADIUS_MEMBER,
    SIGNAL_MEMBER,
    MASK_MEMBER,
)

#: Refuse to allocate more than this from a single member, or in total. Guards
#: against a small archive that declares enormous uncompressed payloads.
MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024

# Fixed ZIP metadata so equivalent exports are byte-identical.
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_ZIP_PERMISSIONS = 0o644 << 16
_COMPRESS_LEVEL = 6

_ALLOWED_ARRAY_KINDS = {"radius": "f", "signal": "f", "mask": "b"}


# --------------------------------------------------------------------------- #
# Public records
# --------------------------------------------------------------------------- #


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AUCXExport(_Frozen):
    """The export event that produced an archive.

    Distinct from the experiment's own import provenance, which records where
    the data originally came from and travels with the model unchanged.
    """

    aucx_format_version: str = AUCX_FORMAT_VERSION
    software: str = "openauc"
    software_version: str | None = None
    exported_at: datetime | None = None
    checksum_algorithm: str = "sha256"
    member_count: int = 0


class AUCXInfo(_Frozen):
    """What an archive declares about itself, after integrity verification."""

    path: str
    aucx_format_version: str
    export: AUCXExport
    members: tuple[str, ...] = ()
    checksum_verified: bool = False
    radius_axis_mode: RadiusAxisMode = RadiusAxisMode.SHARED
    n_scans: int = 0
    n_points: int = 0
    scan_ids: tuple[str, ...] = ()
    radius_unit: Unit = Unit.CENTIMETRE
    signal_unit: Unit = Unit.UNKNOWN
    experiment_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain JSON-friendly Python types."""
        return self.model_dump(mode="json")


@dataclasses.dataclass(frozen=True)
class ArchiveIssue:
    """One archive-integrity finding. Not a structural or scientific finding."""

    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclasses.dataclass(frozen=True)
class ArchiveValidationReport:
    """Container-level validation only.

    This reports whether an archive is readable and internally intact. It makes
    no structural or scientific judgement about the experiment inside — use
    ``experiment.validate()`` and ``experiment.assess_readiness()`` for those,
    after loading.
    """

    path: str
    issues: tuple[ArchiveIssue, ...] = ()
    info: AUCXInfo | None = None

    @property
    def is_valid(self) -> bool:
        """True when no integrity problem was found."""
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "is_valid": self.is_valid,
            "issues": [{"code": i.code, "message": i.message} for i in self.issues],
            "info": self.info.to_dict() if self.info is not None else None,
        }

    def __str__(self) -> str:
        if self.is_valid:
            return f"archive integrity: OK ({self.path})"
        header = f"archive integrity: FAILED ({len(self.issues)} issue(s))"
        return "\n".join([header, *(f"  - {issue}" for issue in self.issues)])


# --------------------------------------------------------------------------- #
# Serialisation helpers
# --------------------------------------------------------------------------- #


def _dumps(payload: dict[str, Any]) -> bytes:
    """Deterministic JSON: sorted keys, fixed separators, trailing newline."""
    text = json.dumps(
        payload, sort_keys=True, indent=2, separators=(",", ": "), ensure_ascii=False
    )
    return (text + "\n").encode("utf-8")


def _save_npy(array: NDArray[Any]) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    return buffer.getvalue()


def _observation_arrays(
    observations: Observations,
) -> tuple[NDArray[Any], NDArray[Any], NDArray[Any]]:
    """``(radius, signal, mask)`` exactly as stored, with a mask in both modes.

    In shared mode the model has no mask because every stored value is a real
    observation; an all-true mask is written so both modes have the same three
    parts and a reader never has to infer one.
    """
    dataset = observations.dataset
    signal = np.asarray(dataset["signal"].to_numpy(), dtype=np.float64)
    if observations.mode is RadiusAxisMode.SHARED:
        radius = np.asarray(dataset["radius"].to_numpy(), dtype=np.float64)
        mask = np.ones(signal.shape, dtype=np.bool_)
        return radius, signal, mask
    radius = np.asarray(dataset["radius"].to_numpy(), dtype=np.float64)
    mask = np.asarray(dataset["mask"].to_numpy(), dtype=np.bool_)
    return radius, signal, mask


def _experiment_payload(experiment: AUCExperiment) -> dict[str, Any]:
    return {
        "metadata": experiment.metadata.model_dump(mode="json"),
        "instrument": (
            experiment.instrument.model_dump(mode="json")
            if experiment.instrument is not None
            else None
        ),
        "samples": [s.model_dump(mode="json") for s in experiment.samples],
        "scans": [s.model_dump(mode="json") for s in experiment.scans],
    }


def _manifest_payload(
    experiment: AUCExperiment,
    export: AUCXExport,
    arrays: tuple[NDArray[Any], NDArray[Any], NDArray[Any]],
) -> dict[str, Any]:
    radius, signal, mask = arrays
    observations = experiment.observations
    return {
        "aucx_format_version": AUCX_FORMAT_VERSION,
        "created_by": {
            "software": export.software,
            "version": export.software_version,
        },
        "exported_at": (
            export.exported_at.isoformat() if export.exported_at is not None else None
        ),
        "checksum_algorithm": export.checksum_algorithm,
        "parts": list(PAYLOAD_MEMBERS),
        "observations": {
            "mode": observations.mode.value,
            "radius_unit": observations.radius_unit.value,
            "signal_unit": observations.signal_unit.value,
            "scan_ids": list(observations.scan_ids),
            "n_scans": int(signal.shape[0]),
            "n_points": int(signal.shape[1]) if signal.ndim == 2 else 0,
            "arrays": {
                "radius": {
                    "path": RADIUS_MEMBER,
                    "dtype": str(radius.dtype),
                    "shape": list(radius.shape),
                },
                "signal": {
                    "path": SIGNAL_MEMBER,
                    "dtype": str(signal.dtype),
                    "shape": list(signal.shape),
                },
                "mask": {
                    "path": MASK_MEMBER,
                    "dtype": str(mask.dtype),
                    "shape": list(mask.shape),
                },
            },
        },
    }


def _checksum_document(members: dict[str, bytes]) -> bytes:
    """``<sha256>  <member>`` lines, sorted by member name, LF-terminated."""
    lines = [
        f"{hashlib.sha256(payload).hexdigest()}  {name}"
        for name, payload in sorted(members.items())
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _parse_checksum_document(raw: bytes) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArchiveIntegrityError(
            f"{CHECKSUM_MEMBER} is not valid UTF-8 text"
        ) from exc
    entries: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        digest, separator, name = line.partition("  ")
        if not separator or not name.strip():
            raise ArchiveIntegrityError(
                f"{CHECKSUM_MEMBER} line {number} is malformed; expected "
                f"'<64-hex digest>  <member name>', got {line!r}"
            )
        digest = digest.strip()
        if len(digest) != 64 or any(
            c not in "0123456789abcdef" for c in digest.lower()
        ):
            raise ArchiveIntegrityError(
                f"{CHECKSUM_MEMBER} line {number} does not carry a 64-character "
                f"hexadecimal SHA-256 digest: {digest!r}"
            )
        if name in entries:
            raise ArchiveIntegrityError(
                f"{CHECKSUM_MEMBER} lists {name!r} more than once"
            )
        entries[name] = digest.lower()
    if not entries:
        raise ArchiveIntegrityError(f"{CHECKSUM_MEMBER} lists no members")
    return entries


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #


def export_aucx(
    experiment: AUCExperiment,
    path: str | Path,
    *,
    overwrite: bool = False,
    exported_at: datetime | None = None,
) -> Path:
    """Write ``experiment`` to an AUCX archive and return the written path.

    The archive is written to a sibling temporary file, verified by reading it
    back in full, and only then moved into place — so a failure never leaves a
    partial or corrupt archive at the destination.

    Args:
        experiment: The experiment to archive.
        path: Destination ``.aucx`` path.
        overwrite: Replace an existing file. Refuses by default.
        exported_at: Timestamp recorded in the export provenance. Defaults to
            the current UTC time; pass a fixed value for byte-identical output.

    Returns:
        The path written.

    Raises:
        ArchiveError: if the destination exists and ``overwrite`` is False, or
            if the archive fails its own verification.
    """
    from openauc import __version__

    destination = Path(path)
    if destination.exists() and not overwrite:
        raise ArchiveError(
            f"refusing to overwrite existing file: {destination}; "
            "pass overwrite=True to replace it"
        )
    if destination.parent and not destination.parent.exists():
        raise ArchiveError(
            f"destination directory does not exist: {destination.parent}"
        )

    export = AUCXExport(
        software_version=__version__,
        exported_at=exported_at if exported_at is not None else datetime.now(UTC),
        member_count=len(PAYLOAD_MEMBERS) + 1,
    )
    members = _build_members(experiment, export)

    handle, temporary_name = tempfile.mkstemp(
        dir=str(destination.parent or Path()), prefix=".aucx-", suffix=".tmp"
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        _write_zip(temporary, members)
        # Verify the completed archive before it replaces anything.
        read_aucx(temporary)
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def _build_members(experiment: AUCExperiment, export: AUCXExport) -> dict[str, bytes]:
    arrays = _observation_arrays(experiment.observations)
    radius, signal, mask = arrays
    provenance_payload = {
        "import": (
            experiment.provenance.model_dump(mode="json")
            if experiment.provenance is not None
            else None
        ),
        "export": export.model_dump(mode="json"),
    }
    members = {
        MANIFEST_MEMBER: _dumps(_manifest_payload(experiment, export, arrays)),
        EXPERIMENT_MEMBER: _dumps(_experiment_payload(experiment)),
        PROVENANCE_MEMBER: _dumps(provenance_payload),
        RADIUS_MEMBER: _save_npy(radius),
        SIGNAL_MEMBER: _save_npy(signal),
        MASK_MEMBER: _save_npy(mask),
    }
    members[CHECKSUM_MEMBER] = _checksum_document(members)
    return members


def _write_zip(target: Path, members: dict[str, bytes]) -> None:
    order = (MANIFEST_MEMBER, *PAYLOAD_MEMBERS, CHECKSUM_MEMBER)
    with zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=_COMPRESS_LEVEL,
    ) as archive:
        for name in order:
            info = zipfile.ZipInfo(filename=name, date_time=_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = _ZIP_PERMISSIONS
            info.create_system = 0
            archive.writestr(info, members[name])


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def _check_member_name(name: str) -> None:
    """Reject absolute, traversing or otherwise unsafe member names."""
    if not name or name.endswith("/"):
        raise ArchiveError(f"archive contains an unexpected directory entry: {name!r}")
    if "\\" in name:
        raise ArchiveError(f"archive member name uses backslashes: {name!r}")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        raise ArchiveError(f"archive member name is absolute: {name!r}")
    parts = PurePosixPath(name).parts
    if any(part == ".." for part in parts):
        raise ArchiveError(f"archive member name traverses directories: {name!r}")


def _open_archive(path: Path) -> zipfile.ZipFile:
    if not path.exists():
        raise ArchiveError(f"archive does not exist: {path}")
    if not path.is_file():
        raise ArchiveError(f"archive path is not a file: {path}")
    try:
        return zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as exc:
        raise ArchiveError(f"{path.name} is not a readable ZIP archive: {exc}") from exc


def _read_members(archive: zipfile.ZipFile, path: Path) -> dict[str, bytes]:
    """Read every member with safety checks applied before allocation."""
    infos = archive.infolist()
    if not infos:
        raise ArchiveError(f"{path.name} contains no members")

    seen: set[str] = set()
    total = 0
    for info in infos:
        _check_member_name(info.filename)
        if info.filename in seen:
            raise ArchiveError(
                f"{path.name} contains duplicate member {info.filename!r}"
            )
        seen.add(info.filename)
        if info.flag_bits & 0x1:
            raise ArchiveError(
                f"{path.name} member {info.filename!r} is encrypted; "
                "encrypted archives are not supported"
            )
        if info.file_size > MAX_MEMBER_BYTES:
            raise ArchiveError(
                f"{path.name} member {info.filename!r} declares "
                f"{info.file_size} bytes, above the {MAX_MEMBER_BYTES}-byte limit"
            )
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise ArchiveError(
                f"{path.name} declares more than {MAX_TOTAL_BYTES} uncompressed "
                "bytes in total"
            )

    payloads: dict[str, bytes] = {}
    for info in infos:
        try:
            payloads[info.filename] = archive.read(info.filename)
        except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
            raise ArchiveError(
                f"{path.name}: member {info.filename!r} could not be read: {exc}"
            ) from exc
    return payloads


def _loads(raw: bytes, member: str, path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"{path.name}: {member} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArchiveError(
            f"{path.name}: {member} must contain a JSON object, "
            f"got {type(payload).__name__}"
        )
    return payload


def _load_npy(raw: bytes, member: str, path: Path) -> NDArray[Any]:
    try:
        array = np.load(io.BytesIO(raw), allow_pickle=False)
    except Exception as exc:  # numpy raises a range of low-level errors
        raise ArchiveError(
            f"{path.name}: {member} is not a readable .npy array "
            f"(pickled arrays are rejected): {exc}"
        ) from exc
    if not isinstance(array, np.ndarray):
        raise ArchiveError(f"{path.name}: {member} did not contain an array")
    if array.dtype.hasobject:
        raise ArchiveError(
            f"{path.name}: {member} contains an object array, which is rejected"
        )
    return array


def _verify_checksums(
    payloads: dict[str, bytes], path: Path
) -> tuple[dict[str, Any], dict[str, str]]:
    """Verify every listed member, then return the parsed manifest and digests."""
    if CHECKSUM_MEMBER not in payloads:
        raise ArchiveIntegrityError(
            f"{path.name} has no {CHECKSUM_MEMBER}; an archive without checksums "
            "cannot be verified and is not accepted"
        )
    listed = _parse_checksum_document(payloads[CHECKSUM_MEMBER])

    if MANIFEST_MEMBER not in listed:
        raise ArchiveIntegrityError(
            f"{path.name}: {CHECKSUM_MEMBER} does not list {MANIFEST_MEMBER}"
        )
    for name, digest in sorted(listed.items()):
        if name not in payloads:
            raise ArchiveIntegrityError(
                f"{path.name}: {CHECKSUM_MEMBER} lists {name!r}, which is missing "
                "from the archive"
            )
        actual = hashlib.sha256(payloads[name]).hexdigest()
        if actual != digest:
            raise ArchiveIntegrityError(
                f"{path.name}: checksum mismatch for {name!r} "
                f"(recorded {digest}, computed {actual}); the archive has been "
                "modified or is corrupt"
            )

    unlisted = set(payloads) - set(listed) - {CHECKSUM_MEMBER}
    if unlisted:
        raise ArchiveIntegrityError(
            f"{path.name} contains member(s) {sorted(unlisted)} that "
            f"{CHECKSUM_MEMBER} does not list"
        )

    manifest = _loads(payloads[MANIFEST_MEMBER], MANIFEST_MEMBER, path)
    return manifest, listed


def _require_version(manifest: dict[str, Any], path: Path) -> str:
    declared = manifest.get("aucx_format_version")
    if not isinstance(declared, str) or not declared:
        raise ArchiveVersionError(
            f"{path.name}: manifest does not declare aucx_format_version"
        )
    if declared != AUCX_FORMAT_VERSION:
        raise ArchiveVersionError(
            f"{path.name}: unsupported AUCX format version {declared!r}; "
            f"this build reads {AUCX_FORMAT_VERSION!r} only. Archives are never "
            "migrated silently."
        )
    return declared


def _require_parts(
    manifest: dict[str, Any], payloads: dict[str, bytes], path: Path
) -> None:
    parts = manifest.get("parts")
    if not isinstance(parts, list) or not all(isinstance(p, str) for p in parts):
        raise ArchiveError(f"{path.name}: manifest 'parts' must be a list of names")
    missing = [name for name in PAYLOAD_MEMBERS if name not in parts]
    if missing:
        raise ArchiveError(
            f"{path.name}: manifest 'parts' omits required member(s) {missing}"
        )
    for name in parts:
        _check_member_name(name)
        if name not in payloads:
            raise ArchiveError(
                f"{path.name}: manifest lists part {name!r}, which is missing "
                "from the archive"
            )
    expected = set(parts) | {MANIFEST_MEMBER, CHECKSUM_MEMBER}
    unexpected = set(payloads) - expected
    if unexpected:
        raise ArchiveError(
            f"{path.name} contains unexpected member(s) {sorted(unexpected)}; "
            "the manifest does not list them as parts"
        )


def _observations_from(
    manifest: dict[str, Any], payloads: dict[str, bytes], path: Path
) -> Observations:
    block = manifest.get("observations")
    if not isinstance(block, dict):
        raise ArchiveError(f"{path.name}: manifest has no 'observations' block")
    try:
        mode = RadiusAxisMode(str(block["mode"]))
        radius_unit = Unit(str(block["radius_unit"]))
        signal_unit = Unit(str(block["signal_unit"]))
        scan_ids = [str(s) for s in block["scan_ids"]]
    except (KeyError, ValueError) as exc:
        raise ArchiveError(
            f"{path.name}: manifest 'observations' block is incomplete or "
            f"invalid: {exc}"
        ) from exc

    radius = _load_npy(payloads[RADIUS_MEMBER], RADIUS_MEMBER, path)
    signal = _load_npy(payloads[SIGNAL_MEMBER], SIGNAL_MEMBER, path)
    mask = _load_npy(payloads[MASK_MEMBER], MASK_MEMBER, path)

    _check_array_kinds(radius, signal, mask, path)
    _check_declared_shapes(block, radius, signal, mask, path)

    if signal.ndim != 2:
        raise ArchiveError(
            f"{path.name}: signal must be 2-D (scan, point), got {signal.ndim}-D"
        )
    if mask.shape != signal.shape:
        raise ArchiveError(
            f"{path.name}: mask shape {mask.shape} does not match signal shape "
            f"{signal.shape}"
        )
    if signal.shape[0] != len(scan_ids):
        raise ArchiveError(
            f"{path.name}: manifest lists {len(scan_ids)} scan id(s) but the "
            f"signal array has {signal.shape[0]} row(s)"
        )

    if mode is RadiusAxisMode.SHARED:
        return _shared_observations(
            radius, signal, mask, scan_ids, signal_unit, radius_unit, path
        )
    return _per_scan_observations(
        radius, signal, mask, scan_ids, signal_unit, radius_unit, path
    )


def _check_array_kinds(
    radius: NDArray[Any], signal: NDArray[Any], mask: NDArray[Any], path: Path
) -> None:
    for name, array in (("radius", radius), ("signal", signal), ("mask", mask)):
        expected = _ALLOWED_ARRAY_KINDS[name]
        if array.dtype.kind != expected:
            raise ArchiveError(
                f"{path.name}: {name} array has dtype {array.dtype!r}; expected a "
                f"{'boolean' if expected == 'b' else 'floating-point'} array"
            )
    if mask.dtype != np.bool_:
        raise ArchiveError(
            f"{path.name}: mask must be a boolean array, got dtype {mask.dtype!r}"
        )


def _check_declared_shapes(
    block: dict[str, Any],
    radius: NDArray[Any],
    signal: NDArray[Any],
    mask: NDArray[Any],
    path: Path,
) -> None:
    declared = block.get("arrays")
    if not isinstance(declared, dict):
        return
    for name, array in (("radius", radius), ("signal", signal), ("mask", mask)):
        entry = declared.get(name)
        if not isinstance(entry, dict):
            continue
        shape = entry.get("shape")
        if isinstance(shape, list) and tuple(shape) != array.shape:
            raise ArchiveError(
                f"{path.name}: manifest declares {name} shape {tuple(shape)} but "
                f"the stored array has shape {array.shape}"
            )


def _shared_observations(
    radius: NDArray[Any],
    signal: NDArray[Any],
    mask: NDArray[Any],
    scan_ids: list[str],
    signal_unit: Unit,
    radius_unit: Unit,
    path: Path,
) -> Observations:
    if radius.ndim != 1:
        raise ArchiveError(
            f"{path.name}: a shared radius axis must be 1-D, got {radius.ndim}-D"
        )
    if signal.shape[1] != radius.shape[0]:
        raise ArchiveError(
            f"{path.name}: shared radius axis has {radius.shape[0]} point(s) but "
            f"the signal array has {signal.shape[1]} column(s)"
        )
    if mask.size and not bool(mask.all()):
        raise ArchiveError(
            f"{path.name}: shared-axis archives must carry an all-true mask; the "
            "canonical model cannot represent partially valid shared-axis scans. "
            "Export this experiment in per-scan mode instead."
        )
    try:
        return Observations.from_shared_axis(
            radius=radius,
            signal=signal,
            scan_ids=scan_ids,
            signal_unit=signal_unit,
            radius_unit=radius_unit,
        )
    except Exception as exc:
        raise ArchiveError(
            f"{path.name}: stored observations are not a valid shared-axis set: {exc}"
        ) from exc


def _per_scan_observations(
    radius: NDArray[Any],
    signal: NDArray[Any],
    mask: NDArray[Any],
    scan_ids: list[str],
    signal_unit: Unit,
    radius_unit: Unit,
    path: Path,
) -> Observations:
    if radius.ndim != 2:
        raise ArchiveError(
            f"{path.name}: per-scan radius must be 2-D (scan, point), got "
            f"{radius.ndim}-D"
        )
    if radius.shape != signal.shape:
        raise ArchiveError(
            f"{path.name}: radius shape {radius.shape} does not match signal "
            f"shape {signal.shape}"
        )
    radii = [row[keep] for row, keep in zip(radius, mask, strict=True)]
    signals = [row[keep] for row, keep in zip(signal, mask, strict=True)]
    try:
        return Observations.from_per_scan(
            radii=radii,
            signals=signals,
            scan_ids=scan_ids,
            signal_unit=signal_unit,
            radius_unit=radius_unit,
        )
    except Exception as exc:
        raise ArchiveError(
            f"{path.name}: stored observations are not a valid per-scan set: {exc}"
        ) from exc


def _experiment_from(
    payloads: dict[str, bytes], observations: Observations, path: Path
) -> AUCExperiment:
    experiment_payload = _loads(payloads[EXPERIMENT_MEMBER], EXPERIMENT_MEMBER, path)
    provenance_payload = _loads(payloads[PROVENANCE_MEMBER], PROVENANCE_MEMBER, path)
    imported = provenance_payload.get("import")
    try:
        instrument = experiment_payload.get("instrument")
        return AUCExperiment(
            metadata=ExperimentMetadata.model_validate(experiment_payload["metadata"]),
            scans=tuple(
                ScanMetadata.model_validate(item)
                for item in experiment_payload.get("scans", [])
            ),
            observations=observations,
            samples=tuple(
                SampleMetadata.model_validate(item)
                for item in experiment_payload.get("samples", [])
            ),
            instrument=(
                InstrumentMetadata.model_validate(instrument)
                if instrument is not None
                else None
            ),
            provenance=(
                ImportProvenance.model_validate(imported)
                if imported is not None
                else None
            ),
        )
    except (KeyError, TypeError, ValidationError) as exc:
        raise ArchiveError(
            f"{path.name}: stored metadata could not be rebuilt into an "
            f"experiment: {exc}"
        ) from exc


def _export_record(payloads: dict[str, bytes], path: Path) -> AUCXExport:
    payload = _loads(payloads[PROVENANCE_MEMBER], PROVENANCE_MEMBER, path)
    record = payload.get("export")
    if not isinstance(record, dict):
        raise ArchiveError(f"{path.name}: {PROVENANCE_MEMBER} has no 'export' object")
    try:
        return AUCXExport.model_validate(record)
    except ValidationError as exc:
        raise ArchiveError(f"{path.name}: export provenance is invalid: {exc}") from exc


def _read_verified(path: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Open, safety-check and fully verify an archive before anything is built."""
    with _open_archive(path) as archive:
        payloads = _read_members(archive, path)
    manifest, _ = _verify_checksums(payloads, path)
    _require_version(manifest, path)
    _require_parts(manifest, payloads, path)
    return payloads, manifest


def read_aucx(path: str | Path) -> AUCExperiment:
    """Read an AUCX archive into an :class:`AUCExperiment`.

    Every checksum is verified before any model is constructed. The returned
    experiment carries the *import* provenance stored in the archive, unchanged,
    so a round trip preserves it; the export record is available separately via
    :func:`inspect_aucx`.

    Raises:
        ArchiveError: for unreadable, unsafe or inconsistent archives.
        ArchiveIntegrityError: for checksum problems.
        ArchiveVersionError: for an unsupported format version.
    """
    target = Path(path)
    payloads, manifest = _read_verified(target)
    observations = _observations_from(manifest, payloads, target)
    return _experiment_from(payloads, observations, target)


def inspect_aucx(path: str | Path) -> AUCXInfo:
    """Verify an archive's integrity and report what it declares.

    This is container-level inspection only. It reports nothing about the
    structural or scientific standing of the experiment inside.
    """
    target = Path(path)
    payloads, manifest = _read_verified(target)
    block = manifest.get("observations")
    observations_block = block if isinstance(block, dict) else {}
    experiment_payload = _loads(payloads[EXPERIMENT_MEMBER], EXPERIMENT_MEMBER, target)
    metadata = experiment_payload.get("metadata")
    experiment_id = (
        str(metadata.get("experiment_id")) if isinstance(metadata, dict) else None
    )
    try:
        mode = RadiusAxisMode(str(observations_block.get("mode")))
    except ValueError as exc:
        raise ArchiveError(f"{target.name}: invalid radius axis mode: {exc}") from exc
    return AUCXInfo(
        path=str(target),
        aucx_format_version=str(manifest["aucx_format_version"]),
        export=_export_record(payloads, target),
        members=tuple(sorted(payloads)),
        checksum_verified=True,
        radius_axis_mode=mode,
        n_scans=int(observations_block.get("n_scans", 0)),
        n_points=int(observations_block.get("n_points", 0)),
        scan_ids=tuple(str(s) for s in observations_block.get("scan_ids", [])),
        radius_unit=Unit(
            str(observations_block.get("radius_unit", Unit.UNKNOWN.value))
        ),
        signal_unit=Unit(
            str(observations_block.get("signal_unit", Unit.UNKNOWN.value))
        ),
        experiment_id=experiment_id,
    )


def validate_aucx(path: str | Path) -> ArchiveValidationReport:
    """Check an archive's integrity without raising.

    Container-level validation only: readability, safety, member agreement and
    checksums. Structural and readiness validation of the experiment inside
    remain separate — load the archive and use ``experiment.validate()``.
    """
    target = Path(path)
    try:
        info = inspect_aucx(target)
    except ArchiveVersionError as exc:
        return _failed(target, "unsupported_format_version", exc)
    except ArchiveIntegrityError as exc:
        return _failed(target, "checksum_verification_failed", exc)
    except ArchiveError as exc:
        return _failed(target, "archive_unreadable", exc)
    try:
        read_aucx(target)
    except ArchiveError as exc:
        return _failed(target, "archive_contents_invalid", exc, info=info)
    return ArchiveValidationReport(path=str(target), info=info)


def _failed(
    path: Path, code: str, exc: Exception, *, info: AUCXInfo | None = None
) -> ArchiveValidationReport:
    return ArchiveValidationReport(
        path=str(path), issues=(ArchiveIssue(code=code, message=str(exc)),), info=info
    )
