"""Core domain models, Enums, and JSON contracts for the Women's Health Triage Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class UrgencyLevel(str, Enum):
    """Clinical triage urgency rank: Emergency > Clinic Visit > Teleconsultation > Self Care."""
    EMERGENCY = "emergency"          # Level 4 (Red)
    CLINIC_VISIT = "clinic_visit"    # Level 3 (Amber)
    TELECONSULTATION = "teleconsultation"  # Level 2 (Yellow)
    SELF_CARE = "self_care"          # Level 1 (Green)
    NONE = "none"                    # No safe level established

    @property
    def rank(self) -> int:
        ranks = {
            UrgencyLevel.NONE: 0,
            UrgencyLevel.SELF_CARE: 1,
            UrgencyLevel.TELECONSULTATION: 2,
            UrgencyLevel.CLINIC_VISIT: 3,
            UrgencyLevel.EMERGENCY: 4,
        }
        return ranks[self]

    @property
    def colour(self) -> "UrgencyColour":
        colours = {
            UrgencyLevel.EMERGENCY: UrgencyColour.RED,
            UrgencyLevel.CLINIC_VISIT: UrgencyColour.AMBER,
            UrgencyLevel.TELECONSULTATION: UrgencyColour.YELLOW,
            UrgencyLevel.SELF_CARE: UrgencyColour.GREEN,
            UrgencyLevel.NONE: UrgencyColour.NONE,
        }
        return colours[self]


class UrgencyColour(str, Enum):
    RED = "red"
    AMBER = "amber"
    YELLOW = "yellow"
    GREEN = "green"
    NONE = "none"


class TriageStatus(str, Enum):
    """Operational processing status separated from clinical urgency."""
    COMPLETE = "complete"
    NEED_MORE_INFO = "need_more_info"
    OUT_OF_SCOPE = "out_of_scope"
    CLINICAL_DECISION_REQUIRED = "clinical_decision_required"
    DEFERRED = "deferred"
    CONFIGURATION_ERROR = "configuration_error"


class TriState(str, Enum):
    """Three-valued logic."""
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_bool(cls, b: Optional[bool]) -> "TriState":
        if b is True:
            return cls.TRUE
        if b is False:
            return cls.FALSE
        return cls.UNKNOWN

    def to_bool(self) -> Optional[bool]:
        if self == TriState.TRUE:
            return True
        if self == TriState.FALSE:
            return False
        return None


class EvidenceStatus(str, Enum):
    EVIDENCE_LOCATED = "evidence_located"
    SOURCE_VERIFIED = "source_verified"


class ApprovalStatus(str, Enum):
    MAPPING_PENDING_DOCTOR_APPROVAL = "mapping_pending_doctor_approval"
    DOCTOR_REVIEWED = "doctor_reviewed"
    APPROVED = "approved"


@dataclass
class UrgencyOutput:
    level: UrgencyLevel
    colour: UrgencyColour
    needs_doctor_review: bool
    needs_physical_exam: bool
    physical_exam_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "colour": self.colour.value,
            "needs_doctor_review": self.needs_doctor_review,
            "needs_physical_exam": self.needs_physical_exam,
            "physical_exam_reason": self.physical_exam_reason,
        }


@dataclass
class ReasonItem:
    rule: str
    text: str

    def to_dict(self) -> Dict[str, str]:
        return {"rule": self.rule, "text": self.text}


@dataclass
class MissingInputItem:
    field: str
    ask: str

    def to_dict(self) -> Dict[str, str]:
        return {"field": self.field, "ask": self.ask}


@dataclass
class TriageMetadata:
    fired_rules: List[str] = field(default_factory=list)
    evaluated_gates: List[str] = field(default_factory=list)
    pending_clinical_decisions: List[str] = field(default_factory=list)
    deferred_pathways: List[Dict[str, Any]] = field(default_factory=list)
    candidate_rules_matched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fired_rules": self.fired_rules,
            "evaluated_gates": self.evaluated_gates,
            "pending_clinical_decisions": self.pending_clinical_decisions,
            "deferred_pathways": self.deferred_pathways,
            "candidate_rules_matched": self.candidate_rules_matched,
        }


@dataclass
class TriageResult:
    status: TriageStatus
    urgency: UrgencyOutput
    reasons: List[ReasonItem] = field(default_factory=list)
    advice: str = ""
    doctor_may_suggest: List[str] = field(default_factory=list)
    safety_net: List[str] = field(default_factory=list)
    missing_inputs: List[MissingInputItem] = field(default_factory=list)
    metadata: TriageMetadata = field(default_factory=TriageMetadata)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "urgency": self.urgency.to_dict(),
            "reasons": [r.to_dict() for r in self.reasons],
            "advice": self.advice,
            "doctor_may_suggest": self.doctor_may_suggest,
            "safety_net": self.safety_net,
            "missing_inputs": [m.to_dict() for m in self.missing_inputs],
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class SourceCitation:
    name: str
    url: str
    section: str
    number_checked: str
    date: str
    evidence_status: EvidenceStatus = EvidenceStatus.EVIDENCE_LOCATED
    approval_status: ApprovalStatus = ApprovalStatus.MAPPING_PENDING_DOCTOR_APPROVAL


@dataclass
class ConditionalEscalation:
    when: Dict[str, Any]
    escalate_to: UrgencyLevel
    needs_physical_exam: bool
    physical_exam_reason: str


@dataclass
class Rule:
    id: str
    domain: str
    name: str
    when: Dict[str, Any]
    level: UrgencyLevel
    needs_physical_exam: bool
    reason: str
    advice: str
    doctor_may_suggest: List[str] = field(default_factory=list)
    safety_net: List[str] = field(default_factory=list)
    physical_exam_reason: Optional[str] = None
    conditional_escalation: Optional[ConditionalEscalation] = None
    is_candidate_rule: bool = False
    pending_clinical_decision: Optional[str] = None
    proposed_levels: Optional[Dict[str, str]] = None
    source: Optional[SourceCitation] = None


@dataclass
class PathwayStep:
    id: str
    question: str
    condition: Optional[Dict[str, Any]] = None
    if_true: Optional[str] = None
    if_false: Optional[str] = None
    if_unknown: Optional[str] = None
    deferred_pathway: Optional[str] = None
    terminal_rule_id: Optional[str] = None
    ask_next: Optional[List[str]] = None


@dataclass
class Pathway:
    id: str
    name: str
    starts_when: Dict[str, Any]
    steps: List[PathwayStep]

