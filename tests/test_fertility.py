"""Unit and pathway integration tests for Fertility & Preconception.

Guideline reference: NICE NG257 (Fertility problems), ASRM Guidelines, & ESHRE Recurrent Loss Guideline
Rules tested: FERT-001 through FERT-008, D9, PATH-FERT-01
"""

import unittest

from src.engine import TriageEngine
from src.loader import load_rules
from src.models import TriageStatus, UrgencyColour, UrgencyLevel


class TestFertility(unittest.TestCase):
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
        }

    def test_fert_001_normal_conception_window_green(self):
        # Age < 35, trying < 12 months, regular cycles, no known risks -> FERT-001 (Green / Self-Care)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 28,
            "menarche_age": 12,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 10,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "trying_to_conceive": "yes",
            "trying_duration_months": 5,
            "miscarriage_count": 0,
            "second_trimester_loss": "no",
            "prior_pid": "no",
            "prior_ectopic_pregnancy": "no",
            "prior_tubal_or_pelvic_surgery": "no",
            "unable_to_have_penetrative_intercourse": "no",
            "period_pain_affects_daily_life": "no",
            "deep_dyspareunia": "no",
            "cyclical_bowel_symptoms": "no",
            "cyclical_urinary_symptoms": "no",
            "chronic_pelvic_pain_6plus_months": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.SELF_CARE)
        self.assertEqual(res.urgency.colour, UrgencyColour.GREEN)
        self.assertIn("FERT-001", res.metadata.fired_rules)

    def test_fert_002_formal_infertility_threshold_age_under_35_trying_ge_12m(self):
        # Age 30 (< 35), trying for 14 months (>= 12m) -> Formal NICE/ASRM threshold -> FERT-002 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 30,
            "trying_to_conceive": "yes",
            "trying_duration_months": 14,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "miscarriage_count": 0,
            "second_trimester_loss": "no",
            "prior_pid": "no",
            "prior_ectopic_pregnancy": "no",
            "prior_tubal_or_pelvic_surgery": "no",
            "unable_to_have_penetrative_intercourse": "no",
            "period_pain_affects_daily_life": "no",
            "deep_dyspareunia": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("FERT-002", res.metadata.fired_rules)

    def test_fert_003_asrm_threshold_age_ge_35_trying_ge_6m(self):
        # Age 37 (>= 35), trying for 8 months (>= 6m) -> Earlier ASRM evaluation threshold -> FERT-003 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 37,
            "trying_to_conceive": "yes",
            "trying_duration_months": 8,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "miscarriage_count": 0,
            "second_trimester_loss": "no",
            "prior_pid": "no",
            "prior_ectopic_pregnancy": "no",
            "prior_tubal_or_pelvic_surgery": "no",
            "unable_to_have_penetrative_intercourse": "no",
            "period_pain_affects_daily_life": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("FERT-003", res.metadata.fired_rules)

    def test_fert_004_nice_earlier_consultation_age_36_to_40_trying_under_6m(self):
        # [REV-2] Woman aged 38 (36–40) trying for 4 months (< 6m) -> Earlier consultation option FERT-004 (Yellow, DEC-09)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 38,
            "trying_to_conceive": "yes",
            "trying_duration_months": 4,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "miscarriage_count": 0,
            "second_trimester_loss": "no",
            "prior_pid": "no",
            "prior_ectopic_pregnancy": "no",
            "prior_tubal_or_pelvic_surgery": "no",
            "unable_to_have_penetrative_intercourse": "no",
            "period_pain_affects_daily_life": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("FERT-004", res.metadata.fired_rules)
        self.assertIn("DEC-09", res.metadata.pending_clinical_decisions)

    def test_fert_age_35_trying_under_6m_pending_decision_rev2(self):
        # [REV-2] Age 35 with < 6 months trying must NOT be automatically assigned Yellow or Green.
        # It terminates at PATH-FERT-01-TERM-AGE35 with status clinical_decision_required and DEC-09.
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 35,
            "trying_to_conceive": "yes",
            "trying_duration_months": 3,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "miscarriage_count": 0,
            "second_trimester_loss": "no",
            "prior_pid": "no",
            "prior_ectopic_pregnancy": "no",
            "prior_tubal_or_pelvic_surgery": "no",
            "unable_to_have_penetrative_intercourse": "no",
            "period_pain_affects_daily_life": "no",
            "deep_dyspareunia": "no",
            "cyclical_bowel_symptoms": "no",
            "cyclical_urinary_symptoms": "no",
            "chronic_pelvic_pain_6plus_months": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.CLINICAL_DECISION_REQUIRED)
        self.assertEqual(res.urgency.level, UrgencyLevel.NONE)
        self.assertIn("DEC-09", res.metadata.pending_clinical_decisions)

    def test_fert_005_ovulatory_dysfunction_subfertility_yellow(self):
        # Trying to conceive with irregular cycles (45d) -> FERT-005 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 29,
            "trying_to_conceive": "yes",
            "trying_duration_months": 4,
            "menarche_age": 13,
            "cycle_length_days": 45,
            "bleeding_duration_days": 5,
            "days_since_last_period": 25,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "miscarriage_count": 0,
            "second_trimester_loss": "no",
            "prior_pid": "no",
            "prior_ectopic_pregnancy": "no",
            "prior_tubal_or_pelvic_surgery": "no",
            "unable_to_have_penetrative_intercourse": "no",
            "period_pain_affects_daily_life": "no",
            "deep_dyspareunia": "no",
            "cyclical_bowel_symptoms": "no",
            "cyclical_urinary_symptoms": "no",
            "chronic_pelvic_pain_6plus_months": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("FERT-005", res.metadata.fired_rules)

    def test_fert_006_tubal_risk_history_amber(self):
        # Trying to conceive with prior ectopic pregnancy -> FERT-006 (Amber / Clinic Visit, exam needed)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 31,
            "trying_to_conceive": "yes",
            "trying_duration_months": 2,
            "prior_ectopic_pregnancy": "yes",
            "prior_pid": "no",
            "prior_tubal_or_pelvic_surgery": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertTrue(res.urgency.needs_physical_exam)
        self.assertIn("FERT-006", res.metadata.fired_rules)

    def test_fert_007_recurrent_pregnancy_loss_amber(self):
        # Recurrent miscarriage (2 prior losses) -> FERT-007 (Amber, DEC-10)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 32,
            "trying_to_conceive": "yes",
            "miscarriage_count": 2,
            "second_trimester_loss": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertTrue(res.urgency.needs_physical_exam)
        self.assertIn("FERT-007", res.metadata.fired_rules)
        self.assertIn("DEC-10", res.metadata.pending_clinical_decisions)

    def test_fert_008_inability_to_have_penetrative_intercourse_amber(self):
        # Trying to conceive + unable to achieve penetrative intercourse -> FERT-008 (Amber)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 27,
            "trying_to_conceive": "yes",
            "unable_to_have_penetrative_intercourse": "yes",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertTrue(res.urgency.needs_physical_exam)
        self.assertIn("FERT-008", res.metadata.fired_rules)

    def test_fertility_unknown_safety_handling(self):
        # [REV-2] Unknown tubal history or unknown coital difficulty must NOT escalate to Amber.
        # Must return need_more_info.
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 29,
            "trying_to_conceive": "yes",
            "trying_duration_months": 4,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "prior_pid": "unknown",
            "prior_ectopic_pregnancy": "unknown",
            "prior_tubal_or_pelvic_surgery": "unknown",
            "unable_to_have_penetrative_intercourse": "unknown",
        })
        res = self.engine.evaluate(patient)
        # Should not falsely escalate to Amber
        self.assertNotEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)


if __name__ == "__main__":
    unittest.main()
