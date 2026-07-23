"""Complete metadata, serialisation and reconstruction (2, 6, 13, 14)."""

from __future__ import annotations

from datetime import UTC, datetime

from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    ExperimentType,
    ImportProvenance,
    InstrumentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    SampleMetadata,
    ScanMetadata,
    Unit,
    ValueProvenance,
    ValueStatus,
)


def _complete_experiment() -> AUCExperiment:
    metadata = ExperimentMetadata(
        experiment_id="exp-complete",
        name="BSA velocity run",
        description="Synthetic complete-metadata fixture",
        experiment_type=ExperimentType.SEDIMENTATION_VELOCITY,
        acquired_at=datetime(2026, 7, 23, 10, 30, tzinfo=UTC),
        operator="synthetic",
        notes="all fields populated",
    )
    instrument = InstrumentMetadata(
        manufacturer="Synthetic Instruments",
        model="Model-X",
        serial_number="SN-001",
        rotor_id="AN-60-Ti",
        nominal_speed=Quantity.of(50000.0, Unit.RPM),
        temperature=Quantity.of(20.0, Unit.DEGREE_CELSIUS),
        cell="1",
        channel="A",
        centrepiece="dual-sector Epon",
        optical_system=OpticalSystem.ABSORBANCE,
        wavelength=Quantity.of(280.0, Unit.NANOMETRE),
    )
    sample = SampleMetadata(
        sample_id="sample-1",
        description="BSA",
        buffer_description="PBS pH 7.4",
        concentration=Quantity.of(0.5, Unit.OTHER, unit_label="mg/mL"),
        density=Quantity.of(1.005, Unit.OTHER, unit_label="g/mL"),
        viscosity=Quantity.unknown(),
        partial_specific_volume=Quantity.of(
            0.734, Unit.OTHER, unit_label="mL/g", provenance=ValueProvenance.INFERRED
        ),
        notes="synthetic",
    )
    scans = tuple(
        ScanMetadata(
            scan_id=f"scan-{i}",
            index=i,
            elapsed_time=Quantity.of(float(i) * 600.0, Unit.SECOND),
            acquired_at=datetime(2026, 7, 23, 10, 30 + i, tzinfo=UTC),
            cell="1",
            channel="A",
            wavelength=Quantity.of(280.0, Unit.NANOMETRE),
            optical_system=OpticalSystem.ABSORBANCE,
            rotor_speed=Quantity.of(50000.0, Unit.RPM),
            temperature=Quantity.of(20.0, Unit.DEGREE_CELSIUS),
            source_file="synthetic.csv",
            annotations=("synthetic",),
        )
        for i in range(3)
    )
    observations = Observations.from_shared_axis(
        radius=[6.0, 6.1, 6.2, 6.3],
        signal=[
            [0.10, 0.20, 0.30, 0.40],
            [0.11, 0.19, 0.29, 0.39],
            [0.12, 0.18, 0.28, 0.38],
        ],
        scan_ids=["scan-0", "scan-1", "scan-2"],
        signal_unit=Unit.ABSORBANCE_UNIT,
    )
    provenance = ImportProvenance(
        source_path="/data/synthetic.csv",
        source_filename="synthetic.csv",
        sha256="a" * 64,
        parser_name="synthetic",
        parser_version="0.0.0",
        imported_at=datetime(2026, 7, 23, 11, 0, tzinfo=UTC),
        transformations=("none",),
        assumptions=("radius declared in centimetres",),
        supplied_values=("metadata.experiment_id",),
        inferred_values=("sample-1.partial_specific_volume",),
    )
    return AUCExperiment(
        metadata=metadata,
        scans=scans,
        observations=observations,
        samples=(sample,),
        instrument=instrument,
        provenance=provenance,
    )


def test_complete_experiment_is_valid() -> None:
    experiment = _complete_experiment()
    report = experiment.validate_structure()
    assert report.is_valid, str(report)
    assert len(experiment.scans) == 3
    assert experiment.instrument is not None
    assert experiment.provenance is not None


def test_missing_optional_metadata_stays_none() -> None:
    metadata = ExperimentMetadata(experiment_id="exp")
    assert metadata.name is None
    assert metadata.operator is None
    # Unknown is distinct from missing/None.
    viscosity = Quantity.unknown()
    assert viscosity.status is ValueStatus.UNKNOWN
    assert viscosity.value is None


def test_metadata_roundtrip_via_dict() -> None:
    experiment = _complete_experiment()
    payload = experiment.to_dict()
    restored = AUCExperiment.from_dict(payload)

    assert restored.metadata == experiment.metadata
    assert restored.instrument == experiment.instrument
    assert restored.samples == experiment.samples
    assert restored.scans == experiment.scans
    assert restored.provenance == experiment.provenance
    assert restored.observations == experiment.observations
    assert restored.to_dict() == payload


def test_pydantic_model_json_roundtrip() -> None:
    scan = ScanMetadata(
        scan_id="s", index=0, elapsed_time=Quantity.of(1.0, Unit.SECOND)
    )
    dumped = scan.model_dump_json()
    restored = ScanMetadata.model_validate_json(dumped)
    assert restored == scan
