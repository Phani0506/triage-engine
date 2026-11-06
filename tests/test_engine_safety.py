"""Systemic safety invariants and governance tests for the triage engine."""

import unittest

from src.engine import TriageEngine
from src.loader import load_rules
from src.models import TriageStatus, UrgencyColour, UrgencyLevel


class TestEngineSafetyInvariants(unittest.TestCase):
    def setUp(self):
        self.engine = TriageEngine()
        self.rules = load_rules()

    def test_strict_green_lockout_on_missing_inputs(self):
        # A completely empty patient payload MUST NEVER receive Green
        empty_res = self.engine.evaluate({})
        self.assertNotEqual(empty_res.urgency.level, UrgencyLevel.SELF_CARE)
        self.assertNotEqual(empty_res.urgency.colour, UrgencyColour.GREEN)
        self.assertEqual(empty_res.status, TriageStatus.NEED_MORE_INFO)

        # A patient with normal cycle length but unknown red flags MUST NOT receive Green
        partial_res = self.engine.evaluate({
            "age": 25,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
        })
        self.assertNotEqual(partial_res.urgency.level, UrgencyLevel.SELF_CARE)
        self.assertNotEqual(partial_res.urgency.colour, UrgencyColour.GREEN)
        self.assertEqual(partial_res.status, TriageStatus.NEED_MORE_INFO)

    def test_red_lock_in_invariant(self):
        # Even when a Green or Yellow condition is technically true in other variables,
        # an Emergency Red trigger locks in the result and cannot be downgraded.
        patient = {
            "age": 28,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "soaking_pad_hourly_2plus_hours": "yes",
            "fainting_or_near_fainting": "yes",  # RF-003 / RF-004 trigger
            "self_reported_heavy_flow": "yes",  # IRR-005 trigger
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertEqual(res.urgency.colour, UrgencyColour.RED)
        self.assertIn("RF-003", res.metadata.fired_rules)

    def test_candidate_rules_inactive_by_default(self):
        # Ensure that RF-009 and EP-001 are marked as candidate rules
        candidate_ids = [r.id for r in self.rules if r.is_candidate_rule]
        self.assertIn("RF-009", candidate_ids)
        self.assertIn("EP-001", candidate_ids)

        # Default engine has candidate_rules_enabled = False
        self.assertFalse(self.engine.candidate_rules_enabled)

        # Matching a candidate condition without enable flag yields clinical_decision_required
        patient = {
            "age": 24,
            "acute_severe_pelvic_pain": "yes",
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.CLINICAL_DECISION_REQUIRED)
        self.assertEqual(res.urgency.level, UrgencyLevel.NONE)
        self.assertIn("DEC-08", res.metadata.pending_clinical_decisions)

    def test_non_prescriptive_patient_language_validator(self):
        # All advice strings across all loaded rules must avoid prescriptive diagnostic orders
        prohibited_phrases = [
            "you must have a pelvic exam",
            "you must take",
            "we diagnose you with",
            "you have endometriosis",
            "you have pcos",
            "take 500mg",
            "take amoxicillin",
            "you require a biopsy",
        ]

        for rule in self.rules:
            advice_lower = rule.advice.lower()
            for phrase in prohibited_phrases:
                self.assertNotIn(
                    phrase,
                    advice_lower,
                    f"Rule {rule.id} advice contains prohibited prescriptive phrase: '{phrase}'",
                )

    def test_separated_urgency_and_status_contract(self):
        # Verify JSON dictionary contract separates status and urgency
        patient = {
            "age": 25,
            "cycle_length_days": 28,
        }
        res_dict = self.engine.evaluate(patient).to_dict()
        self.assertIn("status", res_dict)
        self.assertIn("urgency", res_dict)
        self.assertIn("level", res_dict["urgency"])
        self.assertIn("colour", res_dict["urgency"])
        self.assertIn("reasons", res_dict)
        self.assertIn("missing_inputs", res_dict)
        self.assertIn("metadata", res_dict)


if __name__ == "__main__":
    unittest.main()

