"""YAML schema and rule loaders with strict validation."""

from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .models import (
    ApprovalStatus,
    ConditionalEscalation,
    EvidenceStatus,
    Pathway,
    PathwayStep,
    Rule,
    SourceCitation,
    UrgencyLevel,
)


class SchemaValidationError(Exception):
    """Raised when an input or rule violates the schema."""


class SchemaRegistry:
    """Manages input definitions and variable validation."""

    def __init__(self, schema_data: Dict[str, Any]):
        self.raw_schema = schema_data
        self.patient_inputs_by_id: Dict[str, Dict[str, Any]] = {}
        self.patient_inputs_by_name: Dict[str, Dict[str, Any]] = {}
        self.derived_variables_by_id: Dict[str, Dict[str, Any]] = {}
        self.derived_variables_by_name: Dict[str, Dict[str, Any]] = {}
        self._index_variables()

    def _index_variables(self) -> None:
        for p in self.raw_schema.get("patient_inputs", []):
            p_id = p.get("id")
            name = p.get("name")
            if p_id:
                self.patient_inputs_by_id[p_id] = p
            if name:
                self.patient_inputs_by_name[name] = p

        for d in self.raw_schema.get("derived_variables", []):
            d_id = d.get("id")
            name = d.get("name")
            if d_id:
                self.derived_variables_by_id[d_id] = d
            if name:
                self.derived_variables_by_name[name] = d

    def is_valid_variable(self, field_name: str) -> bool:
        return (
            field_name in self.patient_inputs_by_name
            or field_name in self.patient_inputs_by_id
            or field_name in self.derived_variables_by_name
            or field_name in self.derived_variables_by_id
        )

    FIELD_ALIASES = {
        "rapid_virilization": "rapid_virilization_signs",
        "hirsutism_excessive_hair": "excess_facial_or_body_hair",
        "moderate_severe_cystic_acne": "severe_or_persistent_acne",
        "male_pattern_alopecia": "scalp_hair_thinning",
        "significant_recent_weight_loss_or_intensive_exercise": "significant_weight_loss_or_heavy_training",
        "infant_age_months": "postpartum_delivery_timing",
        "hourly_pad_soaking_more_than_2_hours": "soaking_pad_hourly_2plus_hours",
        "bleeding_soaks_pad_hourly": "soaking_pad_hourly_2plus_hours",
        "syncope_or_near_fainting": "fainting_or_near_fainting",
        "severe_lower_abdominal_pain": "acute_severe_pelvic_pain",
        "fever_with_pelvic_pain": "fever_over_38_5c",
        "acute_severe_pain_with_vomiting": "sudden_pain_with_vomiting",
        "postpartum_heavy_bleeding_with_fever": "postpartum_heavy_or_increasing_bleeding_or_clots",
        "secondary_pph_bleeding": "postpartum_heavy_or_increasing_bleeding_or_clots",
        "typical_cycle_length_days": "cycle_length_days",
        "periods_in_past_year": "cycles_per_year",
        "pelvic_mass_or_fullness": "palpable_pelvic_lump",
    }

    def get_canonical_name(self, key: str) -> str:
        key = self.FIELD_ALIASES.get(key, key)
        if key in self.patient_inputs_by_id:
            return self.patient_inputs_by_id[key]["name"]
        if key in self.derived_variables_by_id:
            return self.derived_variables_by_id[key]["name"]
        return key

    def get_question_prompt(self, field_name: str) -> str:
        var = self.patient_inputs_by_name.get(field_name) or self.patient_inputs_by_id.get(field_name)
        if var:
            return var.get("ask") or var.get("description") or f"Please provide {field_name}."
        d_var = self.derived_variables_by_name.get(field_name) or self.derived_variables_by_id.get(field_name)
        if d_var:
            return d_var.get("description") or f"Please confirm {field_name}."
        return f"Please provide {field_name}."

    def normalize_patient_payload(self, raw_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Maps IDs to names, ensures missing inputs default to 'unknown'."""
        normalized: Dict[str, Any] = {}

        # Sort keys so that canonical schema keys run AFTER alias keys (canonical values win)
        sorted_keys = sorted(
            raw_inputs.keys(),
            key=lambda k: 1 if (k in self.patient_inputs_by_name or k in self.patient_inputs_by_id) else 0
        )

        for k in sorted_keys:
            v = raw_inputs[k]
            canonical = self.get_canonical_name(k)
            # Normalize None or empty string to 'unknown'
            if v is None or v == "":
                val = "unknown"
            elif isinstance(v, bool):
                val = "yes" if v else "no"
            else:
                val = v

            # If canonical is already set by a direct canonical key, do not overwrite with an alias
            if canonical in normalized and canonical in raw_inputs and k != canonical:
                continue

            normalized[canonical] = val
            normalized[k] = val

            # Also store under ID if k was name, or name if k was ID
            if k in self.patient_inputs_by_name:
                p_id = self.patient_inputs_by_name[k].get("id")
                if p_id:
                    normalized[p_id] = val
            elif k in self.patient_inputs_by_id:
                name = self.patient_inputs_by_id[k].get("name")
                if name:
                    normalized[name] = val

        # For any registered patient input missing from payload, mark as 'unknown'
        for name, meta in self.patient_inputs_by_name.items():
            if name not in normalized:
                normalized[name] = "unknown"
                p_id = meta.get("id")
                if p_id and p_id not in normalized:
                    normalized[p_id] = "unknown"

        # Populate known aliases so legacy/pathway alias references match canonical values
        for alias, canonical in self.FIELD_ALIASES.items():
            if canonical in normalized and alias not in normalized:
                normalized[alias] = normalized[canonical]

        return normalized


def load_schema(schema_path: Optional[pathlib.Path] = None) -> SchemaRegistry:
    if schema_path is None:
        schema_path = pathlib.Path(__file__).parent.parent / "rules" / "inputs_schema.yaml"
    if not schema_path.exists():
        # Fallback to research folder if needed
        fallback = pathlib.Path(__file__).parent.parent.parent.parent / "not to be committed" / "inputs.yaml"
        if fallback.exists():
            schema_path = fallback

    with open(schema_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SchemaRegistry(data)


def parse_urgency_level(level_str: str) -> UrgencyLevel:
    clean = level_str.strip().lower()
    mapping = {
        "emergency": UrgencyLevel.EMERGENCY,
        "red": UrgencyLevel.EMERGENCY,
        "clinic_visit": UrgencyLevel.CLINIC_VISIT,
        "amber": UrgencyLevel.CLINIC_VISIT,
        "teleconsultation": UrgencyLevel.TELECONSULTATION,
        "yellow": UrgencyLevel.TELECONSULTATION,
        "self_care": UrgencyLevel.SELF_CARE,
        "green": UrgencyLevel.SELF_CARE,
        "none": UrgencyLevel.NONE,
    }
    return mapping.get(clean, UrgencyLevel.NONE)


def load_rules(rules_path: Optional[pathlib.Path] = None, schema: Optional[SchemaRegistry] = None) -> List[Rule]:
    if rules_path is None:
        rules_path = pathlib.Path(__file__).parent.parent / "rules" / "rules.yaml"

    if not rules_path.exists():
        return []

    with open(rules_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []

    rules: List[Rule] = []
    for item in data:
        # Check conditional escalation
        escalation = None
        if "conditional_escalation" in item and item["conditional_escalation"]:
            esc_data = item["conditional_escalation"]
            escalation = ConditionalEscalation(
                when=esc_data.get("when", {}),
                escalate_to=parse_urgency_level(esc_data.get("escalate_to", "clinic_visit")),
                needs_physical_exam=esc_data.get("needs_physical_exam", True),
                physical_exam_reason=esc_data.get("physical_exam_reason", ""),
            )

        # Source citation
        source = None
        if "source" in item and item["source"]:
            src_data = item["source"]
            ev_str = src_data.get("evidence_status", "evidence_located")
            appr_str = src_data.get("approval_status", "mapping_pending_doctor_approval")
            source = SourceCitation(
                name=src_data.get("name", ""),
                url=src_data.get("url", ""),
                section=src_data.get("section", ""),
                number_checked=src_data.get("number_checked", ""),
                date=src_data.get("date", ""),
                evidence_status=EvidenceStatus(ev_str) if ev_str in EvidenceStatus.__members__.values() else EvidenceStatus.EVIDENCE_LOCATED,
                approval_status=ApprovalStatus(appr_str) if appr_str in ApprovalStatus.__members__.values() else ApprovalStatus.MAPPING_PENDING_DOCTOR_APPROVAL,
            )

        level_str = item.get("level") or item.get("base_level") or "none"
        rule = Rule(
            id=item["id"],
            domain=item.get("domain", "general"),
            name=item.get("name", item["id"]),
            when=item.get("when", {}),
            level=parse_urgency_level(level_str),
            needs_physical_exam=item.get("needs_physical_exam", False),
            physical_exam_reason=item.get("physical_exam_reason"),
            reason=item.get("reason", ""),
            advice=item.get("advice", ""),
            doctor_may_suggest=item.get("doctor_may_suggest", []),
            safety_net=item.get("safety_net", []),
            conditional_escalation=escalation,
            is_candidate_rule=item.get("is_candidate_rule", False),
            is_proposed_mapping=item.get("is_proposed_mapping", False),
            pending_clinical_decision=item.get("pending_clinical_decision"),
            proposed_levels=item.get("proposed_levels"),
            source=source,
        )
        rules.append(rule)

    return rules


def load_pathways(pathways_path: Optional[pathlib.Path] = None) -> List[Pathway]:
    if pathways_path is None:
        pathways_path = pathlib.Path(__file__).parent.parent / "rules" / "pathways.yaml"

    if not pathways_path.exists():
        return []

    with open(pathways_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []

    pathways: List[Pathway] = []
    for item in data:
        steps: List[PathwayStep] = []
        for s in item.get("steps", []):
            step = PathwayStep(
                id=s["id"],
                question=s.get("question", ""),
                condition=s.get("condition"),
                if_true=s.get("if_true"),
                if_false=s.get("if_false"),
                if_unknown=s.get("if_unknown"),
                deferred_pathway=s.get("deferred_pathway"),
                terminal_rule_id=s.get("terminal_rule_id"),
                terminal_type=s.get("terminal_type"),
                decision=s.get("decision"),
                ask_next=s.get("ask_next"),
            )
            steps.append(step)

        pathway = Pathway(
            id=item["id"],
            name=item.get("name", item["id"]),
            starts_when=item.get("starts_when", {}),
            steps=steps,
        )
        pathways.append(pathway)

    return pathways
