# Experiments and metadata

The canonical in-memory model. See
[Canonical data model](../concepts/data-model.md) for the design.

## AUCExperiment

::: openauc.models.experiment.AUCExperiment

## Experiment identity

::: openauc.models.metadata.ExperimentMetadata

## Scans

::: openauc.models.scan.ScanMetadata

## Samples

::: openauc.models.sample.SampleMetadata

## Instrument

::: openauc.models.instrument.InstrumentMetadata

## Quantities

The primitive for a scientific scalar: a value, a declared unit, an explicit
presence status and a provenance tag. See
[Missing, unknown and not-applicable](../concepts/missing-and-unknown-values.md).

::: openauc.models.metadata.Quantity

## Provenance

::: openauc.models.provenance.ImportProvenance

::: openauc.models.provenance.SourceChecksum

## Enumerations

::: openauc.models.enums
    options:
      members:
        - ExperimentType
        - OpticalSystem
        - Unit
        - RadiusAxisMode
        - ValueStatus
        - ValueProvenance
