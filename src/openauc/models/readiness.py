"""Analysis-readiness reporting — metadata presence, never scientific judgement.

Readiness answers one narrow question per workflow: *is the metadata that a
future workflow would need actually present?* It never inspects the signal,
never models sedimentation, and never concludes that data are correct, of good
quality, or scientifically suitable.

That last question is represented explicitly and permanently as
:attr:`~openauc.models.enums.AnalysisKind.SCIENTIFIC_SUITABILITY` with status
:attr:`~openauc.models.enums.ReadinessStatus.NOT_ASSESSED`, so "not assessed" is
machine-readable and cannot be omitted from a report. Its status is a constant:
it is never derived from structural or readiness findings.

Routing follows the declared experiment type:

===============================  ==================  ==================
``ExperimentType``               SV                  SE
===============================  ==================  ==================
``SEDIMENTATION_VELOCITY``       assessed            ``NOT_APPLICABLE``
``SEDIMENTATION_EQUILIBRIUM``    ``NOT_APPLICABLE``  assessed
``UNKNOWN``                      assessed            assessed
``OTHER``                        ``NOT_APPLICABLE``  ``NOT_APPLICABLE``
===============================  ==================  ==================

``OTHER`` is an explicit statement that the run is neither a velocity nor an
equilibrium experiment, so neither readiness tier applies. ``UNKNOWN`` is the
absence of a statement, so both are assessed and a non-blocking
``experiment_type_unknown`` warning is recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from openauc.models.enums import (
    AnalysisKind,
    ExperimentType,
    ReadinessStatus,
    ValidationTier,
)
from openauc.models.validation import ValidationIssue, ValidationReport

if TYPE_CHECKING:
    from openauc.models.experiment import AUCExperiment

__all__ = [
    "AnalysisReadiness",
    "ReadinessAssessment",
    "assess_experiment_readiness",
]

#: The fixed statement attached to the scientific-suitability entry.
SCIENTIFIC_SUITABILITY_NOTE = (
    "openauc does not assess scientific validity, data quality or suitability "
    "for sedimentation analysis, and never will as part of validation."
)

_NOT_APPLICABLE_NOTES = {
    (AnalysisKind.SEDIMENTATION_VELOCITY, ExperimentType.SEDIMENTATION_EQUILIBRIUM): (
        "the experiment is declared as sedimentation equilibrium"
    ),
    (AnalysisKind.SEDIMENTATION_EQUILIBRIUM, ExperimentType.SEDIMENTATION_VELOCITY): (
        "the experiment is declared as sedimentation velocity"
    ),
    (AnalysisKind.SEDIMENTATION_VELOCITY, ExperimentType.OTHER): (
        "the experiment type is declared as 'other', which is neither a "
        "velocity nor an equilibrium run"
    ),
    (AnalysisKind.SEDIMENTATION_EQUILIBRIUM, ExperimentType.OTHER): (
        "the experiment type is declared as 'other', which is neither a "
        "velocity nor an equilibrium run"
    ),
}

_TIER_FOR_ANALYSIS = {
    AnalysisKind.SEDIMENTATION_VELOCITY: ValidationTier.SV_READINESS,
    AnalysisKind.SEDIMENTATION_EQUILIBRIUM: ValidationTier.SE_READINESS,
}


@dataclass(frozen=True)
class AnalysisReadiness:
    """Whether the metadata one workflow would need is present.

    ``POTENTIALLY_READY`` reports metadata presence only. It is never a claim
    that the data are correct or that the analysis is appropriate.
    """

    analysis: AnalysisKind
    status: ReadinessStatus
    blocking_issues: tuple[ValidationIssue, ...] = ()
    advisory_issues: tuple[ValidationIssue, ...] = ()
    note: str | None = None

    @property
    def is_blocked(self) -> bool:
        return self.status is ReadinessStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain JSON-friendly Python types."""
        return {
            "analysis": self.analysis.value,
            "status": self.status.value,
            "note": self.note,
            "blocking_issues": [issue.to_dict() for issue in self.blocking_issues],
            "advisory_issues": [issue.to_dict() for issue in self.advisory_issues],
        }

    def __str__(self) -> str:
        suffix = f" - {self.note}" if self.note else ""
        return f"{self.analysis.value}: {self.status.value}{suffix}"


@dataclass(frozen=True)
class ReadinessAssessment:
    """Readiness for every reported workflow, plus the permanent non-assessment."""

    entries: tuple[AnalysisReadiness, ...]

    def for_analysis(self, analysis: AnalysisKind) -> AnalysisReadiness:
        """The entry for ``analysis``."""
        for entry in self.entries:
            if entry.analysis is analysis:
                return entry
        raise KeyError(f"no readiness entry for {analysis.value!r}")

    @property
    def sedimentation_velocity(self) -> AnalysisReadiness:
        return self.for_analysis(AnalysisKind.SEDIMENTATION_VELOCITY)

    @property
    def sedimentation_equilibrium(self) -> AnalysisReadiness:
        return self.for_analysis(AnalysisKind.SEDIMENTATION_EQUILIBRIUM)

    @property
    def scientific_suitability(self) -> AnalysisReadiness:
        """Always :attr:`ReadinessStatus.NOT_ASSESSED`."""
        return self.for_analysis(AnalysisKind.SCIENTIFIC_SUITABILITY)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain JSON-friendly Python types."""
        return {"entries": [entry.to_dict() for entry in self.entries]}

    def __str__(self) -> str:
        return "\n".join(f"  - {entry}" for entry in self.entries)


def assess_experiment_readiness(experiment: AUCExperiment) -> ReadinessAssessment:
    """Report metadata readiness per workflow. Makes no scientific judgement."""
    report = experiment.validate()
    experiment_type = experiment.metadata.experiment_type
    entries = tuple(
        _assess_one(analysis, experiment_type, report)
        for analysis in (
            AnalysisKind.SEDIMENTATION_VELOCITY,
            AnalysisKind.SEDIMENTATION_EQUILIBRIUM,
        )
    )
    scientific = AnalysisReadiness(
        analysis=AnalysisKind.SCIENTIFIC_SUITABILITY,
        status=ReadinessStatus.NOT_ASSESSED,
        note=SCIENTIFIC_SUITABILITY_NOTE,
    )
    return ReadinessAssessment(entries=(*entries, scientific))


def _assess_one(
    analysis: AnalysisKind,
    experiment_type: ExperimentType,
    report: ValidationReport,
) -> AnalysisReadiness:
    note = _NOT_APPLICABLE_NOTES.get((analysis, experiment_type))
    if note is not None:
        return AnalysisReadiness(
            analysis=analysis,
            status=ReadinessStatus.NOT_APPLICABLE,
            note=note,
        )

    tier = _TIER_FOR_ANALYSIS[analysis]
    blocking = report.blocking_for(tier)
    advisory = tuple(
        issue
        for issue in report.issues
        if tier in issue.tiers and not issue.blocks_tier(tier)
    )
    status = ReadinessStatus.BLOCKED if blocking else ReadinessStatus.POTENTIALLY_READY
    return AnalysisReadiness(
        analysis=analysis,
        status=status,
        blocking_issues=blocking,
        advisory_issues=advisory,
        note=(
            "required metadata is present; scientific suitability is not assessed"
            if not blocking
            else f"{len(blocking)} finding(s) prevent this assessment from passing"
        ),
    )
