"""Unit and boundary tests for Irregular Periods Rules (IRR-001..IRR-013)."""

import unittest

from src.engine import TriageEngine
from src.models import TriageStatus, UrgencyColour, UrgencyLevel


class TestIrregularPeriodsRules(unittest.TestCase):
    def setUp(self):
        self.engine = TriageEngine()

    def test_irr_001_figo_age_stratified_variation_young_cohort(self):
        # Age 22 (<= 25 years): FIGO variation threshold is <= 9 days
        base_young = {
            "age": 22,
            "never_had_period": "no",
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 20,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "self_reported_heavy_flow": "no",
            "intermenstrual_bleeding_cycles": 0,
            "postcoital_bleeding": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "palpable_pelvic_lump": "no",
            "period_pain_affects_daily_life": "no",
            # Red flags ruled out (required for safe Green)
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
            "cycles_per_year": 12,
        }

        # Variation = 9 days -> Normal (Green)
        p_valid_9 = dict(base_young)
        p_valid_9["cycle_variation_days"] = 9
        res_9 = self.engine.evaluate(p_valid_9)
        self.assertEqual(res_9.urgency.level, UrgencyLevel.SELF_CARE)
        self.assertEqual(res_9.urgency.colour, UrgencyColour.GREEN)
        self.assertIn("IRR-001", res_9.metadata.fired_rules)

        # Variation = 10 days -> Exceeds FIGO threshold for young cohort -> Fails IRR-001
        p_invalid_10 = dict(base_young)
        p_invalid_10["cycle_variation_days"] = 10
        res_10 = self.engine.evaluate(p_invalid_10)
        self.assertNotIn("IRR-001", res_10.metadata.fired_rules)

    def test_irr_001_figo_age_stratified_variation_adult_cohort(self):
        # Age 30 (>= 26 years): FIGO variation threshold is <= 7 days
        base_adult = {
            "age": 30,
            "never_had_period": "no",
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 20,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "self_reported_heavy_flow": "no",
            "intermenstrual_bleeding_cycles": 0,
            "postcoital_bleeding": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "palpable_pelvic_lump": "no",
            "period_pain_affects_daily_life": "no",
            # Red flags ruled out (required for safe Green)
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
            "cycles_per_year": 12,
        }

        # Variation = 7 days -> Normal (Green)
        p_valid_7 = dict(base_adult)
        p_valid_7["cycle_variation_days"] = 7
        res_7 = self.engine.evaluate(p_valid_7)
        self.assertEqual(res_7.urgency.level, UrgencyLevel.SELF_CARE)
        self.assertIn("IRR-001", res_7.metadata.fired_rules)

        # Variation = 8 days -> Exceeds FIGO threshold for adult cohort -> Fails IRR-001
        p_invalid_8 = dict(base_adult)
        p_invalid_8["cycle_variation_days"] = 8
        res_8 = self.engine.evaluate(p_invalid_8)
        self.assertNotIn("IRR-001", res_8.metadata.fired_rules)

    def test_irr_002_frequent_menstrual_bleeding(self):
        # Cycle length < 24 days (polymenorrhea per FIGO/NICE)
        patient = {
            "age": 28,
            "cycle_length_days": 21,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("IRR-002", res.metadata.fired_rules)

    def test_irr_003_infrequent_menstrual_bleeding(self):
        # Cycle length 45 days (39-90 days = oligomenorrhea)
        patient = {
            "age": 26,
            "cycle_length_days": 45,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("IRR-003", res.metadata.fired_rules)

    def test_irr_004_secondary_amenorrhea(self):
        # Days since last period > 90 days, previous menses confirmed, pregnancy excluded
        patient = {
            "age": 25,
            "never_had_period": "no",
            "days_since_last_period": 110,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "postpartum_delivery_timing": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("IRR-004", res.metadata.fired_rules)

    def test_irr_005_uncomplicated_heavy_menstrual_bleeding(self):
        # Heavy menstrual flow without acute flooding, severe anemia, or structural mass
        patient = {
            "age": 32,
            "self_reported_heavy_flow": "yes",
            "soaking_pad_hourly_2plus_hours": "no",
            "passing_large_clots": "no",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
            "unusual_fatigue": "no",
            "noticeable_pallor": "no",
            "breathless_on_mild_exertion": "no",
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "postcoital_bleeding": "no",
            "intermenstrual_bleeding_cycles": 0,
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("IRR-005", res.metadata.fired_rules)

    def test_irr_006_functional_hypothalamic_amenorrhea(self):
        # Amenorrhea > 90 days with significant weight loss / low BMI
        patient = {
            "age": 21,
            "never_had_period": "no",
            "days_since_last_period": 120,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "pregnancy_test_days_ago": 5,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "palpable_pelvic_lump": "no",
            "persistent_pelvic_pain_or_pressure": "no",
            "postpartum_delivery_timing": "no",
            "significant_recent_weight_loss_or_intensive_exercise": "yes",
            "bmi": 17.5,
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("IRR-006", res.metadata.fired_rules)

    def test_irr_007_intermenstrual_bleeding_recurrent(self):
        # Spotting between periods in 2+ cycles -> Amber (Clinic Visit)
        patient = {
            "age": 29,
            "intermenstrual_bleeding_cycles": 2,
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res.urgency.colour, UrgencyColour.AMBER)
        self.assertIn("IRR-007", res.metadata.fired_rules)

    def test_irr_007a_stable_acute_flooding_or_large_clots(self):
        # Hourly soaking for 2+ hours without hemodynamic collapse -> Amber (Same-day clinic visit)
        patient = {
            "age": 27,
            "soaking_pad_hourly_2plus_hours": "yes",
            "fainting_or_near_fainting": "no",
            "racing_heartbeat_at_rest": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res.urgency.colour, UrgencyColour.AMBER)
        self.assertIn("IRR-007A", res.metadata.fired_rules)

    def test_irr_008_postcoital_bleeding(self):
        # Bleeding after intercourse -> Amber (Needs in-person speculum examination)
        patient = {
            "age": 34,
            "postcoital_bleeding": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertTrue(res.urgency.needs_physical_exam)
        self.assertIn("IRR-008", res.metadata.fired_rules)

    def test_irr_009_hmb_with_symptomatic_anemia(self):
        # Heavy bleeding with severe pallor and breathlessness -> Amber (Clinic Visit)
        patient = {
            "age": 30,
            "self_reported_heavy_flow": "yes",
            "noticeable_pallor": "yes",
            "breathless_on_mild_exertion": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-009", res.metadata.fired_rules)

    def test_irr_010_amenorrhea_with_pelvic_mass_or_pressure(self):
        # Amenorrhea with palpable pelvic lump -> Amber (Clinic Visit)
        patient = {
            "age": 27,
            "days_since_last_period": 100,
            "palpable_pelvic_lump": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-010", res.metadata.fired_rules)

    def test_irr_011_primary_amenorrhea(self):
        # Never had a period at age >= 18 -> Amber (Clinic Visit)
        patient = {
            "age": 19,
            "never_had_period": "yes",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("IRR-011", res.metadata.fired_rules)

    def test_irr_012_single_rule_conditional_escalation(self):
        # Case A: Expected unscheduled bleeding <= 3 months with up-to-date screening -> Yellow
        p_mild = {
            "age": 28,
            "contraceptive_method_type": "progestin_implant",
            "unscheduled_contraceptive_bleeding": "yes",
            "contraception_duration_months": 2,
            "cervical_screening_up_to_date": "yes",
        }
        res_mild = self.engine.evaluate(p_mild)
        self.assertEqual(res_mild.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res_mild.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("IRR-012", res_mild.metadata.fired_rules)

        # Case B: Bleeding persisting > 3 months -> Conditionally escalates to Amber (Clinic Visit)
        p_persisting = dict(p_mild)
        p_persisting["contraception_duration_months"] = 4
        res_persisting = self.engine.evaluate(p_persisting)
        self.assertEqual(res_persisting.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res_persisting.urgency.colour, UrgencyColour.AMBER)
        self.assertIn("IRR-012", res_persisting.metadata.fired_rules)

        # Case C: Cervical screening overdue/unknown -> Conditionally escalates to Amber
        p_screening_overdue = dict(p_mild)
        p_screening_overdue["cervical_screening_up_to_date"] = "no"
        res_screening = self.engine.evaluate(p_screening_overdue)
        self.assertEqual(res_screening.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res_screening.urgency.colour, UrgencyColour.AMBER)
        self.assertIn("IRR-012", res_screening.metadata.fired_rules)

    def test_irr_013_outpatient_pid_presentation(self):
        # Mild/moderate pelvic pain with feverishness or purulent discharge -> Amber (Clinic Visit)
        patient = {
            "age": 24,
            "pelvic_pain_any": "yes",
            "foul_smelling_or_purulent_discharge": "yes",
            "acute_severe_pelvic_pain": "no",
            "fever_over_38_5c": "no",
            "feels_severely_unwell": "no",
            "persistent_vomiting_cannot_keep_fluids_down": "no",
        }
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res.urgency.colour, UrgencyColour.AMBER)
        self.assertIn("IRR-013", res.metadata.fired_rules)


if __name__ == "__main__":
    unittest.main()
