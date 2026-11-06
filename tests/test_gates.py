"""Unit and boundary tests for Safety Gates (GATE-001..GATE-006) and Day 3 Derived Variables."""

import unittest

from src.gates import GateEvaluator


class TestSafetyGates(unittest.TestCase):
    def test_d10_interval_calculation(self):
        # Conclusive interval: 30 days since sex, tested 5 days ago -> 25 days interval
        patient = {"days_since_last_unprotected_sex": 30, "pregnancy_test_days_ago": 5}
        self.assertEqual(GateEvaluator.evaluate_d10(patient), 25.0)

        # Inconclusive interval: 15 days since sex, tested 2 days ago -> 13 days (< 21)
        patient = {"days_since_last_unprotected_sex": 15, "pregnancy_test_days_ago": 2}
        self.assertEqual(GateEvaluator.evaluate_d10(patient), 13.0)

        # Invalid/missing inputs
        self.assertEqual(GateEvaluator.evaluate_d10({}), "unknown")
        self.assertEqual(GateEvaluator.evaluate_d10({"days_since_last_unprotected_sex": "unknown"}), "unknown")

    def test_gate_001_pregnancy_precedence(self):
        # 1. Positive pregnancy test -> pregnancy_excluded is False
        p_pos = {"pregnancy_test_result": "positive"}
        val, _ = GateEvaluator.evaluate_d1_gate_001(p_pos)
        self.assertFalse(val)

        # 2. Conclusive negative test (>= 21 days post-exposure) -> True
        p_neg_conclusive = {
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,  # 30 - 5 = 25 >= 21
        }
        val, _ = GateEvaluator.evaluate_d1_gate_001(p_neg_conclusive)
        self.assertTrue(val)

        # 3. Inconclusive negative test (< 21 days post-exposure) -> "unknown"
        p_neg_early = {
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 15,
            "pregnancy_test_days_ago": 5,  # 15 - 5 = 10 < 21
        }
        val, _ = GateEvaluator.evaluate_d1_gate_001(p_neg_early)
        self.assertEqual(val, "unknown")

        # 4. Pregnancy excluded by sexual history (no activity/exposure) -> True
        p_no_sex = {
            "pregnancy_possible": "no",
            "unprotected_sex_in_last_12_months": "no",
        }
        val, _ = GateEvaluator.evaluate_d1_gate_001(p_no_sex)
        self.assertTrue(val)

        # 5. Sexual exposure reported, no test done -> "unknown"
        p_exposure_no_test = {
            "pregnancy_possible": "yes",
            "unprotected_sex_in_last_12_months": "yes",
            "pregnancy_test_result": "not_done",
        }
        val, _ = GateEvaluator.evaluate_d1_gate_001(p_exposure_no_test)
        self.assertEqual(val, "unknown")

    def test_gate_002_age_cohort_boundaries(self):
        # Under 18 -> out_of_scope
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 17})
        self.assertEqual(val, "out_of_scope")

        # Boundary: 18 -> 18_25
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 18})
        self.assertEqual(val, "18_25")

        # Boundary: 25 -> 18_25
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 25})
        self.assertEqual(val, "18_25")

        # Boundary: 26 -> 26_34
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 26})
        self.assertEqual(val, "26_34")

        # Boundary: 34 -> 26_34
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 34})
        self.assertEqual(val, "26_34")

        # Boundary: 35 -> 35_40
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 35})
        self.assertEqual(val, "35_40")

        # Boundary: 40 -> 35_40
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 40})
        self.assertEqual(val, "35_40")

        # Over 40 -> out_of_scope
        val, _ = GateEvaluator.evaluate_d2_gate_002({"age": 41})
        self.assertEqual(val, "out_of_scope")

        # Missing age -> unknown
        val, _ = GateEvaluator.evaluate_d2_gate_002({})
        self.assertEqual(val, "unknown")

    def test_gate_003a_and_003b_contraception(self):
        # Active COCP -> D3 is True
        p_cocp = {"contraceptive_method_type": "cocp_combined_pill"}
        val3a, _ = GateEvaluator.evaluate_d3_gate_003a(p_cocp)
        self.assertTrue(val3a)

        # Stopped COCP < 3 months -> D3 is True
        p_stopped = {"stopped_cocp_within_3_months": "yes"}
        val3a, _ = GateEvaluator.evaluate_d3_gate_003a(p_stopped)
        self.assertTrue(val3a)

        # Progestin only -> D4 is True
        p_prog = {"contraceptive_method_type": "progestin_implant"}
        val3b, _ = GateEvaluator.evaluate_d4_gate_003b(p_prog)
        self.assertTrue(val3b)

        # D5 composite: either COCP or progestin
        val5, _ = GateEvaluator.evaluate_d5(p_prog)
        self.assertTrue(val5)

        # No contraception -> False
        p_none = {
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
        }
        val3a, _ = GateEvaluator.evaluate_d3_gate_003a(p_none)
        val3b, _ = GateEvaluator.evaluate_d4_gate_003b(p_none)
        val5, _ = GateEvaluator.evaluate_d5(p_none)
        self.assertFalse(val3a)
        self.assertFalse(val3b)
        self.assertFalse(val5)

    def test_gate_004_d6_formal_lam_strict_criteria(self):
        # Strict Formal LAM: < 6 months postpartum + exclusive breastfeeding + menses NOT returned
        p_lam_valid = {
            "postpartum_delivery_timing": "12_weeks_to_under_6_months",
            "exclusively_breastfeeding": "yes",
            "menses_returned": "no",
            "days_since_last_period": 100,
        }
        val, exp = GateEvaluator.evaluate_d6_gate_004(p_lam_valid)
        self.assertTrue(val)
        self.assertIn("Formal LAM eligible", exp)

        # Negative Boundary 1: Infant age >= 6 months (exactly_6_to_12_months)
        # Even with exclusive breastfeeding, formal contraceptive LAM has expired!
        p_lam_expired = {
            "postpartum_delivery_timing": "exactly_6_to_12_months",
            "exclusively_breastfeeding": "yes",
            "menses_returned": "no",
            "days_since_last_period": 200,
        }
        val, exp = GateEvaluator.evaluate_d6_gate_004(p_lam_expired)
        self.assertFalse(val)
        self.assertIn("expired", exp)

        # Negative Boundary 2: Return of menses breaks formal LAM
        p_menses_returned = {
            "postpartum_delivery_timing": "6_to_12_weeks",
            "exclusively_breastfeeding": "yes",
            "menses_returned": "yes",
            "days_since_last_period": 20,
        }
        val, exp = GateEvaluator.evaluate_d6_gate_004(p_menses_returned)
        self.assertFalse(val)
        self.assertIn("returned", exp)

        # Negative Boundary 3: Not exclusively breastfeeding (< 6m) -> False
        p_formula = {
            "postpartum_delivery_timing": "6_to_12_weeks",
            "exclusively_breastfeeding": "no",
            "menses_returned": "no",
        }
        val, exp = GateEvaluator.evaluate_d6_gate_004(p_formula)
        self.assertFalse(val)

        # Non-postpartum patient -> False
        val, _ = GateEvaluator.evaluate_d6_gate_004({"postpartum_delivery_timing": "no"})
        self.assertFalse(val)

    def test_gate_005_gynecological_age(self):
        # Age 25, menarche at 13 -> gynegological age = 12 >= 3 -> True
        val, _ = GateEvaluator.evaluate_d7_gate_005({"age": 25, "menarche_age": 13})
        self.assertTrue(val)

        # Age 18, menarche at 16 -> gynecological age = 2 < 3 -> False (immature axis)
        val, _ = GateEvaluator.evaluate_d7_gate_005({"age": 18, "menarche_age": 16})
        self.assertFalse(val)

        # Primary amenorrhea (never menstruated) -> False
        val, _ = GateEvaluator.evaluate_d7_gate_005({"age": 19, "never_had_period": "yes"})
        self.assertFalse(val)

    def test_gate_006_sti_risk(self):
        val, _ = GateEvaluator.evaluate_d8_gate_006({"new_or_multiple_sexual_partners_past_12_months": "yes"})
        self.assertTrue(val)

        val, _ = GateEvaluator.evaluate_d8_gate_006({"new_or_multiple_sexual_partners_past_12_months": "no"})
        self.assertFalse(val)

    def test_d9_tubal_risk_history(self):
        self.assertTrue(GateEvaluator.evaluate_d9({"prior_pid": "yes", "prior_ectopic_pregnancy": "no", "prior_tubal_or_pelvic_surgery": "no"})[0])
        self.assertTrue(GateEvaluator.evaluate_d9({"prior_pid": "no", "prior_ectopic_pregnancy": "yes", "prior_tubal_or_pelvic_surgery": "no"})[0])
        self.assertTrue(GateEvaluator.evaluate_d9({"prior_pid": "no", "prior_ectopic_pregnancy": "no", "prior_tubal_or_pelvic_surgery": "yes"})[0])
        self.assertFalse(GateEvaluator.evaluate_d9({"prior_pid": "no", "prior_ectopic_pregnancy": "no", "prior_tubal_or_pelvic_surgery": "no"})[0])
        self.assertEqual(GateEvaluator.evaluate_d9({"prior_pid": "no", "prior_ectopic_pregnancy": "no", "prior_tubal_or_pelvic_surgery": "unknown"})[0], "unknown")

    def test_d12_ovulatory_dysfunction_pattern(self):
        # Irregular cycle length (42 days) with mature axis, no contraception, pregnancy excluded -> True
        p_irreg = {"cycle_length_days": 42}
        self.assertTrue(GateEvaluator.evaluate_d12(p_irreg, d7=True, d5=False, d1=True)[0])

        # Short cycle length (18 days) -> True
        p_short = {"cycle_length_days": 18}
        self.assertTrue(GateEvaluator.evaluate_d12(p_short, d7=True, d5=False, d1=True)[0])

        # Cycles per year < 8 -> True
        p_infreq = {"cycles_per_year": 6}
        self.assertTrue(GateEvaluator.evaluate_d12(p_infreq, d7=True, d5=False, d1=True)[0])

        # Days since last period > 90 -> True
        p_gap = {"days_since_last_period": 100}
        self.assertTrue(GateEvaluator.evaluate_d12(p_gap, d7=True, d5=False, d1=True)[0])

        # Regular cycles (28 days) -> False
        p_reg = {"cycle_length_days": 28, "cycles_per_year": 12, "days_since_last_period": 14}
        self.assertFalse(GateEvaluator.evaluate_d12(p_reg, d7=True, d5=False, d1=True)[0])

        # Gated out if pregnant (d1=False), on pill (d5=True), or immature (d7=False)
        self.assertFalse(GateEvaluator.evaluate_d12(p_irreg, d7=False, d5=False, d1=True)[0])
        self.assertFalse(GateEvaluator.evaluate_d12(p_irreg, d7=True, d5=True, d1=True)[0])
        self.assertFalse(GateEvaluator.evaluate_d12(p_irreg, d7=True, d5=False, d1=False)[0])

        # Unknown gate parameter -> returns unknown
        self.assertEqual(GateEvaluator.evaluate_d12(p_irreg, d7="unknown", d5=False, d1=True)[0], "unknown")

    def test_d13_endometriosis_suspicion_signal(self):
        self.assertTrue(GateEvaluator.evaluate_d13({"period_pain_affects_daily_life": "yes", "deep_dyspareunia": "no", "cyclical_bowel_symptoms": "no", "cyclical_urinary_symptoms": "no", "chronic_pelvic_pain_6plus_months": "no"})[0])
        self.assertTrue(GateEvaluator.evaluate_d13({"period_pain_affects_daily_life": "no", "deep_dyspareunia": "yes", "cyclical_bowel_symptoms": "no", "cyclical_urinary_symptoms": "no", "chronic_pelvic_pain_6plus_months": "no"})[0])
        self.assertFalse(GateEvaluator.evaluate_d13({"period_pain_affects_daily_life": "no", "deep_dyspareunia": "no", "cyclical_bowel_symptoms": "no", "cyclical_urinary_symptoms": "no", "chronic_pelvic_pain_6plus_months": "no"})[0])
        self.assertEqual(GateEvaluator.evaluate_d13({"period_pain_affects_daily_life": "no", "deep_dyspareunia": "unknown", "cyclical_bowel_symptoms": "no", "cyclical_urinary_symptoms": "no", "chronic_pelvic_pain_6plus_months": "no"})[0], "unknown")


if __name__ == "__main__":
    unittest.main()
