"""Deterministic clinical risk triage engine orchestrator."""

from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional, Set

from .evaluator import ConditionEvaluator
from .gates import GateEvaluator
from .loader import SchemaRegistry, load_pathways, load_rules, load_schema
from .models import (
    MissingInputItem,
    ReasonItem,
    Rule,
    TriageMetadata,
    TriageResult,
    TriageStatus,
    TriState,
    UrgencyColour,
    UrgencyLevel,
    UrgencyOutput,
)
from .pathways import PathwayRunner, PathwayTraversalResult


class TriageEngine:
    """Core deterministic risk triage engine."""

    def __init__(
        self,
        schema: Optional[SchemaRegistry] = None,
        rules: Optional[List[Rule]] = None,
        pathway_runner: Optional[PathwayRunner] = None,
        candidate_rules_enabled: bool = False,
        rf006_policy: Optional[str] = None,  # None (unresolved DEC-03 pending doctor approval), 'clinic_visit', or 'emergency'
        rf005_policy: Optional[str] = None,  # None (unresolved DEC-02 pending doctor approval), 'single_marker_emergency', or 'combination_required'
    ):
        self.schema = schema or load_schema()
        self.rules = rules if rules is not None else load_rules(schema=self.schema)
        self.candidate_rules_enabled = candidate_rules_enabled
        self.rf006_policy = rf006_policy
        self.rf005_policy = rf005_policy

        if pathway_runner is not None:
            self.pathway_runner = pathway_runner
        else:
            raw_pathways = load_pathways()
            self.pathway_runner = PathwayRunner(
                raw_pathways, candidate_rules_enabled=self.candidate_rules_enabled
            )

        self.rules_by_id = {r.id: r for r in self.rules}

    def evaluate(self, raw_patient_inputs: Dict[str, Any]) -> TriageResult:
        """
        Executes the 4-step triage sequence:
          Step 0: Normalize & evaluate Gates/Derived Variables
          Step 1: Check Red Flags (enforce Red lock-in)
          Step 2: Check Scope Gate
          Step 3: Run Decision Pathways & Standalone Rules
          Step 4: Resolve Highest Urgency & Assemble Result
        """
        # Step 0: Normalize patient inputs against schema
        context = self.schema.normalize_patient_payload(raw_patient_inputs)

        # Compute derived variables and gates
        derived_vars, gate_explanations = GateEvaluator.evaluate_all(context)
        context.update(derived_vars)

        evaluated_gates = list(gate_explanations.keys())
        fired_rules: List[str] = []
        pending_decisions: List[str] = []
        deferred_pathways: List[Dict[str, Any]] = []
        candidate_rules_matched: List[str] = []
        matching_rules: List[Rule] = []
        effective_levels: Dict[str, UrgencyLevel] = {}
        missing_inputs_set: Set[str] = set()

        # Step 1: Check Red Flags first (RF-001..RF-008 + RF-009)
        red_flag_rules = [r for r in self.rules if r.domain in ["red_flags", "red_flag"]]

        for rule in red_flag_rules:
            # Handle candidate gap rules (RF-009, EP-001)
            if rule.is_candidate_rule and not self.candidate_rules_enabled:
                app_state, _ = ConditionEvaluator.evaluate(rule.when, context)
                if app_state == TriState.TRUE:
                    candidate_rules_matched.append(rule.id)
                    pending_decisions.append("DEC-08")
                continue

            # Special Clinical Governance Policy handling for RF-005 (DEC-02)
            if rule.id == "RF-005":
                if self.rf005_policy is None:
                    # Unresolved policy
                    app_state, _ = ConditionEvaluator.evaluate(rule.when, context)
                    if app_state == TriState.TRUE:
                        pending_decisions.append("DEC-02")
                        return TriageResult(
                            status=TriageStatus.CLINICAL_DECISION_REQUIRED,
                            urgency=UrgencyOutput(
                                level=UrgencyLevel.NONE,
                                colour=UrgencyColour.NONE,
                                needs_doctor_review=False,
                                needs_physical_exam=False,
                            ),
                            reasons=[ReasonItem(rule="RF-005", text="Severe pelvic infection presentation requires clinical governance policy selection (single marker vs combination per DEC-02).")],
                            advice="Clinical policy decision required for pelvic infection severity mapping.",
                            metadata=TriageMetadata(
                                fired_rules=["RF-005"],
                                evaluated_gates=evaluated_gates,
                                pending_clinical_decisions=["DEC-02"],
                            ),
                        )
                elif self.rf005_policy == "combination_required":
                    # Require measured high fever AND prostration/vomiting
                    p28 = context.get("fever_over_38_5c")
                    p30 = context.get("feels_severely_unwell")
                    p31 = context.get("persistent_vomiting_cannot_keep_fluids_down")
                    p20 = context.get("pelvic_pain_any")
                    if p20 == "yes" and p28 == "yes" and (p30 == "yes" or p31 == "yes"):
                        matching_rules.append(rule)
                        fired_rules.append(rule.id)
                        effective_levels[rule.id] = UrgencyLevel.EMERGENCY
                    continue

            # Special Clinical Governance Policy handling for RF-006 (DEC-03)
            if rule.id == "RF-006":
                if self.rf006_policy is None:
                    app_state, _ = ConditionEvaluator.evaluate(rule.when, context)
                    if app_state == TriState.TRUE:
                        pending_decisions.append("DEC-03")
                        return TriageResult(
                            status=TriageStatus.CLINICAL_DECISION_REQUIRED,
                            urgency=UrgencyOutput(
                                level=UrgencyLevel.NONE,
                                colour=UrgencyColour.NONE,
                                needs_doctor_review=False,
                                needs_physical_exam=False,
                            ),
                            reasons=[ReasonItem(rule="RF-006", text="Confirmed early pregnancy with bleeding and pain requires clinical policy selection (NICE EPAS Amber vs Indian Casualty Red per DEC-03).")],
                            advice="Early pregnancy pain and bleeding policy selection pending doctor review.",
                            metadata=TriageMetadata(
                                fired_rules=["RF-006"],
                                evaluated_gates=evaluated_gates,
                                pending_clinical_decisions=["DEC-03"],
                            ),
                        )
                elif self.rf006_policy == "emergency":
                    app_state, missing = ConditionEvaluator.evaluate(rule.when, context)
                    if app_state == TriState.TRUE:
                        matching_rules.append(rule)
                        fired_rules.append(rule.id)
                        effective_levels[rule.id] = UrgencyLevel.EMERGENCY
                    elif app_state == TriState.UNKNOWN:
                        missing_inputs_set.update(missing)
                    continue

            # Standard Red Flag evaluation
            app_state, missing = ConditionEvaluator.evaluate(rule.when, context)
            if app_state == TriState.TRUE:
                matching_rules.append(rule)
                fired_rules.append(rule.id)
                effective_levels[rule.id] = rule.level
                if rule.pending_clinical_decision:
                    pending_decisions.append(rule.pending_clinical_decision)
            elif app_state == TriState.UNKNOWN:
                missing_inputs_set.update(missing)

        # Check if an Emergency Red rule fired -> RED LOCK-IN
        has_red = any(effective_levels.get(r.id) == UrgencyLevel.EMERGENCY for r in matching_rules)
        if has_red:
            return self._build_result(
                status=TriageStatus.COMPLETE,
                highest_level=UrgencyLevel.EMERGENCY,
                matching_rules=[r for r in matching_rules if effective_levels.get(r.id) == UrgencyLevel.EMERGENCY],
                effective_levels=effective_levels,
                missing_inputs=set(),  # Red lock-in is not held back by non-critical missing inputs
                evaluated_gates=evaluated_gates,
                pending_decisions=pending_decisions,
                deferred_pathways=[],
                candidate_rules_matched=candidate_rules_matched,
            )

        # If acute non-pregnant pain matched candidate RF-009 while disabled:
        if "RF-009" in candidate_rules_matched:
            return TriageResult(
                status=TriageStatus.CLINICAL_DECISION_REQUIRED,
                urgency=UrgencyOutput(
                    level=UrgencyLevel.NONE,
                    colour=UrgencyColour.NONE,
                    needs_doctor_review=False,
                    needs_physical_exam=False,
                ),
                reasons=[ReasonItem(rule="RF-009", text="Acute severe pelvic pain with pregnancy excluded matches candidate gap rule RF-009 awaiting doctor approval under DEC-08.")],
                advice="Acute severe pelvic pain requires urgent in-person evaluation to rule out acute abdominal emergencies.",
                metadata=TriageMetadata(
                    fired_rules=["RF-009"],
                    evaluated_gates=evaluated_gates,
                    pending_clinical_decisions=["DEC-08"],
                    candidate_rules_matched=["RF-009"],
                ),
            )

        # Step 2: Demographic boundary check (GATE-002 / D2)
        age_cohort = context.get("age_cohort")
        if age_cohort == "out_of_scope":
            age_val = context.get("age")
            return TriageResult(
                status=TriageStatus.OUT_OF_SCOPE,
                urgency=UrgencyOutput(
                    level=UrgencyLevel.NONE,
                    colour=UrgencyColour.NONE,
                    needs_doctor_review=False,
                    needs_physical_exam=False,
                ),
                reasons=[ReasonItem(rule="GATE-002", text=f"Patient age {age_val} is outside reproductive target scope (18 to 40 years).")],
                advice="This triage system is calibrated specifically for reproductive-aged women aged 18 to 40 years. Please consult a qualified doctor for age-appropriate evaluation.",
                metadata=TriageMetadata(
                    fired_rules=[],
                    evaluated_gates=evaluated_gates,
                    pending_clinical_decisions=[],
                ),
            )

        # Step 3: Run Decision Pathways (PATH-AMEN-01, PATH-HMB-01)
        pathway_results = self.pathway_runner.run_applicable_pathways(context)
        for pw_res in pathway_results:
            if pw_res.status == TriageStatus.NEED_MORE_INFO:
                missing_inputs_set.update(pw_res.missing_inputs)

            if pw_res.status == TriageStatus.CLINICAL_DECISION_REQUIRED:
                if pw_res.pending_decision:
                    pending_decisions.append(pw_res.pending_decision)
                if pw_res.special_terminal_id:
                    candidate_rules_matched.append(pw_res.special_terminal_id)
                return TriageResult(
                    status=TriageStatus.CLINICAL_DECISION_REQUIRED,
                    urgency=UrgencyOutput(
                        level=UrgencyLevel.NONE,
                        colour=UrgencyColour.NONE,
                        needs_doctor_review=False,
                        needs_physical_exam=False,
                    ),
                    reasons=[ReasonItem(rule=pw_res.special_terminal_id or pw_res.pathway_id, text=pw_res.notes or "Clinical decision required.")],
                    advice="Clinical mapping pending medical governance approval.",
                    metadata=TriageMetadata(
                        fired_rules=[pw_res.special_terminal_id] if pw_res.special_terminal_id else [],
                        evaluated_gates=evaluated_gates,
                        pending_clinical_decisions=pending_decisions,
                        candidate_rules_matched=candidate_rules_matched,
                    ),
                )

            if pw_res.status == TriageStatus.DEFERRED:
                if pw_res.deferred_pathway:
                    deferred_pathways.append(pw_res.deferred_pathway)

            if pw_res.terminal_rule_id and pw_res.terminal_rule_id in self.rules_by_id:
                term_rule = self.rules_by_id[pw_res.terminal_rule_id]
                if term_rule not in matching_rules:
                    matching_rules.append(term_rule)
                    fired_rules.append(term_rule.id)
                    effective_levels[term_rule.id] = term_rule.level

        # Step 4: Evaluate Standalone Rules (IRR-001..IRR-013)
        domain_rules = [r for r in self.rules if r.domain in ["irregular_periods", "general"]]

        for rule in domain_rules:
            app_state, missing = ConditionEvaluator.evaluate(rule.when, context)
            if app_state == TriState.TRUE:
                # Check for conditional escalation (e.g. IRR-012)
                level = rule.level
                if rule.conditional_escalation:
                    esc_state, _ = ConditionEvaluator.evaluate(rule.conditional_escalation.when, context)
                    if esc_state == TriState.TRUE:
                        level = rule.conditional_escalation.escalate_to

                if rule not in matching_rules:
                    matching_rules.append(rule)
                    fired_rules.append(rule.id)
                effective_levels[rule.id] = level
            elif app_state == TriState.UNKNOWN:
                missing_inputs_set.update(missing)

        # Step 5: Resolve Highest Clinical Urgency
        if not matching_rules:
            # If no rules matched and there are missing inputs or deferred pathways
            if deferred_pathways:
                return TriageResult(
                    status=TriageStatus.DEFERRED,
                    urgency=UrgencyOutput(
                        level=UrgencyLevel.NONE,
                        colour=UrgencyColour.NONE,
                        needs_doctor_review=False,
                        needs_physical_exam=False,
                    ),
                    reasons=[ReasonItem(rule=d.get("source_pathway", "PATHWAY"), text=d.get("reason", "Deferred")) for d in deferred_pathways],
                    advice="Symptom evaluation requires specialized topic assessment scheduled for Day 4 (PCOS/Endometriosis/Fertility).",
                    metadata=TriageMetadata(
                        fired_rules=[],
                        evaluated_gates=evaluated_gates,
                        deferred_pathways=deferred_pathways,
                    ),
                )

            status = TriageStatus.NEED_MORE_INFO if missing_inputs_set else TriageStatus.COMPLETE
            return self._build_result(
                status=status,
                highest_level=UrgencyLevel.NONE,
                matching_rules=[],
                effective_levels={},
                missing_inputs=missing_inputs_set,
                evaluated_gates=evaluated_gates,
                pending_decisions=pending_decisions,
                deferred_pathways=deferred_pathways,
                candidate_rules_matched=candidate_rules_matched,
            )

        # Sort matching rules by effective urgency rank (highest first)
        matching_rules.sort(key=lambda r: effective_levels.get(r.id, UrgencyLevel.NONE).rank, reverse=True)
        highest_rule = matching_rules[0]
        highest_level = effective_levels[highest_rule.id]

        # Safety Check: Strict Green Lockout
        # Green (SELF_CARE) can NEVER be issued if any required field is unknown
        if highest_level == UrgencyLevel.SELF_CARE:
            if missing_inputs_set or any(context.get(k) == "unknown" for k in ["never_had_period", "cycle_length_days", "bleeding_duration_days", "self_reported_heavy_flow"]):
                return self._build_result(
                    status=TriageStatus.NEED_MORE_INFO,
                    highest_level=UrgencyLevel.NONE,
                    matching_rules=[],
                    effective_levels={},
                    missing_inputs=missing_inputs_set or {"cycle_length_days"},
                    evaluated_gates=evaluated_gates,
                    pending_decisions=pending_decisions,
                    deferred_pathways=deferred_pathways,
                    candidate_rules_matched=candidate_rules_matched,
                )

        # If a higher urgency rule matched (e.g. Amber or Yellow), but gating was missing
        status = TriageStatus.COMPLETE
        if missing_inputs_set and highest_level not in [UrgencyLevel.EMERGENCY, UrgencyLevel.CLINIC_VISIT]:
            # Critical gating check: if pregnancy_excluded is unknown for secondary amenorrhea
            if context.get("pregnancy_excluded") == "unknown" and any(r.id == "IRR-004" for r in matching_rules):
                return self._build_result(
                    status=TriageStatus.NEED_MORE_INFO,
                    highest_level=UrgencyLevel.NONE,
                    matching_rules=[],
                    effective_levels={},
                    missing_inputs={"pregnancy_test_result", "days_since_last_unprotected_sex"},
                    evaluated_gates=evaluated_gates,
                    pending_decisions=pending_decisions,
                    deferred_pathways=deferred_pathways,
                    candidate_rules_matched=candidate_rules_matched,
                )

        return self._build_result(
            status=status,
            highest_level=highest_level,
            matching_rules=matching_rules,
            effective_levels=effective_levels,
            missing_inputs=missing_inputs_set if status == TriageStatus.NEED_MORE_INFO else set(),
            evaluated_gates=evaluated_gates,
            pending_decisions=pending_decisions,
            deferred_pathways=deferred_pathways,
            candidate_rules_matched=candidate_rules_matched,
        )

    def _build_result(
        self,
        status: TriageStatus,
        highest_level: UrgencyLevel,
        matching_rules: List[Rule],
        effective_levels: Dict[str, UrgencyLevel],
        missing_inputs: Set[str],
        evaluated_gates: List[str],
        pending_decisions: List[str],
        deferred_pathways: List[Dict[str, Any]],
        candidate_rules_matched: List[str],
    ) -> TriageResult:
        reasons: List[ReasonItem] = []
        doctor_suggest_set: Set[str] = set()
        safety_net_set: Set[str] = set()
        fired_ids: List[str] = []
        primary_advice = ""
        needs_exam = False
        exam_reasons: List[str] = []

        for r in matching_rules:
            fired_ids.append(r.id)
            reasons.append(ReasonItem(rule=r.id, text=r.reason))
            for sug in r.doctor_may_suggest:
                doctor_suggest_set.add(sug)
            for sn in r.safety_net:
                safety_net_set.add(sn)

            # Exam requirement
            rule_eff_level = effective_levels.get(r.id, r.level)
            if rule_eff_level in [UrgencyLevel.CLINIC_VISIT, UrgencyLevel.EMERGENCY]:
                needs_exam = True
                if r.conditional_escalation and rule_eff_level == r.conditional_escalation.escalate_to:
                    if r.conditional_escalation.physical_exam_reason:
                        exam_reasons.append(r.conditional_escalation.physical_exam_reason)
                elif r.physical_exam_reason:
                    exam_reasons.append(r.physical_exam_reason)

            if not primary_advice and r.advice:
                primary_advice = r.advice

        # Format missing inputs
        missing_items: List[MissingInputItem] = []
        for f in sorted(missing_inputs):
            ask = self.schema.get_question_prompt(f)
            missing_items.append(MissingInputItem(field=f, ask=ask))

        if not primary_advice:
            if status == TriageStatus.NEED_MORE_INFO:
                primary_advice = "To give you accurate guidance, please answer the follow-up questions."
            elif highest_level == UrgencyLevel.NONE:
                primary_advice = "Please consult a healthcare professional for clinical advice."

        needs_review = highest_level in [UrgencyLevel.EMERGENCY, UrgencyLevel.CLINIC_VISIT, UrgencyLevel.TELECONSULTATION]

        urgency_out = UrgencyOutput(
            level=highest_level,
            colour=highest_level.colour,
            needs_doctor_review=needs_review,
            needs_physical_exam=needs_exam,
            physical_exam_reason="; ".join(exam_reasons) if exam_reasons else None,
        )

        return TriageResult(
            status=status,
            urgency=urgency_out,
            reasons=reasons,
            advice=primary_advice,
            doctor_may_suggest=sorted(list(doctor_suggest_set)),
            safety_net=sorted(list(safety_net_set)),
            missing_inputs=missing_items,
            metadata=TriageMetadata(
                fired_rules=fired_ids,
                evaluated_gates=evaluated_gates,
                pending_clinical_decisions=sorted(list(set(pending_decisions))),
                deferred_pathways=deferred_pathways,
                candidate_rules_matched=candidate_rules_matched,
            ),
        )

