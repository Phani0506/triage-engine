"""Unit and safety tests for Red Flags (RF-001..RF-008) and Candidates (RF-009)."""

import unittest

from src.engine import TriageEngine
from src.models import TriageStatus, UrgencyColour, UrgencyLevel


class TestRedFlags(unittest.TestCase):
    def setUp(self):
        self.engine = TriageEngine()

    def test_rf_001_acute_severe_pain_pregnancy_not_excluded(self):
        # Patient age 24 with sudden severe pain and pregnancy test not done (pregnancy not excluded)
        patient = {
            "age": 24,
            "acute_severe_pelvic_pain": "yes",
            "pregnancy_test_result": "not_done",
            "pregnancy_possible": "yes",
            "unprotected_sex_in_last_12_months": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.COMPLETE)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertEqual(res.urgency.colour, UrgencyColour.RED)
        self.assertIn("RF-001", res.metadata.fired_rules)

    def test_rf_002_shoulder_tip_pain(self):
        # Shoulder-tip pain with pelvic symptoms -> Emergency (Red)
        patient = {
            "age": 28,
            "shoulder_tip_pain": "yes",
            "pelvic_pain_any": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.COMPLETE)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-002", res.metadata.fired_rules)

    def test_rf_003_hourly_soaking_with_instability(self):
        # Bleeding soaking pad hourly for 2+ hours with resting tachycardia (instability proxy)
        patient = {
            "age": 30,
            "soaking_pad_hourly_2plus_hours": "yes",
            "racing_heartbeat_at_rest": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.COMPLETE)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-003", res.metadata.fired_rules)

    def test_rf_004_syncope_with_bleeding_or_pain(self):
        # Fainting/collapse with active bleeding
        patient = {
            "age": 26,
            "fainting_or_near_fainting": "yes",
            "vaginal_bleeding_now": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.COMPLETE)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-004", res.metadata.fired_rules)

    def test_rf_005_dec02_policy_handling(self):
        # Presentation: pelvic pain with high fever (> 38.5C)
        patient = {
            "age": 22,
            "pelvic_pain_any": "yes",
            "fever_over_38_5c": "yes",
            "feels_severely_unwell": "no",
            "persistent_vomiting_cannot_keep_fluids_down": "no",
        }

        # Policy 1: Default / Unresolved (None) -> Must NOT silently assign Red, must halt with clinical_decision_required
        engine_unresolved = TriageEngine(rf005_policy=None)
        res_unresolved = engine_unresolved.evaluate(patient)
        self.assertEqual(res_unresolved.status, TriageStatus.CLINICAL_DECISION_REQUIRED)
        self.assertEqual(res_unresolved.urgency.level, UrgencyLevel.NONE)
        self.assertIn("DEC-02", res_unresolved.metadata.pending_clinical_decisions)

        # Policy 2: Single marker emergency -> Fires Red
        engine_single = TriageEngine(rf005_policy="single_marker_emergency")
        res_single = engine_single.evaluate(patient)
        self.assertEqual(res_single.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-005", res_single.metadata.fired_rules)

        # Policy 3: Combination required -> Does not fire Red without prostration/vomiting
        engine_combo = TriageEngine(rf005_policy="combination_required")
        res_combo = engine_combo.evaluate(patient)
        self.assertNotIn("RF-005", res_combo.metadata.fired_rules)

        # But with fever + prostration, combo policy DOES fire Red:
        patient_combo = dict(patient)
        patient_combo["feels_severely_unwell"] = "yes"
        res_combo_active = engine_combo.evaluate(patient_combo)
        self.assertEqual(res_combo_active.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-005", res_combo_active.metadata.fired_rules)

    def test_rf_006_dec03_policy_handling(self):
        # Presentation: confirmed early pregnancy with bleeding and pelvic pain (hemodynamically stable)
        patient = {
            "age": 29,
            "pregnancy_test_result": "positive",
            "vaginal_bleeding_now": "yes",
            "pelvic_pain_any": "yes",
            "acute_severe_pelvic_pain": "no",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
        }

        # Policy 1: Unresolved (None) -> Must halt with clinical_decision_required and DEC-03
        engine_unresolved = TriageEngine(rf006_policy=None)
        res_unresolved = engine_unresolved.evaluate(patient)
        self.assertEqual(res_unresolved.status, TriageStatus.CLINICAL_DECISION_REQUIRED)
        self.assertEqual(res_unresolved.urgency.level, UrgencyLevel.NONE)
        self.assertIn("DEC-03", res_unresolved.metadata.pending_clinical_decisions)

        # Policy 2: Indian Casualty Model (Emergency / Red)
        engine_emergency = TriageEngine(rf006_policy="emergency")
        res_emergency = engine_emergency.evaluate(patient)
        self.assertEqual(res_emergency.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-006", res_emergency.metadata.fired_rules)

        # Policy 3: NICE Early Pregnancy Assessment Service Model (Clinic Visit / Amber)
        engine_clinic = TriageEngine(rf006_policy="clinic_visit")
        res_clinic = engine_clinic.evaluate(patient)
        self.assertEqual(res_clinic.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res_clinic.urgency.colour, UrgencyColour.AMBER)
        self.assertIn("RF-006", res_clinic.metadata.fired_rules)

    def test_rf_007_acute_pain_with_vomiting(self):
        # Sudden acute pain with persistent vomiting (ovarian torsion marker)
        patient = {
            "age": 27,
            "acute_severe_pelvic_pain": "yes",
            "sudden_pain_with_vomiting": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-007", res.metadata.fired_rules)

    def test_rf_008_postpartum_hemorrhage_with_systemic_signs(self):
        # Delivery 4 weeks ago, heavy bleeding with fever > 38.5C
        patient = {
            "age": 31,
            "postpartum_delivery_timing": "within_6_weeks",
            "postpartum_heavy_or_increasing_bleeding_or_clots": "yes",
            "fever_over_38_5c": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-008", res.metadata.fired_rules)

    def test_rf_009_candidate_rule_safety_guard(self):
        # Acute severe pain with pregnancy excluded matches candidate RF-009
        patient = {
            "age": 25,
            "acute_severe_pelvic_pain": "yes",
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,  # D1 pregnancy_excluded is True
        }

        # By default: candidate rules are disabled -> halts with clinical_decision_required and DEC-08
        res_default = self.engine.evaluate(patient)
        self.assertEqual(res_default.status, TriageStatus.CLINICAL_DECISION_REQUIRED)
        self.assertEqual(res_default.urgency.level, UrgencyLevel.NONE)
        self.assertIn("DEC-08", res_default.metadata.pending_clinical_decisions)
        self.assertIn("RF-009", res_default.metadata.candidate_rules_matched)

        # When candidate rules are explicitly enabled by doctor configuration:
        engine_enabled = TriageEngine(candidate_rules_enabled=True)
        res_enabled = engine_enabled.evaluate(patient)
        self.assertEqual(res_enabled.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertIn("RF-009", res_enabled.metadata.fired_rules)

    def test_red_lock_in_priority_invariant(self):
        # Patient matches both Red RF-003 and Yellow IRR-005 (heavy bleeding)
        patient = {
            "age": 28,
            "soaking_pad_hourly_2plus_hours": "yes",
            "fainting_or_near_fainting": "yes",  # Triggers RF-003 / RF-004
            "self_reported_heavy_flow": "yes",  # Triggers IRR-005
            "cycle_length_days": 28,
            "bleeding_duration_days": 6,
        }
        res = self.engine.evaluate(patient)
        # Red must NEVER be downgraded to Yellow
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertEqual(res.urgency.colour, UrgencyColour.RED)


if __name__ == "__main__":
    unittest.main()
