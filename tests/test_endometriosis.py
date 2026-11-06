"""Unit and pathway integration tests for Endometriosis & Pelvic Pain.

Guideline reference: NICE NG73 (Endometriosis: diagnosis and management) & ESHRE Endometriosis Guideline
Rules tested: ENDO-001 through ENDO-008, D13, PATH-ENDO-01
"""

import unittest

from src.engine import TriageEngine
from src.loader import load_rules
from src.models import TriageStatus, UrgencyColour, UrgencyLevel


class TestEndometriosis(unittest.TestCase):
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

    def test_endo_001_normal_menses_no_symptoms_green(self):
        # Absence of disabling period pain and extragenital symptoms -> ENDO-001 (Green)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 28,
            "menarche_age": 12,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "days_since_last_period": 14,
            "pregnancy_test_result": "negative",
            "days_since_last_unprotected_sex": 30,
            "contraceptive_method_type": "none",
            "stopped_cocp_within_3_months": "no",
            "period_pain_affects_daily_life": "no",
            "deep_dyspareunia": "no",
            "cyclical_bowel_symptoms": "no",
            "cyclical_urinary_symptoms": "no",
            "chronic_pelvic_pain_6plus_months": "no",
            "known_endometriosis": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.SELF_CARE)
        self.assertEqual(res.urgency.colour, UrgencyColour.GREEN)
        self.assertIn("ENDO-001", res.metadata.fired_rules)

    def test_endo_002_severe_cyclical_dysmenorrhea_yellow(self):
        # Disabling period pain interfering with daily life -> ENDO-002 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 26,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "period_pain_affects_daily_life": "yes",
            "deep_dyspareunia": "no",
            "cyclical_bowel_symptoms": "no",
            "cyclical_urinary_symptoms": "no",
            "chronic_pelvic_pain_6plus_months": "no",
            "pelvic_mass_or_fullness": "no",
            "prior_endometriosis_treatment_failed": "no",
            "trying_to_conceive": "no",
            "known_endometriosis": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertEqual(res.urgency.colour, UrgencyColour.YELLOW)
        self.assertIn("ENDO-002", res.metadata.fired_rules)

    def test_endo_003_deep_dyspareunia_and_cyclical_bowel_yellow(self):
        # Deep dyspareunia or cyclical bowel symptoms -> ENDO-003 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 29,
            "period_pain_affects_daily_life": "no",
            "deep_dyspareunia": "yes",
            "cyclical_bowel_symptoms": "yes",
            "cyclical_urinary_symptoms": "no",
            "chronic_pelvic_pain_6plus_months": "no",
            "pelvic_mass_or_fullness": "no",
            "prior_endometriosis_treatment_failed": "no",
            "trying_to_conceive": "no",
            "known_endometriosis": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("ENDO-003", res.metadata.fired_rules)

    def test_endo_004_chronic_pelvic_pain_amber(self):
        # Chronic pelvic pain >= 6 months -> ENDO-004 (Amber / Clinic Visit, in-person exam needed)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 31,
            "chronic_pelvic_pain_6plus_months": "yes",
            "pelvic_mass_or_fullness": "no",
            "period_pain_affects_daily_life": "yes",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertEqual(res.urgency.colour, UrgencyColour.AMBER)
        self.assertTrue(res.urgency.needs_physical_exam)
        self.assertIn("ENDO-004", res.metadata.fired_rules)

    def test_endo_005_failed_first_line_treatment_amber(self):
        # Failure of first-line hormonal/NSAID treatment -> ENDO-005 (Amber, specialist referral)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 27,
            "period_pain_affects_daily_life": "yes",
            "prior_endometriosis_treatment_failed": "yes",
            "chronic_pelvic_pain_6plus_months": "no",
            "pelvic_mass_or_fullness": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertTrue(res.urgency.needs_physical_exam)
        self.assertIn("ENDO-005", res.metadata.fired_rules)

    def test_endo_006_concurrent_subfertility_amber(self):
        # Suspected endometriosis + trying to conceive -> ENDO-006 (Amber)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 30,
            "period_pain_affects_daily_life": "yes",
            "trying_to_conceive": "yes",
            "chronic_pelvic_pain_6plus_months": "no",
            "pelvic_mass_or_fullness": "no",
            "prior_endometriosis_treatment_failed": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("ENDO-006", res.metadata.fired_rules)

    def test_endo_007_known_endometriosis_monitoring_yellow(self):
        # Known endometriosis routine follow-up -> ENDO-007 (Yellow)
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 33,
            "known_endometriosis": "yes",
            "chronic_pelvic_pain_6plus_months": "no",
            "pelvic_mass_or_fullness": "no",
            "prior_endometriosis_treatment_failed": "no",
            "trying_to_conceive": "no",
        })
        res = self.engine.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("ENDO-007", res.metadata.fired_rules)

    def test_endo_008_proposed_mapping_dec07_inactive_by_default(self):
        # [REV-2] ENDO-008 is a proposed mapping (2 of 4) requiring doctor approval (DEC-07).
        # By default, it MUST NOT auto-assign Amber triage level; it records proposal in metadata.
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 28,
            "cycle_length_days": 28,
            "bleeding_duration_days": 5,
            "period_pain_affects_daily_life": "yes",
            "deep_dyspareunia": "yes",
            "cyclical_bowel_symptoms": "no",
            "cyclical_urinary_symptoms": "no",
            "chronic_pelvic_pain_6plus_months": "no",
            "pelvic_mass_or_fullness": "no",
            "prior_endometriosis_treatment_failed": "no",
            "trying_to_conceive": "no",
            "known_endometriosis": "no",
        })
        res = self.engine.evaluate(patient)
        # Without endo008_policy approved, it does not escalate to Amber; ENDO-002/003 (Yellow) handles care
        self.assertEqual(res.urgency.level, UrgencyLevel.TELECONSULTATION)
        self.assertIn("DEC-07", res.metadata.pending_clinical_decisions)
        self.assertIn("ENDO-008", res.metadata.proposed_mappings_matched)

    def test_endo_008_policy_active_clinic_visit(self):
        # When endo008_policy is explicitly configured to 'clinic_visit', it escalates to Amber
        engine_approved = TriageEngine(endo008_policy="clinic_visit")
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 28,
            "period_pain_affects_daily_life": "yes",
            "deep_dyspareunia": "yes",
            "chronic_pelvic_pain_6plus_months": "no",
            "pelvic_mass_or_fullness": "no",
            "prior_endometriosis_treatment_failed": "no",
            "trying_to_conceive": "no",
        })
        res = engine_approved.evaluate(patient)
        self.assertEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)
        self.assertIn("ENDO-008", res.metadata.fired_rules)

    def test_unknown_never_auto_escalates_to_amber_rev2(self):
        # [REV-2] In PATH-ENDO-01, unknown deep dyspareunia, cyclical bowel/urinary symptoms, or treatment history
        # must NOT route directly to Amber. Unknown must return need_more_info.
        patient = dict(self._base_ruled_out_red_flags())
        patient.update({
            "age": 28,
            "period_pain_affects_daily_life": "yes",
            "deep_dyspareunia": "unknown",
            "cyclical_bowel_symptoms": "unknown",
            "chronic_pelvic_pain_6plus_months": "unknown",
        })
        res = self.engine.evaluate(patient)
        # Disabling period pain is present, but chronic pain and extragenital symptoms are unknown
        # Engine must not jump straight to Amber without clear physical exam indications
        self.assertNotEqual(res.urgency.level, UrgencyLevel.CLINIC_VISIT)


if __name__ == "__main__":
    unittest.main()

