"""Unit and branch traversal tests for Day 3 Decision Pathways (PATH-AMEN-01 and PATH-HMB-01)."""

import unittest

from src.engine import TriageEngine
from src.models import TriageStatus, UrgencyColour, UrgencyLevel


class TestDay3Pathways(unittest.TestCase):
    def setUp(self):
        self.engine = TriageEngine()

    # --------------------------------------------------------------------------
    # PATH-AMEN-01 (Amenorrhea & Missed Periods > 90 days)
    # --------------------------------------------------------------------------

    def test_path_amen_01_step_s1_primary_amenorrhea(self):
        # Patient age 19, never menstruated
        patient = {
            "age": 19,
            "never_had_period": "yes",
            "days_since_last_period": 999,
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-011", res.metadata.fired_rules)

    def test_path_amen_01_step_s1_unknown_handling(self):
        # Patient misses periods > 90 days, but never_had_period is unknown -> need_more_info
        patient = {
            "age": 22,
            "days_since_last_period": 100,
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.NEED_MORE_INFO)
        missing_fields = [m.field for m in res.missing_inputs]
        self.assertIn("never_had_period", missing_fields)

    def test_path_amen_01_step_s2_pregnancy_gate_need_more_info(self):
        # Menses confirmed, pregnancy possible but no test done -> need_more_info
        patient = {
            "age": 24,
            "never_had_period": "no",
            "days_since_last_period": 100,
            "pregnancy_possible": "yes",
            "unprotected_sex_in_last_12_months": "yes",
            "pregnancy_test_result": "not_done",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.NEED_MORE_INFO)
        missing_fields = [m.field for m in res.missing_inputs]
        self.assertIn("pregnancy_test_result", missing_fields)

    def test_path_amen_01_step_s3_pelvic_mass_or_pressure(self):
        # Secondary amenorrhea with palpable pelvic lump -> IRR-010 (Amber)
        patient = {
            "age": 27,
            "never_had_period": "no",
            "days_since_last_period": 120,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "palpable_pelvic_lump": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-010", res.metadata.fired_rules)

    def test_path_amen_01_step_s4_lactational_amenorrhea(self):
        # Postpartum LAM eligible (< 6m, exclusive breastfeeding, amenorrheic)
        patient = {
            "age": 29,
            "never_had_period": "no",
            "days_since_last_period": 100,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "postpartum_delivery_timing": "12_weeks_to_under_6_months",
            "exclusively_breastfeeding": "yes",
            "menses_returned": "no",
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("IRR-004", res.metadata.fired_rules)

    def test_path_amen_01_step_s5b_clean_pcos_deferral(self):
        # Patient with amenorrhea > 90 days and hirsutism/acne -> Clean Day 4 PCOS deferral recorded in metadata
        patient = {
            "age": 25,
            "never_had_period": "no",
            "days_since_last_period": 120,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "postpartum_delivery_timing": "no",
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "rapid_virilization": "no",
            "hirsutism_excessive_hair": "yes",
        }
        res = self.engine.evaluate(patient)
        # Standalone IRR-004 provides safety base, while deferred pathway records PCOS Day 4 link
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("IRR-004", res.metadata.fired_rules)
        target_pathways = [d["target_pathway"] for d in res.metadata.deferred_pathways]
        self.assertIn("PATH-PCOS-01", target_pathways)

    def test_path_amen_01_step_s5c_fha_and_uncomplicated(self):
        # Endogenous secondary amenorrhea with low BMI -> IRR-006 (Yellow)
        patient_fha = {
            "age": 23,
            "never_had_period": "no",
            "days_since_last_period": 110,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "postpartum_delivery_timing": "no",
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "rapid_virilization": "no",
            "hirsutism_excessive_hair": "no",
            "moderate_severe_cystic_acne": "no",
            "male_pattern_alopecia": "no",
            "significant_recent_weight_loss_or_intensive_exercise": "yes",
            "bmi": 17.8,
        }
        res_fha = self.engine.evaluate(patient_fha)
        self.assertEqual(res_fha.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("IRR-006", res_fha.metadata.fired_rules)

        # Standard endogenous secondary amenorrhea (normal weight) -> IRR-004 (Yellow)
        patient_norm = dict(patient_fha)
        patient_norm["significant_recent_weight_loss_or_intensive_exercise"] = "no"
        patient_norm["bmi"] = 22.0
        res_norm = self.engine.evaluate(patient_norm)
        self.assertEqual(res_norm.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("IRR-004", res_norm.metadata.fired_rules)

    # --------------------------------------------------------------------------
    # PATH-HMB-01 (Heavy & Abnormal Menstrual Bleeding)
    # --------------------------------------------------------------------------

    def test_path_hmb_01_step_s1_instability_emergency(self):
        # Heavy bleeding + syncope -> RF-003 / RF-004 (Red)
        patient = {
            "age": 28,
            "self_reported_heavy_flow": "yes",
            "soaking_pad_hourly_2plus_hours": "yes",
            "fainting_or_near_fainting": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.EMERGENCY)
        self.assertEqual(res.urgency.colour, UrgencyColour.RED)

    def test_path_hmb_01_step_s1b_stable_flooding_amber(self):
        # Hourly soaking for 2+ hours, stable hemodynamics -> IRR-007A (Amber)
        patient = {
            "age": 31,
            "self_reported_heavy_flow": "yes",
            "soaking_pad_hourly_2plus_hours": "yes",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res.urgency.colour, UrgencyColour.AMBER)
        self.assertIn("IRR-007A", res.metadata.fired_rules)

    def test_path_hmb_01_step_s2_postcoital_bleeding(self):
        # Postcoital bleeding reported -> IRR-008 (Amber)
        patient = {
            "age": 33,
            "self_reported_heavy_flow": "no",
            "postcoital_bleeding": "yes",
            "soaking_pad_hourly_2plus_hours": "no",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
            "passing_large_clots": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-008", res.metadata.fired_rules)

    def test_path_hmb_01_step_s3_recurrent_intermenstrual_bleeding(self):
        # Bleeding between periods in 2+ cycles -> IRR-007 (Amber)
        patient = {
            "age": 29,
            "self_reported_heavy_flow": "no",
            "intermenstrual_bleeding_cycles": 2,
            "postcoital_bleeding": "no",
            "soaking_pad_hourly_2plus_hours": "no",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
            "passing_large_clots": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-007", res.metadata.fired_rules)

    def test_path_hmb_01_step_s4_anemia_amber(self):
        # Heavy bleeding + severe pallor / breathlessness -> IRR-009 (Amber)
        patient = {
            "age": 30,
            "self_reported_heavy_flow": "yes",
            "soaking_pad_hourly_2plus_hours": "no",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
            "passing_large_clots": "no",
            "postcoital_bleeding": "no",
            "intermenstrual_bleeding_cycles": 0,
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "noticeable_pallor": "yes",
            "breathless_on_mild_exertion": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-009", res.metadata.fired_rules)

    def test_path_hmb_01_step_s4b_uncomplicated_hmb_yellow(self):
        # Uncomplicated heavy flow without anemia, acute flooding, or pain -> IRR-005 (Yellow)
        patient = {
            "age": 30,
            "self_reported_heavy_flow": "yes",
            "soaking_pad_hourly_2plus_hours": "no",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
            "passing_large_clots": "no",
            "postcoital_bleeding": "no",
            "intermenstrual_bleeding_cycles": 0,
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "unusual_fatigue": "no",
            "noticeable_pallor": "no",
            "breathless_on_mild_exertion": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("IRR-005", res.metadata.fired_rules)

    def test_path_hmb_01_step_s4b_single_cycle_imb_gap_resolution(self):
        # Solves Feedback #7: Isolated single-cycle IMB (P41 == 1) without heavy flow
        # Must NOT route to IRR-005 (whose condition is false); routes to candidate terminal pending DISC-IMB1 review
        patient = {
            "age": 28,
            "self_reported_heavy_flow": "no",
            "intermenstrual_bleeding_cycles": 1,
            "postcoital_bleeding": "no",
            "soaking_pad_hourly_2plus_hours": "no",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
            "passing_large_clots": "no",
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "unusual_fatigue": "no",
            "noticeable_pallor": "no",
            "breathless_on_mild_exertion": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.status, TriageStatus.CLINICAL_DECISION_REQUIRED)
        self.assertEqual(res.urgency.level, UrgencyLevel.NONE)
        self.assertIn("DISC-IMB1", res.metadata.pending_clinical_decisions)


if __name__ == "__main__":
    unittest.main()
