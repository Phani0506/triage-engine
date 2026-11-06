"""Decision tree runner with unknown safety routing, Day 4 deferrals, and candidate rule guards."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .evaluator import ConditionEvaluator
from .models import Pathway, PathwayStep, TriageStatus, TriState


class PathwayTraversalResult:
    def __init__(
        self,
        pathway_id: str,
        terminal_rule_id: Optional[str] = None,
        status: TriageStatus = TriageStatus.COMPLETE,
        missing_inputs: Optional[Set[str]] = None,
        deferred_pathway: Optional[Dict[str, Any]] = None,
        pending_decision: Optional[str] = None,
        special_terminal_id: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        self.pathway_id = pathway_id
        self.terminal_rule_id = terminal_rule_id
        self.status = status
        self.missing_inputs = missing_inputs or set()
        self.deferred_pathway = deferred_pathway
        self.pending_decision = pending_decision
        self.special_terminal_id = special_terminal_id
        self.notes = notes


class PathwayRunner:
    """Executes clinical decision pathways step-by-step."""

    def __init__(
        self,
        pathways: List[Pathway],
        candidate_rules_enabled: bool = False,
    ):
        self.pathways = {p.id: p for p in pathways}
        self.candidate_rules_enabled = candidate_rules_enabled

    def run_applicable_pathways(
        self, context: Dict[str, Any]
    ) -> List[PathwayTraversalResult]:
        """Finds all pathways whose starts_when matches and evaluates them."""
        results: List[PathwayTraversalResult] = []

        for p in self.pathways.values():
            app_state, _ = ConditionEvaluator.evaluate(p.starts_when, context)
            if app_state == TriState.TRUE:
                res = self.traverse(p, context)
                results.append(res)

        return results

    def traverse(self, pathway: Pathway, context: Dict[str, Any]) -> PathwayTraversalResult:
        """Walks a pathway step-by-step from step 0."""
        step_map: Dict[str, PathwayStep] = {s.id: s for s in pathway.steps}
        current_step_id = pathway.steps[0].id if pathway.steps else None

        while current_step_id:
            step = step_map.get(current_step_id)
            if not step:
                return PathwayTraversalResult(
                    pathway_id=pathway.id,
                    status=TriageStatus.CONFIGURATION_ERROR,
                    notes=f"Step ID '{current_step_id}' not found in pathway {pathway.id}.",
                )

            # Check if step has an explicit condition block
            if step.condition:
                eval_state, missing = ConditionEvaluator.evaluate(step.condition, context)
            else:
                eval_state = TriState.TRUE
                missing = set()

            # Determine next target based on 3-valued state
            if eval_state == TriState.TRUE:
                target = step.if_true
            elif eval_state == TriState.FALSE:
                target = step.if_false
            else:
                target = step.if_unknown

            # Process destination target
            if not target or target == "need_more_info":
                prompt_fields = set(step.ask_next or [])
                prompt_fields.update(missing)
                return PathwayTraversalResult(
                    pathway_id=pathway.id,
                    status=TriageStatus.NEED_MORE_INFO,
                    missing_inputs=prompt_fields,
                    notes=f"Pathway {pathway.id} step {step.id} requires missing information.",
                )

            # Check for candidate rule target guards
            if target in ["EP-001", "RF-009"] and not self.candidate_rules_enabled:
                return PathwayTraversalResult(
                    pathway_id=pathway.id,
                    status=TriageStatus.CLINICAL_DECISION_REQUIRED,
                    pending_decision="DEC-08",
                    special_terminal_id=target,
                    notes=f"Pathway reached candidate rule {target} which is inactive pending doctor approval (DEC-08).",
                )

            # Check for explicit deferred hooks (e.g. Day 4 PCOS deferrals)
            if target.startswith("PATH-PCOS") or target.startswith("DEFERRED"):
                target_path = target
                return PathwayTraversalResult(
                    pathway_id=pathway.id,
                    status=TriageStatus.DEFERRED,
                    deferred_pathway={
                        "step": step.id,
                        "source_pathway": pathway.id,
                        "target_pathway": target_path,
                        "reason": f"Topic evaluation deferred to {target_path} (Day 4 scope).",
                    },
                    notes=f"Deferred to {target_path}.",
                )

            # Check for explicit candidate terminals (e.g. single-cycle IMB, Age 35 DEC-09)
            if target == "PATH-HMB-01-TERM-IMB1":
                return PathwayTraversalResult(
                    pathway_id=pathway.id,
                    status=TriageStatus.CLINICAL_DECISION_REQUIRED,
                    pending_decision="DISC-IMB1",
                    special_terminal_id="PATH-HMB-01-TERM-IMB1",
                    notes="Isolated single-cycle intermenstrual spotting without heavy flow; clinical mapping pending doctor review.",
                )

            if target == "PATH-FERT-01-TERM-AGE35":
                decision_id = getattr(step, "decision", None) or "DEC-09"
                return PathwayTraversalResult(
                    pathway_id=pathway.id,
                    status=TriageStatus.CLINICAL_DECISION_REQUIRED,
                    pending_decision=decision_id,
                    special_terminal_id=target,
                    notes=f"Age 35 trying < 6 months requires clinical governance policy selection ({decision_id}).",
                )

            # Check if target is another step in this pathway
            if target in step_map:
                current_step_id = target
                continue

            # Otherwise, target is a terminal rule ID
            return PathwayTraversalResult(
                pathway_id=pathway.id,
                terminal_rule_id=target,
                status=TriageStatus.COMPLETE,
                notes=f"Completed at terminal rule {target}.",
            )

        return PathwayTraversalResult(
            pathway_id=pathway.id,
            status=TriageStatus.COMPLETE,
            notes="Pathway finished without explicit terminal rule.",
        )
