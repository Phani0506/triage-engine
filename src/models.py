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
    proposed_mappings_matched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fired_rules": self.fired_rules,
            "evaluated_gates": self.evaluated_gates,
            "pending_clinical_decisions": self.pending_clinical_decisions,
            "deferred_pathways": self.deferred_pathways,
            "candidate_rules_matched": self.candidate_rules_matched,
            "proposed_mappings_matched": self.proposed_mappings_matched,
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
    is_proposed_mapping: bool = False
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
    terminal_type: Optional[str] = None
    decision: Optional[str] = None
    ask_next: Optional[List[str]] = None


@dataclass
class Pathway:
    id: str
    name: str
    starts_when: Dict[str, Any]
    steps: List[PathwayStep]


@dataclass
class OracleExpectation:
    expected_level: str  # emergency, clinic_visit, teleconsultation, self_care, none
    expected_colour: str  # red, amber, yellow, green, none
    expected_status: str  # complete, need_more_info, clinical_decision_required, out_of_scope
    expected_rule_ids: List[str] = field(default_factory=list)
    expected_reasons: List[str] = field(default_factory=list)
    oracle_source_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_level": self.expected_level,
            "expected_colour": self.expected_colour,
            "expected_status": self.expected_status,
            "expected_rule_ids": self.expected_rule_ids,
            "expected_reasons": self.expected_reasons,
            "oracle_source_note": self.oracle_source_note,
        }


@dataclass
class SyntheticCase:
    case_id: str
    collection: str  # 'practice' or 'exam'
    topic: str  # 'red_flags', 'irregular_periods', 'pcos', 'endometriosis', 'fertility', 'multi_topic'
    difficulty: str  # 'normal', 'borderline', 'complicated', 'high_risk', 'missing_info'
    patient_summary_lines: List[str]
    patient_inputs: Dict[str, Any]
    missing_or_unknown_fields: List[str] = field(default_factory=list)
    oracle: Optional[OracleExpectation] = None
    batch_id: Optional[str] = None
    case_sha256: str = ""
    synthetic: bool = True

    def to_dict(self, include_oracle: bool = True) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "case_id": self.case_id,
            "collection": self.collection,
            "batch_id": self.batch_id,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "patient_summary_lines": self.patient_summary_lines,
            "patient_inputs": self.patient_inputs,
            "missing_or_unknown_fields": self.missing_or_unknown_fields,
            "case_sha256": self.case_sha256,
            "synthetic": self.synthetic,
        }
        if include_oracle and self.oracle:
            d["oracle"] = self.oracle.to_dict()
        return d


@dataclass
class DoctorReviewRecord:
    review_id: str
    case_id: str
    case_type: str  # 'practice', 'exam'
    batch_id: str
    doctor_name: str
    patient_data_json: str
    doctor_level: str
    doctor_colour: str
    doctor_initial_notes: Optional[str]
    engine_output_json: str
    engine_level: str
    engine_colour: str
    fired_rule_ids_json: str
    engine_version: str
    rule_set_version: str
    agreement_status: str  # 'same', 'engine_higher', 'engine_lower'
    verdict: Optional[str] = None  # 'doctor_is_right', 'engine_is_right', 'both_fine'
    problem_chips_json: Optional[str] = None
    doctor_feedback_text: Optional[str] = None
    correction_request: Optional[str] = None
    review_status: str = "assessed"  # 'assessed', 'feedback_complete'
    submitted_at: str = ""


