"""Deterministic, independent oracle-based synthetic patient case generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .loader import SchemaRegistry
from .models import OracleExpectation, SyntheticCase


@dataclass
class OracleBlueprint:
    blueprint_id: str
    topic: str  # red_flags, irregular_periods, pcos, endometriosis, fertility, multi_topic
    difficulty: str  # normal, borderline, complicated, high_risk, missing_info
    expected_level: str
    expected_colour: str
    expected_status: str
    expected_rule_ids: List[str]
    expected_reasons: List[str]
    oracle_source_note: str
    summary_template: List[str]
    inputs_factory: Callable[[random.Random], Tuple[Dict[str, Any], List[str]]]


def _base_healthy_inputs() -> Dict[str, Any]:
    """Base inputs representing a healthy asymptomatic reproductive-age woman."""
    return {
        "age": 26,
        "pregnancy_status": "not_pregnant",
        "pregnancy_test_result": "negative",
        "pregnancy_test_days_ago": 5,
        "days_since_last_unprotected_sex": 30,
        "contraceptive_method_type": "none",
        "stopped_cocp_within_3_months": "no",
        "currently_breastfeeding": "no",
        "menarche_age": 13,
        "days_since_last_period": 28,
        "cycle_length_days": 28,
        "cycles_per_year": 12,
        "cycle_variation_days": 2,
        "period_duration_days": 5,
        "never_had_period": "no",
        "trying_to_conceive": "no",
        "trying_duration_months": 0,
        "miscarriage_count": 0,
        "second_trimester_loss": "no",
        "prior_pid": "no",
        "prior_ectopic_pregnancy": "no",
        "prior_tubal_or_pelvic_surgery": "no",
        "unable_to_have_penetrative_intercourse": "no",
        "acute_severe_pelvic_pain": "no",
        "pelvic_pain_any": "no",
        "vaginal_bleeding_now": "no",
        "shoulder_tip_pain": "no",
        "soaking_pad_hourly_2plus_hours": "no",
        "fainting_or_near_fainting": "no",
        "racing_heartbeat_at_rest": "no",
        "passing_large_clots": "no",
        "self_reported_heavy_flow": "no",
        "bleeding_duration_days": 5,
        "fever_over_38_5c": "no",
        "feels_feverish_or_has_chills": "no",
        "feels_severely_unwell": "no",
        "persistent_vomiting_cannot_keep_fluids_down": "no",
        "foul_smelling_or_purulent_discharge": "no",
        "sudden_pain_with_vomiting": "no",
        "postpartum_delivery_timing": "none",
        "postpartum_heavy_or_increasing_bleeding_or_clots": "no",
        "period_pain_affects_daily_life": "no",
        "pain_starts_days_before_period": "no",
        "deep_dyspareunia": "no",
        "cyclical_bowel_symptoms": "no",
        "cyclical_urinary_symptoms": "no",
        "chronic_pelvic_pain_6plus_months": "no",
        "prior_endometriosis_treatment_failed": "no",
        "failed_first_line_pain_treatment": "no",
        "known_endometriosis": "no",
        "family_history_endometriosis": "no",
        "excess_facial_or_body_hair": "no",
        "hirsutism_excessive_hair": "no",
        "severe_or_persistent_acne": "no",
        "scalp_hair_thinning": "no",
        "rapid_virilization_signs": "no",
        "acanthosis_nigricans": "no",
        "bmi": 21.5,
        "intermenstrual_bleeding": "no",
        "intermenstrual_bleeding_cycles": 0,
        "postcoital_bleeding": "no",
        "unusual_fatigue": "no",
        "noticeable_pallor": "no",
        "breathless_on_mild_exertion": "no",
        "pelvic_mass_or_fullness": "no",
        "palpable_pelvic_lump": "no",
        "persistent_pelvic_pain_or_pressure": "no",
        "significant_weight_loss_or_heavy_training": "no",
        "partner_sti_symptoms_or_new_partner": "no",
        "recent_partner_change": "no",
    }


# =====================================================================
# CLINICIAN-AUTHORED BLUEPRINTS (Derived from Day 2 Excel Guidelines)
# =====================================================================

def bp_rf001_ectopic(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(22, 34),
        "pregnancy_status": "unknown",
        "pregnancy_test_result": "unknown",
        "acute_severe_pelvic_pain": "yes",
        "pelvic_pain_any": "yes",
        "days_since_last_period": rng.randint(45, 60),
    })
    return inputs, ["pregnancy_test_result", "pregnancy_status"]

def bp_rf002_shoulder_tip(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(23, 35),
        "shoulder_tip_pain": "yes",
        "acute_severe_pelvic_pain": "yes",
        "pelvic_pain_any": "yes",
        "vaginal_bleeding_now": "yes",
        "pregnancy_status": "unknown",
        "pregnancy_test_result": "unknown",
        "days_since_last_unprotected_sex": "unknown",
    })
    return inputs, ["pregnancy_status"]

def bp_rf003_pad_soaking_instability(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(20, 38),
        "soaking_pad_hourly_2plus_hours": "yes",
        "fainting_or_near_fainting": "yes",
        "vaginal_bleeding_now": "yes",
    })
    return inputs, []

def bp_rf007_torsion(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(19, 32),
        "acute_severe_pelvic_pain": "yes",
        "sudden_pain_with_vomiting": "yes",
        "pelvic_pain_any": "yes",
    })
    return inputs, []

def bp_rf008_postpartum_sepsis(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(22, 36),
        "postpartum_delivery_timing": "within_6_weeks",
        "postpartum_heavy_or_increasing_bleeding_or_clots": "yes",
        "fever_over_38_5c": "yes",
    })
    return inputs, []

def bp_pcos003_rotterdam_hirsutism(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(22, 32),
        "cycle_length_days": rng.randint(42, 55),
        "cycle_variation_days": 14,
        "cycles_per_year": 7,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "bmi": round(rng.uniform(21.0, 24.5), 1),
    })
    return inputs, []

def bp_pcos004_acne_alopecia(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(20, 29),
        "cycle_length_days": 46,
        "cycles_per_year": 7,
        "severe_or_persistent_acne": "yes",
        "moderate_severe_cystic_acne": "yes",
        "excess_facial_or_body_hair": "no",
        "hirsutism_excessive_hair": "no",
    })
    return inputs, []

def bp_pcos005_rapid_virilization(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(25, 34),
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "rapid_virilization_signs": "yes",
        "rapid_virilization": "yes",
        "cycle_length_days": 48,
        "cycles_per_year": 7,
    })
    return inputs, []

def bp_pcos006_regular_hirsutism(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(22, 35),
        "cycle_length_days": 29,
        "cycles_per_year": 12,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
    })
    return inputs, []

def bp_pcos007_cardiometabolic(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 28,
        "cycle_length_days": 50,
        "cycles_per_year": 6,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "bmi": 28.4,
        "acanthosis_nigricans": "yes",
    })
    return inputs, []

def bp_pcos009_healthy_green(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(21, 30),
        "cycle_length_days": 28,
        "cycles_per_year": 12,
        "cycle_variation_days": 2,
    })
    return inputs, []

def bp_pcos_borderline_gap91(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 26,
        "days_since_last_period": 95,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "bmi": 29.0,
        "acanthosis_nigricans": "yes",
    })
    return inputs, []

def bp_pcos_gate005_adolescent(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 19,
        "menarche_age": 17,
        "cycle_length_days": 42,
        "cycles_per_year": 7,
    })
    return inputs, []

def bp_pcos_bmi_boundary_indian(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 30,
        "cycle_length_days": 48,
        "cycles_per_year": 7,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "bmi": 23.4,
    })
    return inputs, []

def bp_pcos_with_pcb_cross_amber(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 28,
        "cycle_length_days": 45,
        "cycles_per_year": 7,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "postcoital_bleeding": "yes",
    })
    return inputs, []

def bp_pcos_uncertain_pregnancy_window(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 25,
        "days_since_last_period": 95,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "days_since_last_unprotected_sex": 12,
        "pregnancy_test_days_ago": 1,
        "pregnancy_status": "unknown",
        "pregnancy_test_result": "negative",
    })
    return inputs, []

def bp_pcos_cocp_washout(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 24,
        "contraceptive_method_type": "cocp_combined_pill",
        "cycle_length_days": 42,
        "cycles_per_year": 7,
    })
    return inputs, []

def bp_pcos_green_lockout_unknown_androgen(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 22,
        "severe_or_persistent_acne": "unknown",
        "scalp_hair_thinning": "unknown",
    })
    return inputs, ["severe_or_persistent_acne", "scalp_hair_thinning"]

def bp_pcos_unknown_rapid_virilization(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 31,
        "excess_facial_or_body_hair": "yes",
        "hirsutism_excessive_hair": "yes",
        "rapid_virilization_signs": "unknown",
        "rapid_virilization": "unknown",
    })
    return inputs, ["rapid_virilization_signs"]

# Endometriosis Blueprints
def bp_endo001_healthy_green(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(22, 34),
        "period_pain_affects_daily_life": "no",
        "deep_dyspareunia": "no",
        "cyclical_bowel_symptoms": "no",
        "chronic_pelvic_pain_6plus_months": "no",
    })
    return inputs, []

def bp_endo002_dysmenorrhea_yellow(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(21, 33),
        "period_pain_affects_daily_life": "yes",
        "deep_dyspareunia": "no",
        "cyclical_bowel_symptoms": "no",
        "failed_first_line_pain_treatment": "no",
    })
    return inputs, []

def bp_endo003_deep_dyspareunia_yellow(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(24, 35),
        "deep_dyspareunia": "yes",
        "cyclical_bowel_symptoms": "yes",
        "failed_first_line_pain_treatment": "no",
    })
    return inputs, []

def bp_endo004_chronic_pain_amber(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(25, 38),
        "chronic_pelvic_pain_6plus_months": "yes",
    })
    return inputs, []

def bp_endo005_failed_treatment_amber(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(23, 36),
        "period_pain_affects_daily_life": "yes",
        "failed_first_line_pain_treatment": "yes",
    })
    return inputs, []

def bp_endo006_subfertility_amber(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(27, 36),
        "trying_to_conceive": "yes",
        "trying_duration_months": 4,
        "period_pain_affects_daily_life": "yes",
    })
    return inputs, []

# Fertility Blueprints
def bp_fert001_normal_window_green(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(23, 33),
        "trying_to_conceive": "yes",
        "trying_duration_months": rng.randint(2, 8),
    })
    return inputs, []

def bp_fert002_age_under35_trying12m(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(24, 34),
        "trying_to_conceive": "yes",
        "trying_duration_months": rng.randint(12, 18),
    })
    return inputs, []

def bp_fert003_age_ge35_trying6m(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(35, 40),
        "trying_to_conceive": "yes",
        "trying_duration_months": rng.randint(6, 10),
    })
    return inputs, []

def bp_fert004_age36to40_trying_under6m(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(36, 40),
        "trying_to_conceive": "yes",
        "trying_duration_months": rng.randint(2, 5),
    })
    return inputs, []

def bp_fert005_ovulatory_dysfunction(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(24, 34),
        "trying_to_conceive": "yes",
        "trying_duration_months": 3,
        "typical_cycle_length_days": 48,
        "periods_in_past_year": 7,
    })
    return inputs, []

def bp_fert006_tubal_risk(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(26, 36),
        "trying_to_conceive": "yes",
        "trying_duration_months": 2,
        "prior_ectopic_pregnancy": "yes",
    })
    return inputs, []

def bp_fert007_recurrent_loss(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(26, 38),
        "trying_to_conceive": "yes",
        "trying_duration_months": 4,
        "miscarriage_count": 2,
    })
    return inputs, []

def bp_fert008_coital_difficulty(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(23, 34),
        "trying_to_conceive": "yes",
        "trying_duration_months": 5,
        "unable_to_have_penetrative_intercourse": "yes",
    })
    return inputs, []

def bp_fert_age35_trying_under6m_pending(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": 35,
        "trying_to_conceive": "yes",
        "trying_duration_months": 4,
    })
    return inputs, []

# Irregular Periods Blueprints
def bp_irr004_secondary_amenorrhea(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(22, 34),
        "days_since_last_period": 105,
    })
    return inputs, []

def bp_irr005_uncomplicated_hmb(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(23, 37),
        "bleeding_soaks_pad_hourly": "yes",
        "fatigue_or_breathlessness_with_bleeding": "no",
    })
    return inputs, []

def bp_irr008_postcoital_bleeding(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(24, 38),
        "postcoital_bleeding": "yes",
    })
    return inputs, []

def bp_irr009_hmb_anemia(rng: random.Random) -> Tuple[Dict[str, Any], List[str]]:
    inputs = _base_healthy_inputs()
    inputs.update({
        "age": rng.randint(25, 39),
        "bleeding_soaks_pad_hourly": "yes",
        "fatigue_or_breathlessness_with_bleeding": "yes",
    })
    return inputs, []


ALL_BLUEPRINTS: List[OracleBlueprint] = [
    # Red Flags
    OracleBlueprint("BP-RF-001", "red_flags", "high_risk", "emergency", "red", "complete", ["RF-001"], ["Acute severe pain with missed period and pregnancy not excluded"], "NICE NG126 / FOGSI", ["28-year-old female presenting with acute severe lower abdominal pain.", "Missed period by 3 weeks, no recent pregnancy test taken.", "Reports pain is sharp, constant, and worsening over the past 4 hours."], bp_rf001_ectopic),
    OracleBlueprint("BP-RF-002", "red_flags", "high_risk", "emergency", "red", "complete", ["RF-002"], ["Shoulder-tip pain indicating diaphragmatic peritonism"], "NICE NG126 / RCOG GTG 21", ["30-year-old female with sudden right shoulder-tip pain.", "Associated with lower pelvic pain and abnormal vaginal bleeding.", "Feeling lightheaded upon standing and noticeably pale."], bp_rf002_shoulder_tip),
    OracleBlueprint("BP-RF-003", "red_flags", "high_risk", "emergency", "red", "complete", ["RF-003", "RF-004"], ["Hourly pad soaking with fainting / instability"], "FIGO AUB / NICE NG88", ["26-year-old female soaking through pads every hour for 3 hours.", "Reports episode of fainting (syncope) and dizziness.", "Passing large clots with resting heart rate feeling rapid."], bp_rf003_pad_soaking_instability),
    OracleBlueprint("BP-RF-007", "red_flags", "high_risk", "emergency", "red", "complete", ["RF-007"], ["Acute severe pelvic pain with repeated vomiting"], "RCOG Green-top / ACOG", ["23-year-old female with abrupt onset of severe unilateral pain.", "Accompanied by persistent vomiting and nausea.", "Unable to keep fluids down with severe localized pelvic tenderness."], bp_rf007_torsion),
    OracleBlueprint("BP-RF-008", "red_flags", "high_risk", "emergency", "red", "complete", ["RF-008"], ["Postpartum heavy bleeding with high fever"], "WHO Postpartum Hemorrhage / Sepsis", ["29-year-old female 3 weeks postpartum.", "Sudden onset heavy vaginal clots accompanied by fever.", "High fever (38.8°C), chills, and feeling severely unwell."], bp_rf008_postpartum_sepsis),

    # PCOS
    OracleBlueprint("BP-PCOS-003", "pcos", "normal", "teleconsultation", "yellow", "complete", ["PCOS-003"], ["Adult Rotterdam criteria with clinical hirsutism"], "2023 International PCOS Guideline Rec 1.1.1 & 1.3.1", ["24-year-old female with 48-day menstrual cycle gaps.", "Excess coarse facial hair on chin and upper lip.", "Not pregnant and not currently using hormonal contraception."], bp_pcos003_rotterdam_hirsutism),
    OracleBlueprint("BP-PCOS-004", "pcos", "normal", "teleconsultation", "yellow", "complete", ["PCOS-004"], ["Irregular cycles with persistent cystic acne"], "2023 International PCOS Guideline Rec 1.3.2", ["25-year-old female with 45-day cycle gaps.", "Severe cystic acne refractory to topical care; no hirsutism.", "Skin breakouts persisting despite 6 months of over-the-counter washes."], bp_pcos004_acne_alopecia),
    OracleBlueprint("BP-PCOS-005", "pcos", "high_risk", "clinic_visit", "amber", "complete", ["PCOS-005"], ["Rapid virilization signs screening for androgen-secreting neoplasm"], "2023 International PCOS Guideline Rec 1.3.1", ["27-year-old female reporting rapid facial hair growth over 4 months.", "Associated deepening of voice and temporal hair thinning.", "Previously had regular monthly cycles with no prior hair growth."], bp_pcos005_rapid_virilization),
    OracleBlueprint("BP-PCOS-006", "pcos", "normal", "teleconsultation", "yellow", "complete", ["PCOS-006"], ["Regular cycles with marked clinical hirsutism"], "2023 International PCOS Guideline Rec 1.3.1", ["29-year-old female with regular 28-day periods.", "Noticeable coarse excess body and facial hair.", "Mild persistent acne on jawline without signs of virilization."], bp_pcos006_regular_hirsutism),
    OracleBlueprint("BP-PCOS-007", "pcos", "complicated", "teleconsultation", "yellow", "complete", ["PCOS-003", "PCOS-007"], ["PCOS features with cardiometabolic risk markers"], "2023 PCOS Guideline & ICMR Indian Guidelines", ["28-year-old female with 50-day cycle intervals.", "Excess facial hair, BMI 28.4 kg/m2, acanthosis nigricans.", "Dark velvety patches observed on the posterior neck and axillae."], bp_pcos007_cardiometabolic),
    OracleBlueprint("BP-PCOS-009", "pcos", "normal", "self_care", "green", "complete", ["PCOS-009"], ["Regular cycles with no clinical signs of hyperandrogenism"], "2023 International PCOS Guideline", ["23-year-old female with predictable 28-day cycles.", "No hirsutism, cystic acne, or alopecia.", "No pelvic pain or abnormal bleeding; tracking cycles on mobile app."], bp_pcos009_healthy_green),

    # Borderline & Interactions
    OracleBlueprint("BP-PCOS-GAP91", "pcos", "borderline", "teleconsultation", "yellow", "complete", ["PCOS-002", "PCOS-003", "PCOS-007", "PCOS-008"], ["Single cycle gap > 90 days with PCOS features and endometrial protection alert"], "2023 PCOS Guideline & Task Brief Patient A", ["26-year-old female with no period for 95 days (negative pregnancy test).", "Facial hirsutism, BMI 29, dark skin velvety patches.", "Prolonged amenorrhea following previously irregular cycles."], bp_pcos_borderline_gap91),
    OracleBlueprint("BP-PCOS-GATE005", "pcos", "borderline", "teleconsultation", "yellow", "complete", ["IRR-003", "GATE-005"], ["Adolescent gynecological axis maturity boundary (< 3 years post-menarche) with oligomenorrhea"], "2023 PCOS Guideline Section 1.2", ["19-year-old female, menarche at 17 (gynecological age 2 years).", "Cycles 42 days apart.", "No excessive body hair, severe acne, or significant pelvic pain."], bp_pcos_gate005_adolescent),
    OracleBlueprint("BP-PCOS-BMI-INDIAN", "pcos", "borderline", "teleconsultation", "yellow", "complete", ["PCOS-003", "PCOS-007"], ["PCOS with Indian BMI boundary marker (23.4 kg/m2)"], "ICMR / FOGSI Consensus Guidelines (DEC-06)", ["30-year-old female with 48-day cycle variation and mild hirsutism.", "BMI 23.4 kg/m2 (South Asian background).", "Family history of early-onset type 2 diabetes mellitus."], bp_pcos_bmi_boundary_indian),
    OracleBlueprint("BP-PCOS-PCB-CROSS", "multi_topic", "complicated", "clinic_visit", "amber", "complete", ["IRR-008"], ["PCOS signs with co-occurring postcoital bleeding"], "NICE NG12 / FOGSI Cervical Health", ["28-year-old female with irregular periods and mild hirsutism.", "Reports bleeding after sexual intercourse on multiple occasions.", "Intermenstrual spotting noted across the last two menstrual cycles."], bp_pcos_with_pcb_cross_amber),

    # Uncertainty & Missing Inputs
    OracleBlueprint("BP-PCOS-UNCERTAIN-PREG", "pcos", "missing_info", "none", "none", "need_more_info", ["GATE-001"], ["Uncertain pregnancy exclusion due to early test window (D10 < 21 days)"], "FSRH / NICE NG126 Window Rule", ["25-year-old female with 95 days since last period.", "Negative urine test done only 12 days after unprotected sex.", "Sexual exposure occurred less than two weeks prior to testing."], bp_pcos_uncertain_pregnancy_window),
    OracleBlueprint("BP-PCOS-COCP-WASHOUT", "pcos", "missing_info", "none", "none", "need_more_info", ["GATE-003A"], ["Active or recent combined oral contraception masking endogenous cycle"], "2023 PCOS Guideline Rec 1.1.2", ["24-year-old female currently on combined oral contraceptive pill.", "Seeking evaluation for irregular cycles experienced prior to pill use.", "Wants to know about hormonal testing while on oral contraception."], bp_pcos_cocp_washout),
    OracleBlueprint("BP-PCOS-GREEN-LOCKOUT", "pcos", "missing_info", "none", "none", "need_more_info", [], ["Strict Green lockout triggered by unknown acne/alopecia inputs"], "System Safety Invariant", ["22-year-old female with regular cycles.", "Acne severity and hair thinning status unconfirmed.", "Did not provide details on skin changes or family history."], bp_pcos_green_lockout_unknown_androgen),
    OracleBlueprint("BP-PCOS-UNKNOWN-VIRIL", "pcos", "missing_info", "none", "none", "need_more_info", ["PCOS-005"], ["Unknown rapid virilization in patient with hirsutism requires follow-up safety questions"], "Clinical Risk Mitigation Principle", ["31-year-old female with noticeable facial hirsutism.", "Speed of onset and voice deepening unknown.", "Onset timeline and progression rate of excess hair growth uncharacterized."], bp_pcos_unknown_rapid_virilization),

    # Endometriosis
    OracleBlueprint("BP-ENDO-001", "endometriosis", "normal", "self_care", "green", "complete", ["ENDO-001"], ["Normal menstruation without chronic or disabling pelvic pain"], "NICE NG73 (2024)", ["24-year-old female with mild cyclical cramping not disrupting daily life.", "No deep pain, chronic pain, or cyclical bowel/urinary symptoms.", "Pain easily relieved with occasional over-the-counter paracetamol."], bp_endo001_healthy_green),
    OracleBlueprint("BP-ENDO-002", "endometriosis", "normal", "teleconsultation", "yellow", "complete", ["ENDO-002"], ["Disabling cyclical dysmenorrhea without deep infiltrative signs"], "NICE NG73 Rec 1.3.1", ["22-year-old female with severe period pain missing college classes.", "No deep dyspareunia or bowel/urinary symptoms; treatment naive.", "Severe cramping starting 1-2 days before bleeding each cycle."], bp_endo002_dysmenorrhea_yellow),
    OracleBlueprint("BP-ENDO-003", "endometriosis", "normal", "teleconsultation", "yellow", "complete", ["ENDO-003"], ["Deep dyspareunia and cyclical bowel symptoms"], "NICE NG73 Rec 1.3.1 & 1.3.2", ["27-year-old female with sharp pain on deep intercourse.", "Cyclical painful defecation during menstruation.", "Painful bowel movements coinciding strictly with menstrual period."], bp_endo003_deep_dyspareunia_yellow),
    OracleBlueprint("BP-ENDO-004", "endometriosis", "complicated", "clinic_visit", "amber", "complete", ["ENDO-004"], ["Chronic non-cyclical pelvic pain lasting over 6 months"], "NICE NG73 Rec 1.3.1 / RCOG", ["28-year-old female with persistent lower pelvic pain for 8 months.", "Daily dull ache unrelated to menstrual bleeding.", "Pelvic discomfort present almost daily for over half a year."], bp_endo004_chronic_pain_amber),
    OracleBlueprint("BP-ENDO-005", "endometriosis", "complicated", "clinic_visit", "amber", "complete", ["ENDO-005"], ["Suspected endometriosis refractory to 3-month medical therapy"], "NICE NG73 Rec 1.4.3", ["26-year-old female with disabling dysmenorrhea.", "Symptoms unimproved after 4 months on continuous oral progestin.", "Severe cramping and pelvic aching persisting despite hormonal therapy."], bp_endo005_failed_treatment_amber),
    OracleBlueprint("BP-ENDO-006", "endometriosis", "complicated", "clinic_visit", "amber", "complete", ["ENDO-006"], ["Suspected endometriosis in a patient trying to conceive"], "NICE NG73 Rec 1.3.3 & ESHRE 2022", ["30-year-old female actively trying to conceive for 4 months.", "Significant dysmenorrhea and cyclical pelvic pain.", "Seeking conception while experiencing worsening monthly menstrual pain."], bp_endo006_subfertility_amber),

    # Fertility
    OracleBlueprint("BP-FERT-001", "fertility", "normal", "self_care", "green", "complete", ["FERT-001"], ["Trying to conceive under 12 months, age under 35, zero risk factors"], "NICE NG257 Rec 1.1.1", ["27-year-old female trying to conceive for 5 months.", "Regular cycles, no prior surgery, pelvic infections, or losses.", "Both partners healthy with no known reproductive health conditions."], bp_fert001_normal_window_green),
    OracleBlueprint("BP-FERT-002", "fertility", "normal", "teleconsultation", "yellow", "complete", ["FERT-002"], ["Formal subfertility investigation threshold reached (age < 35, >= 12m)"], "NICE NG257 Rec 1.2.1 / ASRM", ["31-year-old female trying to conceive for 14 months without success.", "Regular cycles, general health normal.", "Trying to conceive with regular intercourse for over one year."], bp_fert002_age_under35_trying12m),
    OracleBlueprint("BP-FERT-003", "fertility", "normal", "teleconsultation", "yellow", "complete", ["FERT-003"], ["ASRM evaluation threshold reached (age >= 35, >= 6m trying)"], "ASRM Committee Opinion 2022 / NICE NG257", ["36-year-old female trying to conceive for 7 months.", "No known pelvic pathologies.", "Trying to conceive for over six months at maternal age 36."], bp_fert003_age_ge35_trying6m),
    OracleBlueprint("BP-FERT-004", "fertility", "borderline", "teleconsultation", "yellow", "complete", ["FERT-004"], ["Age 36-40 trying < 6 months earlier specialist consultation (proposed mapping)"], "NICE NG257 Rec 1.2.2 (DEC-09)", ["38-year-old female trying to conceive for 3 months.", "Regular menses, no acute symptoms.", "Maternal age 38, inquiring about timeline for fertility assessments."], bp_fert004_age36to40_trying_under6m),
    OracleBlueprint("BP-FERT-005", "fertility", "complicated", "teleconsultation", "yellow", "complete", ["FERT-005"], ["Subfertility with co-occurring ovulatory dysfunction / oligomenorrhea"], "NICE NG257 Rec 1.2.3 & 2023 PCOS Guideline", ["28-year-old female trying to conceive for 3 months.", "Cycles 48 days apart, infrequent ovulation.", "Infrequent menstrual periods since stopping barrier contraception."], bp_fert005_ovulatory_dysfunction),
    OracleBlueprint("BP-FERT-006", "fertility", "complicated", "clinic_visit", "amber", "complete", ["FERT-006"], ["Subfertility with tubal risk history (prior ectopic pregnancy)"], "NICE NG257 Rec 1.2.3", ["30-year-old female trying to conceive for 2 months.", "History of salpingectomy for ruptured ectopic pregnancy 3 years ago.", "Single remaining fallopian tube following prior ectopic surgery."], bp_fert006_tubal_risk),
    OracleBlueprint("BP-FERT-007", "fertility", "complicated", "clinic_visit", "amber", "complete", ["FERT-007"], ["Recurrent pregnancy loss threshold reached (>= 2 losses)"], "ESHRE Guideline RPL 2023 / ASRM (DEC-10)", ["32-year-old female trying to conceive with history of 2 consecutive miscarriages.", "Both previous pregnancies lost in first trimester.", "Regular cycles, inquiring about evaluations after recurrent losses."], bp_fert007_recurrent_loss),
    OracleBlueprint("BP-FERT-008", "fertility", "complicated", "clinic_visit", "amber", "complete", ["FERT-008"], ["Subfertility associated with inability to have penetrative intercourse"], "NICE NG257 Rec 1.1.2 & FOGSI", ["26-year-old female trying to conceive for 5 months.", "Severe vaginismus / dyspareunia preventing penetrative intercourse.", "Unable to achieve penetrative intercourse due to severe coital pain."], bp_fert008_coital_difficulty),
    OracleBlueprint("BP-FERT-AGE35-PENDING", "fertility", "borderline", "none", "none", "clinical_decision_required", [], ["Age 35 trying < 6 months halts at explicit pending clinical decision terminal"], "Pending Decision DEC-09", ["35-year-old female trying to conceive for 4 months.", "Regular 28-day cycles, no prior surgeries or infections.", "Age 35 presenting after four months of pregnancy attempts."], bp_fert_age35_trying_under6m_pending),

    # Irregular Periods
    OracleBlueprint("BP-IRR-004", "irregular_periods", "normal", "teleconsultation", "yellow", "complete", ["IRR-004"], ["Secondary amenorrhea exceeding 90 days with negative pregnancy test"], "FIGO Menstrual Disorders / NICE", ["26-year-old female, 105 days since last period.", "Confirmed negative home pregnancy test 25 days post-exposure.", "Over three months of amenorrhea with negative pregnancy test."], bp_irr004_secondary_amenorrhea),
    OracleBlueprint("BP-IRR-005", "irregular_periods", "normal", "teleconsultation", "yellow", "complete", ["IRR-005"], ["Uncomplicated heavy menstrual bleeding without red flags"], "NICE NG88 Heavy Menstrual Bleeding", ["30-year-old female with heavy periods soaking pads hourly.", "No syncope, dizziness, or symptomatic anemia.", "Menstrual flow lasting 8 days with heavy bleeding on days 2-4."], bp_irr005_uncomplicated_hmb),
    OracleBlueprint("BP-IRR-008", "irregular_periods", "complicated", "clinic_visit", "amber", "complete", ["IRR-008"], ["Postcoital bleeding requiring cervical evaluation"], "NICE NG12 Cervical Cancer Referral Guidelines", ["32-year-old female with repeated bleeding following sexual intercourse.", "No heavy pelvic pain.", "Fresh spotting observed on toilet paper after intercourse on multiple occasions."], bp_irr008_postcoital_bleeding),
    OracleBlueprint("BP-IRR-009", "irregular_periods", "complicated", "clinic_visit", "amber", "complete", ["IRR-009"], ["Heavy menstrual bleeding with signs of symptomatic anemia"], "NICE NG88 Rec 1.2.6 / FOGSI", ["34-year-old female with heavy prolonged menstrual flow.", "Marked fatigue, breathlessness on climbing stairs, and pallor.", "Noticeable weakness and shortness of breath during heavy flow days."], bp_irr009_hmb_anemia),
]


class SyntheticPatientGenerator:
    """Generates schema-conforming synthetic cases using independent clinical blueprints."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_case_from_blueprint(
        self,
        blueprint: OracleBlueprint,
        case_id: str,
        collection: str,
        batch_id: Optional[str] = None,
    ) -> SyntheticCase:
        patient_inputs, missing_fields = blueprint.inputs_factory(self.rng)

        oracle = OracleExpectation(
            expected_level=blueprint.expected_level,
            expected_colour=blueprint.expected_colour,
            expected_status=blueprint.expected_status,
            expected_rule_ids=blueprint.expected_rule_ids,
            expected_reasons=blueprint.expected_reasons,
            oracle_source_note=blueprint.oracle_source_note,
        )

        case = SyntheticCase(
            case_id=case_id,
            collection=collection,
            batch_id=batch_id,
            topic=blueprint.topic,
            difficulty=blueprint.difficulty,
            patient_summary_lines=blueprint.summary_template,
            patient_inputs=patient_inputs,
            missing_or_unknown_fields=missing_fields,
            oracle=oracle,
            synthetic=True,
        )
        data_hash = hashlib.sha256(
            json.dumps({"inputs": patient_inputs, "oracle": oracle.to_dict()}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        case.case_sha256 = data_hash
        return case

    def generate_batch1_cases(self) -> List[SyntheticCase]:
        """Generate the canonical 18-case Batch 1 (Red Flags + PCOS) matching Section 17.1."""
        target_ids = [
            # 5 Red Flags
            ("BATCH1-001", "BP-RF-001"),
            ("BATCH1-002", "BP-RF-002"),
            ("BATCH1-003", "BP-RF-003"),
            ("BATCH1-004", "BP-RF-007"),
            ("BATCH1-005", "BP-RF-008"),
            # 5 Straightforward PCOS
            ("BATCH1-006", "BP-PCOS-003"),
            ("BATCH1-007", "BP-PCOS-005"),
            ("BATCH1-008", "BP-PCOS-006"),
            ("BATCH1-009", "BP-PCOS-009"),
            ("BATCH1-010", "BP-PCOS-004"),
            # 4 Borderline / Multi-Rule Interactions
            ("BATCH1-011", "BP-PCOS-GAP91"),
            ("BATCH1-012", "BP-PCOS-GATE005"),
            ("BATCH1-013", "BP-PCOS-BMI-INDIAN"),
            ("BATCH1-014", "BP-PCOS-PCB-CROSS"),
            # 4 Uncertainty / Missing-Information
            ("BATCH1-015", "BP-PCOS-UNCERTAIN-PREG"),
            ("BATCH1-016", "BP-PCOS-COCP-WASHOUT"),
            ("BATCH1-017", "BP-PCOS-GREEN-LOCKOUT"),
            ("BATCH1-018", "BP-PCOS-UNKNOWN-VIRIL"),
            # 1 Additional PCOS (Metabolic)
            ("BATCH1-019", "BP-PCOS-007"),
            # 6 Endometriosis
            ("BATCH1-020", "BP-ENDO-001"),
            ("BATCH1-021", "BP-ENDO-002"),
            ("BATCH1-022", "BP-ENDO-003"),
            ("BATCH1-023", "BP-ENDO-004"),
            ("BATCH1-024", "BP-ENDO-005"),
            ("BATCH1-025", "BP-ENDO-006"),
            # 9 Fertility / Subfertility
            ("BATCH1-026", "BP-FERT-001"),
            ("BATCH1-027", "BP-FERT-002"),
            ("BATCH1-028", "BP-FERT-003"),
            ("BATCH1-029", "BP-FERT-004"),
            ("BATCH1-030", "BP-FERT-005"),
            ("BATCH1-031", "BP-FERT-006"),
            ("BATCH1-032", "BP-FERT-007"),
            ("BATCH1-033", "BP-FERT-008"),
            ("BATCH1-034", "BP-FERT-AGE35-PENDING"),
            # 4 Irregular Bleeding / AUB
            ("BATCH1-035", "BP-IRR-004"),
            ("BATCH1-036", "BP-IRR-005"),
            ("BATCH1-037", "BP-IRR-008"),
            ("BATCH1-038", "BP-IRR-009"),
        ]

        bp_map = {bp.blueprint_id: bp for bp in ALL_BLUEPRINTS}
        cases: List[SyntheticCase] = []
        for case_id, bp_id in target_ids:
            bp = bp_map[bp_id]
            cases.append(self.generate_case_from_blueprint(bp, case_id, "exam", batch_id="batch1"))
        return cases

    def generate_collection(
        self,
        collection: str,
        count: int,
        topic_filter: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> List[SyntheticCase]:
        blueprints = ALL_BLUEPRINTS
        if topic_filter:
            blueprints = [bp for bp in blueprints if bp.topic == topic_filter]
        if not blueprints:
            blueprints = ALL_BLUEPRINTS

        prefix = "PRAC-" if collection == "practice" else "EXAM-"
        cases: List[SyntheticCase] = []
        for i in range(1, count + 1):
            bp = blueprints[(i - 1) % len(blueprints)]
            case_id = f"{prefix}{i:03d}"
            cases.append(self.generate_case_from_blueprint(bp, case_id, collection, batch_id))
        return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic Patient Case Generator")
    parser.add_argument("--collection", choices=["practice", "exam"], default="practice")
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--batch-id", type=str, default=None)
    parser.add_argument("--topic", type=str, default=None)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--save-db", action="store_true", help="Save directly into SQLite CaseStore")
    args = parser.parse_args()

    gen = SyntheticPatientGenerator(seed=101)

    if args.batch_id == "batch1":
        cases = gen.generate_batch1_cases()
        out_path = args.out or "data/cases/batch1_cases.json"
    else:
        cases = gen.generate_collection(
            collection=args.collection,
            count=args.count,
            topic_filter=args.topic,
            batch_id=args.batch_id or ("default_prac" if args.collection == "practice" else "default_exam"),
        )
        out_path = args.out or f"data/cases/{args.collection}_cases.json"

    # Save to JSON
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([c.to_dict(include_oracle=True) for c in cases], f, indent=2)
    print(f"Successfully generated {len(cases)} cases -> {out_path}")

    # Optionally populate CaseStore
    if args.save_db:
        from .case_store import CaseStore
        store = CaseStore()
        for c in cases:
            store.save_synthetic_case(c)
        print(f"Committed {len(cases)} cases to database: {store.db_path}")


if __name__ == "__main__":
    main()

