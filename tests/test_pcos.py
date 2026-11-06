"""Unit and pathway integration tests for Polycystic Ovary Syndrome (PCOS).

Guideline reference: 2023 International Evidence-based PCOS Guideline (Monash / Endocrine Society)
Rules tested: PCOS-001 through PCOS-009, D12, PATH-PCOS-01
"""

import unittest

from src.engine import TriageEngine
from src.loader import load_rules
from src.models import TriageStatus, UrgencyColour, UrgencyLevel


class TestPCOS(unittest.TestCase):
    def setUp(self):
        self.engine = TriageEngine()
        self.rules = {r.id: r for r in load_rules()}

    def _base_ruled_out_red_flags(self):
        return {
            "acute_severe_pelvic_pain": "no",
            "shoulder_tip_pain": "no",
            "soaking_pad_hourly_2plus_hours": "no",
            "fainting_or_near_fainting": "no",
            "pelvic_pain_any": "no",
            "vaginal_bleeding_now": "no",
            "postpartum_delivery_timing": "no",
            "fever_over_38_5c": "no",
            "feels_feverish_or_has_chills": "no",
            "foul_smelling_or_purulent_discharge": "no",
            "passing_large_clots": "no",
            "sudden_pain_with_vomiting": "no",
            "rapid_virilization_signs": "no",
            "rapid_virilization": "no",
        }

    def test_pcos_001_ovulatory_dysfunction_screening_adult_yellow(self):
        # Adult woman (>= 3 yrs post-menarche) with cycle length > 35 days -> PCOS-001 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 24,
            "menarche_age": 12,
            "cycle_length_days": 42,
            "bleeding_duration_days": 5,
            "days_since_last_period": 20,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "hirsutism_excessive_hair": "no",
            "moderate_severe_cystic_acne": "no",
            "male_pattern_alopecia": "no",
            "known_pcos": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("PCOS-001", res.metadata.fired_rules)

    def test_pcos_002_prolonged_cycle_gap_with_androgen_signs_yellow(self):
        # Adult woman with amenorrhea > 90 days and hirsutism -> PCOS-002 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 25,
            "menarche_age": 13,
            "cycle_length_days": 30,
            "bleeding_duration_days": 5,
            "days_since_last_period": 100,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "hirsutism_excessive_hair": "yes",
            "known_pcos": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("PCOS-002", res.metadata.fired_rules)

    def test_pcos_003_adult_rotterdam_clinical_hirsutism_yellow(self):
        # Adult with ovulatory dysfunction pattern + clinical hirsutism -> Rotterdam adult phenotype PCOS-003 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 26,
            "menarche_age": 12,
            "cycle_length_days": 45,
            "bleeding_duration_days": 5,
            "days_since_last_period": 25,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "hirsutism_excessive_hair": "yes",
            "known_pcos": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("PCOS-003", res.metadata.fired_rules)

    def test_pcos_004_irregular_cycles_isolated_acne_or_alopecia(self):
        # Ovulatory dysfunction + severe acne without hirsutism -> PCOS-004 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 25,
            "menarche_age": 12,
            "cycle_length_days": 50,
            "bleeding_duration_days": 5,
            "days_since_last_period": 30,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "hirsutism_excessive_hair": "no",
            "moderate_severe_cystic_acne": "yes",
            "male_pattern_alopecia": "no",
            "known_pcos": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("PCOS-004", res.metadata.fired_rules)

    def test_pcos_005_rapid_virilization_amber(self):
        # Rapid virilization signs -> PCOS-005 (Amber / Clinic Visit, in-person exam required)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 28,
            "rapid_virilization_signs": "yes",
            "rapid_virilization": "yes",
            "hirsutism_excessive_hair": "yes",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res.urgency.colour, UrgencyColour.AMBER)
        self.assertTrue(res.urgency.needs_physical_exam)
        self.assertIn("PCOS-005", res.metadata.fired_rules)

    def test_pcos_006_regular_cycles_clinical_hirsutism(self):
        # Regular cycles (28d) but marked clinical hirsutism -> PCOS-006 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 27,
            "menarche_age": 12,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "hirsutism_excessive_hair": "yes",
            "known_pcos": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("PCOS-006", res.metadata.fired_rules)

    def test_pcos_007_cardiometabolic_risk_markers(self):
        # Known PCOS with BMI >= 23 or acanthosis nigricans -> PCOS-007 (Yellow, DEC-06)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 30,
            "known_pcos": "yes",
            "bmi": 26.5,
            "acanthosis_nigricans": "yes",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("PCOS-007", res.metadata.fired_rules)
        self.assertIn("DEC-06", res.metadata.pending_clinical_decisions)

    def test_pcos_008_endometrial_protection_alert(self):
        # Amenorrhea > 90 days with known PCOS -> PCOS-008 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 29,
            "days_since_last_period": 110,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "known_pcos": "yes",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("PCOS-008", res.metadata.fired_rules)

    def test_pcos_009_normal_cycles_no_pcos_green(self):
        # Normal regular cycles with confirmed absence of androgen excess signs -> PCOS-009 (Green)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 24,
            "menarche_age": 12,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "hirsutism_excessive_hair": "no",
            "moderate_severe_cystic_acne": "no",
            "male_pattern_alopecia": "no",
            "known_pcos": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.SELF_CARE)
        self.assertEqual(res.urgency.colour, UrgencyColour.GREEN)
        self.assertIn("PCOS-009", res.metadata.fired_rules)

    def test_bmi_not_a_diagnostic_criterion(self):
        # High BMI (34.5) alone without ovulatory dysfunction or hyperandrogenism MUST NOT trigger PCOS
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 27,
            "menarche_age": 12,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "bmi": 34.5,
            "hirsutism_excessive_hair": "no",
            "moderate_severe_cystic_acne": "no",
            "male_pattern_alopecia": "no",
            "known_pcos": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertNotIn("PCOS-003", res.metadata.fired_rules)
        self.assertNotIn("PCOS-004", res.metadata.fired_rules)


if __name__ == "__main__":
    unittest.main()
