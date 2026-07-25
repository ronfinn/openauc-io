"""Validation findings, reports, and the validation entry points.

Validation in ``openauc`` is **tiered**. Four independent questions are asked of
an experiment (see :class:`~openauc.models.enums.ValidationTier`):

* ``ARCHIVAL`` — can it be stored and returned unchanged and unambiguously?
* ``STRUCTURAL`` — are metadata, scans and observations internally consistent?
* ``SV_READINESS`` / ``SE_READINESS`` — is the metadata a future
  sedimentation-velocity or sedimentation-equilibrium workflow needs present?

A fifth question — whether the data are *scientifically* valid or suitable — is
**never answered**. It is not a tier; it is reported permanently as
``NOT_ASSESSED`` by :mod:`openauc.models.readiness`.

Validation is deterministic and explainable: checks run in a fixed order, every
finding carries a stable code and a stated expectation, and no machine learning,
heuristic scientific interpretation or inference of any kind is involved. Field
level invariants (finiteness, non-negative time and wavelength, valid masks) are
enforced earlier still, at construction, and raise immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from openauc.exceptions import StructuralValidationError
from openauc.models.enums import ValidationSeverity, ValidationTier

if TYPE_CHECKING:
    from openauc.models.experiment import AUCExperiment

__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "validate_experiment",
    "validate_experiment_structure",
]

#: Tiers reported by :func:`validate_experiment_structure`.
_STRUCTURAL_TIERS = (ValidationTier.ARCHIVAL, ValidationTier.STRUCTURAL)

#: Severities reported by :func:`validate_experiment_structure`. Informational
#: findings are descriptive only and are available from
#: :func:`validate_experiment` instead, which keeps the historical content and
#: meaning of ``validate_structure()`` unchanged.
_STRUCTURAL_SEVERITIES = (ValidationSeverity.ERROR, ValidationSeverity.WARNING)


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding.

    Attributes:
        code: Stable identifier for the check that produced the finding.
        message: Human-readable statement of what was found.
        severity: See :class:`~openauc.models.enums.ValidationSeverity`.
        location: The single affected scan, sample or component, when exactly
            one is affected.
        tiers: The tier(s) the finding speaks to. Never empty.
        blocks: The tier(s) the finding prevents. A finding may pertain to a
            tier without blocking it.
        observed: What was actually found, rendered as text.
        expected: The condition that would have satisfied the check.
        remediation: A concrete suggestion for resolving the finding.
        component: The model field or component the finding concerns.
        scan_ids: Every affected scan identifier, sorted. One finding
            aggregates a condition across many scans rather than emitting one
            finding per scan.
    """

    code: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    location: str | None = None
    tiers: tuple[ValidationTier, ...] = (ValidationTier.STRUCTURAL,)
    blocks: tuple[ValidationTier, ...] = ()
    observed: str | None = None
    expected: str | None = None
    remediation: str | None = None
    component: str | None = None
    scan_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.tiers:
            raise ValueError("a ValidationIssue must name at least one tier")

    def __str__(self) -> str:
        where = f" [{self.location}]" if self.location else ""
        return f"{self.severity.value.upper()} {self.code}{where}: {self.message}"

    @property
    def tier(self) -> ValidationTier:
        """The primary (first-named) tier this finding speaks to."""
        return self.tiers[0]

    @property
    def blocks_structural_validity(self) -> bool:
        """True when this finding prevents structural validity.

        Equivalent to carrying ``ERROR`` severity: by the severity policy only
        errors may block the archival or structural tiers.
        """
        return self.severity is ValidationSeverity.ERROR

    def blocks_tier(self, tier: ValidationTier) -> bool:
        """True when this finding prevents ``tier``."""
        return tier in self.blocks

    def describe(self) -> str:
        """A multi-line rendering including observed/expected/remediation."""
        lines = [str(self)]
        details = (
            ("tiers", ", ".join(t.value for t in self.tiers)),
            ("blocks", ", ".join(t.value for t in self.blocks) or "nothing"),
            ("component", self.component),
            ("observed", self.observed),
            ("expected", self.expected),
            ("remediation", self.remediation),
            ("scans", ", ".join(self.scan_ids) if self.scan_ids else None),
        )
        lines.extend(f"    {label}: {value}" for label, value in details if value)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the finding to plain JSON-friendly Python types."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "location": self.location,
            "tiers": [t.value for t in self.tiers],
            "blocks": [t.value for t in self.blocks],
            "observed": self.observed,
            "expected": self.expected,
            "remediation": self.remediation,
            "component": self.component,
            "scan_ids": list(self.scan_ids),
        }


@dataclass(frozen=True)
class ValidationReport:
    """The result of validation: an ordered, deterministic list of findings."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """True when there are no ERROR-severity issues.

        This is a statement about **structural** validity only. It is never a
        claim that the data are scientifically valid or that any analysis is
        appropriate.
        """
        return not any(
            issue.severity is ValidationSeverity.ERROR for issue in self.issues
        )

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is ValidationSeverity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is ValidationSeverity.WARNING)

    @property
    def infos(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is ValidationSeverity.INFO)

    def counts(self) -> tuple[int, int, int]:
        """``(errors, warnings, infos)``."""
        return (len(self.errors), len(self.warnings), len(self.infos))

    def by_code(self, code: str) -> tuple[ValidationIssue, ...]:
        """Every finding carrying ``code``, in report order."""
        return tuple(i for i in self.issues if i.code == code)

    def codes(self) -> tuple[str, ...]:
        """Every finding's code, in report order (duplicates retained)."""
        return tuple(i.code for i in self.issues)

    def for_tiers(
        self,
        *tiers: ValidationTier,
        severities: tuple[ValidationSeverity, ...] | None = None,
    ) -> ValidationReport:
        """A report narrowed to findings pertaining to ``tiers``.

        Args:
            tiers: Keep a finding when any of its ``tiers`` is named here.
            severities: When given, additionally keep only these severities.
        """
        selected = tuple(
            issue
            for issue in self.issues
            if any(tier in tiers for tier in issue.tiers)
            and (severities is None or issue.severity in severities)
        )
        return ValidationReport(issues=selected)

    def blocking_for(self, tier: ValidationTier) -> tuple[ValidationIssue, ...]:
        """Every finding that prevents ``tier``."""
        return tuple(i for i in self.issues if i.blocks_tier(tier))

    def raise_if_invalid(self) -> None:
        """Raise :class:`StructuralValidationError` if any errors are present."""
        if not self.is_valid:
            raise StructuralValidationError(str(self))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the report to plain JSON-friendly Python types."""
        errors, warnings, infos = self.counts()
        return {
            "is_valid": self.is_valid,
            "counts": {"error": errors, "warning": warnings, "info": infos},
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def __str__(self) -> str:
        if not self.issues:
            return "structural validation: OK (no issues)"
        header = (
            f"structural validation: {'OK' if self.is_valid else 'FAILED'} "
            f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        return "\n".join([header, *(f"  - {issue}" for issue in self.issues)])


def validate_experiment(experiment: AUCExperiment) -> ValidationReport:
    """Run every check across all four tiers and return the full report.

    Findings are ordered by the fixed check registry; within a check, affected
    scans are sorted. Equivalent experiments therefore produce equivalent
    reports.
    """
    from openauc.models.checks import CHECKS

    issues: list[ValidationIssue] = []
    for check in CHECKS:
        issues.extend(check(experiment))
    return ValidationReport(issues=tuple(issues))


def validate_experiment_structure(experiment: AUCExperiment) -> ValidationReport:
    """Validate archival and structural consistency only.

    Returns the ``ARCHIVAL`` and ``STRUCTURAL`` findings of ``ERROR`` or
    ``WARNING`` severity. Readiness findings and purely informational findings
    are reported by :func:`validate_experiment` instead. This is a
    representational check; it makes no scientific judgement.
    """
    return validate_experiment(experiment).for_tiers(
        *_STRUCTURAL_TIERS, severities=_STRUCTURAL_SEVERITIES
    )
