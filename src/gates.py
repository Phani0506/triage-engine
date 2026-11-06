"""Deterministic evaluation of Safety Gates (GATE-001..GATE-006) and Day 3 Derived Variables."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class GateEvaluator:
    """Evaluates all Day 3 clinical safety gates and derived variables."""

    @staticmethod
    def evaluate_d10(patient: Dict[str, Any]) -> Any:
        """D10: Days between last unprotected sex and pregnancy test (P6 - P8)."""
        p6 = patient.get("days_since_last_unprotected_sex")
        p8 = patient.get("pregnancy_test_days_ago")

        try:
            p6_val = float(p6)
            p8_val = float(p8)
            if p6_val >= p8_val:
                return p6_val - p8_val
        except (ValueError, TypeError):
            pass
        return "unknown"

    @classmethod
    def evaluate_d1_gate_001(cls, patient: Dict[str, Any]) -> Tuple[Any, str]:
        """
        GATE-001 / D1: pregnancy_excluded.
        Precedence:
          1. Confirmed pregnant if test positive -> False
          2. Conclusive negative if test negative and D10 >= 21 -> True
          3. Sexual exposure ruled out (P4 == no and P5 == no) -> True
          4. Otherwise -> 'unknown'
        """
        p7 = patient.get("pregnancy_test_result")
        p4 = patient.get("pregnancy_possible")
        p5 = patient.get("unprotected_sex_in_last_12_months")
        d10 = cls.evaluate_d10(patient)

        if p7 == "positive":
            return False, "GATE-001: Pregnancy test is positive."

        if p4 == "no" and p5 == "no":
            return True, "GATE-001: Pregnancy excluded by sexual history (no possibility/exposure)."

        if p7 == "negative":
            if isinstance(d10, (int, float)) and d10 >= 21:
                return True, "GATE-001: Conclusive negative test (>= 21 days post-exposure)."
            # If tested too early (< 21 days) or interval unknown
            return "unknown", "GATE-001: Negative test taken < 21 days post-exposure or interval unknown (repeat test at >= 21 days required)."

        if p4 in ["yes", "not_sure"] or p5 == "yes":
            return "unknown", "GATE-001: Pregnancy is possible but test is not done or unknown."

        return "unknown", "GATE-001: Insufficient pregnancy history."

    @staticmethod
    def evaluate_d2_gate_002(patient: Dict[str, Any]) -> Tuple[str, str]:
        """
        GATE-002 / D2: age_cohort and demographic scope filter (18..40).
        """
        age = patient.get("age")
        try:
            age_val = float(age)
        except (ValueError, TypeError):
            return "unknown", "GATE-002: Age is missing or invalid."

        if age_val < 18 or age_val > 40:
            return "out_of_scope", f"GATE-002: Patient age {age_val} is outside reproductive target scope (18 to 40)."
        if age_val <= 25:
            return "18_25", "GATE-002: Young adult cohort (18-25)."
        if age_val <= 34:
            return "26_34", "GATE-002: Prime reproductive cohort (26-34)."
        return "35_40", "GATE-002: Later reproductive cohort (35-40)."

    @staticmethod
    def evaluate_d3_gate_003a(patient: Dict[str, Any]) -> Tuple[Any, str]:
        """
        GATE-003A / D3: cocp_washout_required (3-month pill washout for PCOS).
        """
        p9 = patient.get("contraceptive_method_type")
        p11 = patient.get("stopped_cocp_within_3_months")

        if p9 == "cocp_combined_pill" or p11 == "yes":
            return True, "GATE-003A: Active COCP or stopped < 3 months; hormonal washout required."
        if p9 not in ["cocp_combined_pill", "unknown"] and p11 == "no":
            return False, "GATE-003A: No recent COCP use."
        return "unknown", "GATE-003A: Contraceptive history incomplete."

    @staticmethod
    def evaluate_d4_gate_003b(patient: Dict[str, Any]) -> Tuple[Any, str]:
        """
        GATE-003B / D4: progestin_contraception_active.
        """
        p9 = patient.get("contraceptive_method_type")
        progestin_methods = ["progestin_pill", "progestin_implant", "hormonal_iud", "injection_depo"]

        if p9 in progestin_methods:
            return True, "GATE-003B: Active progestin-only contraception."
        if p9 != "unknown":
            return False, "GATE-003B: Not on progestin-only contraception."
        return "unknown", "GATE-003B: Contraceptive method unknown."

    @classmethod
    def evaluate_d5(cls, patient: Dict[str, Any]) -> Tuple[Any, str]:
        """D5: hormonal_cycle_interference (composite D3 OR D4)."""
        d3, _ = cls.evaluate_d3_gate_003a(patient)
        d4, _ = cls.evaluate_d4_gate_003b(patient)

        if d3 is True or d4 is True:
            return True, "D5: Exogenous hormonal contraception interferes with cycle evaluation."
        if d3 is False and d4 is False:
            return False, "D5: No exogenous hormonal cycle interference."
        return "unknown", "D5: Hormonal interference status unknown."

    @staticmethod
    def evaluate_d6_gate_004(patient: Dict[str, Any]) -> Tuple[Any, str]:
        """
        GATE-004 / D6: physiological_lactational_amenorrhea.
        Strict Formal LAM criteria (WHO MEC 2023 / FSRH):
          1. Infant strictly under 6 months postpartum (< 6m)
          2. Exclusively or nearly exclusively breastfeeding (P16 == yes)
          3. Menstruation has NOT returned (amenorrheic)
        """
        p15 = patient.get("postpartum_delivery_timing")
        p16 = patient.get("exclusively_breastfeeding")
        menses_returned = patient.get("menses_returned")
        days_since_period = patient.get("days_since_last_period")

        # Non-postpartum cases
        if p15 in ["no", "more_than_12_months_ago"]:
            return False, "GATE-004: Not within postpartum window."

        # Check menstruation return: if menses explicitly returned, formal LAM is broken
        if menses_returned == "yes":
            return False, "GATE-004: Menstruation has returned; formal contraceptive LAM no longer applies."

        # If recent period reported (e.g. within 56 days post-delivery)
        if isinstance(days_since_period, (int, float)) and days_since_period < 56 and p15 not in ["within_6_weeks"]:
            # Note: bleeding within first 6 weeks may be lochia; after 6 weeks, bleeding indicates menses return
            if menses_returned != "no":
                return False, "GATE-004: Bleeding episode after puerperium indicates return of menses."

        # Strict infant age check (< 6 months)
        lam_postpartum_windows = [
            "within_6_weeks",
            "6_to_12_weeks",
            "12_weeks_to_under_6_months",
            "12_weeks_to_6_months",  # backward compatible
        ]

        if p15 in lam_postpartum_windows:
            if p16 == "yes":
                if menses_returned == "no" or (isinstance(days_since_period, (int, float)) and days_since_period >= 56) or days_since_period == "unknown":
                    return True, "GATE-004: Formal LAM eligible (< 6 months postpartum, exclusive breastfeeding, amenorrheic)."
            if p16 == "no":
                return False, "GATE-004: Not exclusively breastfeeding; formal LAM does not apply."
            return "unknown", "GATE-004: Breastfeeding exclusivity unknown."

        # Extended postpartum lactation (>= 6 months to 12 months)
        if p15 in ["exactly_6_to_12_months", "6_to_12_months"]:
            if p16 == "yes":
                return False, "GATE-004: Infant >= 6 months; formal contraceptive LAM has expired (extended physiological lactational amenorrhea)."
            return False, "GATE-004: Infant >= 6 months and not exclusively breastfeeding."

        return "unknown", "GATE-004: Postpartum delivery timing unknown."

    @staticmethod
    def evaluate_d7_gate_005(patient: Dict[str, Any]) -> Tuple[Any, str]:
        """
        GATE-005 / D7: adult_gynecological_age (>= 3 years post-menarche).
        """
        p1 = patient.get("age")
        p2 = patient.get("never_had_period")
        p3 = patient.get("menarche_age")

        if p2 == "yes":
            return False, "GATE-005: Primary amenorrhea (never menstruated)."

        try:
            age_val = float(p1)
            menarche_val = float(p3)
            if (age_val - menarche_val) >= 3.0:
                return True, f"GATE-005: Adult gynecological age confirmed ({age_val - menarche_val:.0f} years post-menarche)."
            return False, f"GATE-005: Gynecologically immature (< 3 years post-menarche: {age_val - menarche_val:.0f} years)."
        except (ValueError, TypeError):
            pass

        return "unknown", "GATE-005: Menarche age unknown; cannot assume gynecological maturity."

    @staticmethod
    def evaluate_d8_gate_006(patient: Dict[str, Any]) -> Tuple[Any, str]:
        """GATE-006 / D8: sti_risk_present (context note only per DEC-11)."""
        p13 = patient.get("new_or_multiple_sexual_partners_past_12_months")
        if p13 == "yes":
            return True, "GATE-006: Partner history indicates STI risk factor."
        if p13 == "no":
            return False, "GATE-006: No partner-history STI risk factor reported."
        return "unknown", "GATE-006: STI risk partner history unknown."

    @staticmethod
    def evaluate_d11(patient: Dict[str, Any]) -> Tuple[Any, str]:
        """
        D11: reported_hemodynamic_instability.
        Syncope (P25) is direct instability.
        Resting tachycardia (P26) acts as early proxy when acute bleeding (P24) or severe pain (P19) is present.
        """
        p25 = patient.get("fainting_or_near_fainting")
        p26 = patient.get("racing_heartbeat_at_rest")
        p24 = patient.get("soaking_pad_hourly_2plus_hours")
        p19 = patient.get("acute_severe_pelvic_pain")

        if p25 == "yes":
            return True, "D11: Syncope or near-fainting reported."
        if p26 == "yes" and (p24 == "yes" or p19 == "yes"):
            return True, "D11: Resting tachycardia reported alongside acute bleeding or severe pain."

        if p25 == "no":
            if p26 == "no" or (p24 == "no" and p19 == "no"):
                return False, "D11: Hemodynamically stable by patient report."

        return "unknown", "D11: Vital stability proxy unknown."

    @staticmethod
    def evaluate_d14(patient: Dict[str, Any]) -> Tuple[Any, str]:
        """
        D14: pelvic_infection_severity_marker (CDC hospitalisation indicators).
        OR logic coded; pending clinical decision DEC-02.
        """
        p28 = patient.get("fever_over_38_5c")
        p30 = patient.get("feels_severely_unwell")
        p31 = patient.get("persistent_vomiting_cannot_keep_fluids_down")

        if p28 == "yes" or p30 == "yes" or p31 == "yes":
            markers = []
            if p28 == "yes":
                markers.append("fever > 38.5°C")
            if p30 == "yes":
                markers.append("severe prostration")
            if p31 == "yes":
                markers.append("persistent vomiting")
            return True, f"D14: Systemic infection severity markers present ({', '.join(markers)})."

        if p28 == "no" and p30 == "no" and p31 == "no":
            return False, "D14: No systemic toxicity markers reported."

        return "unknown", "D14: Systemic infection severity status unknown."

    @classmethod
    def evaluate_all(cls, patient: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Evaluates all Day 3 derived variables and returns (values_dict, explanations_dict)."""
        derived: Dict[str, Any] = {}
        explanations: Dict[str, str] = {}

        d10 = cls.evaluate_d10(patient)
        derived["unprotected_sex_to_test_interval_days"] = d10
        derived["D10"] = d10

        d1, exp1 = cls.evaluate_d1_gate_001(patient)
        derived["pregnancy_excluded"] = d1
        derived["D1"] = d1
        explanations["GATE-001"] = exp1

        d2, exp2 = cls.evaluate_d2_gate_002(patient)
        derived["age_cohort"] = d2
        derived["D2"] = d2
        explanations["GATE-002"] = exp2

        d3, exp3 = cls.evaluate_d3_gate_003a(patient)
        derived["cocp_washout_required"] = d3
        derived["D3"] = d3
        explanations["GATE-003A"] = exp3

        d4, exp4 = cls.evaluate_d4_gate_003b(patient)
        derived["progestin_contraception_active"] = d4
        derived["D4"] = d4
        explanations["GATE-003B"] = exp4

        d5, exp5 = cls.evaluate_d5(patient)
        derived["hormonal_cycle_interference"] = d5
        derived["D5"] = d5
        explanations["D5"] = exp5

        d6, exp6 = cls.evaluate_d6_gate_004(patient)
        derived["physiological_lactational_amenorrhea"] = d6
        derived["D6"] = d6
        explanations["GATE-004"] = exp6

        d7, exp7 = cls.evaluate_d7_gate_005(patient)
        derived["adult_gynecological_age"] = d7
        derived["D7"] = d7
        explanations["GATE-005"] = exp7

        d8, exp8 = cls.evaluate_d8_gate_006(patient)
        derived["sti_risk_present"] = d8
        derived["D8"] = d8
        explanations["GATE-006"] = exp8

        d11, exp11 = cls.evaluate_d11(patient)
        derived["reported_hemodynamic_instability"] = d11
        derived["D11"] = d11
        explanations["D11"] = exp11

        d14, exp14 = cls.evaluate_d14(patient)
        derived["pelvic_infection_severity_marker"] = d14
        derived["D14"] = d14
        explanations["D14"] = exp14

        return derived, explanations
