# Women's Health Clinical Risk Triage Engine (v0.1 Foundation — Day 3)

A deterministic, offline, evidence-backed clinical risk triage engine for women's reproductive health (calibrated for women aged 18–40).

> [!IMPORTANT]
> **Codebase Isolation Guarantee:**
> This triage engine lives inside `` as a standalone, self-contained Python module. It has zero coupling, zero imports, and zero dependencies on the legacy `server/triage/` codebase or active production routes. All evaluations are 100% deterministic, offline, and operate without an LLM or external AI API.

---

## 1. Clinical Scope & Target Population

* **Target Population:** Reproductive-aged individuals (18 to 40 years).
* **Non-Diagnostic Scope:** This engine performs **urgency triage and clinical risk stratification only**, sorting presentations into 4 clinical urgency levels to guide care navigation. It does NOT diagnose medical conditions or prescribe therapeutic regimens.
* **Separation of Concerns:** 
  * Clinical urgency (`level`: `emergency`, `clinic_visit`, `teleconsultation`, `self_care`, `none`) is strictly separated from processing status (`status`: `complete`, `need_more_info`, `out_of_scope`, `clinical_decision_required`, `deferred`).
  * Clinician physical examination requirements (`needs_physical_exam`, `physical_exam_reason`) are kept strictly separated from non-prescriptive patient advisory text (`doctor_may_suggest`).

---

## 2. Directory Structure

```text

├── README.md                      # Comprehensive architecture, setup, rules, and governance guide
├── pyproject.toml                 # Packaging, Python >= 3.10 runtime specification
├── rules/
│   ├── inputs_schema.yaml         # 86 validated variables (72 patient P1..P72 + 14 derived D1..D14)
│   ├── rules.yaml                 # 31 rule entries (22 baseline clinical + 7 gates + 2 candidates)
│   └── pathways.yaml              # Decision trees (PATH-AMEN-01 and PATH-HMB-01)
├── src/
│   ├── __init__.py                # Package exports: evaluate_patient, get_engine, TriageEngine
│   ├── cli.py                     # Offline CLI runner (JSON payload / file input, policy flags)
│   ├── engine.py                  # Orchestrator: Red Flags -> Gates -> Pathways -> Rules -> Resolver
│   ├── evaluator.py               # 3-valued condition evaluator (TRUE, FALSE, UNKNOWN)
│   ├── gates.py                   # Pure evaluation of Gates 1-6 and Day 3 derived variables
│   ├── loader.py                  # Strict YAML loaders and SchemaRegistry
│   ├── models.py                  # Pure dataclasses and Enums (TriageResult, UrgencyLevel, etc.)
│   └── pathways.py                # Decision tree runner with safety routing and Day 4 deferrals
└── tests/
    ├── __init__.py
    ├── test_gates.py              # 7 unit & boundary tests for Gates 1-6, D1-D8, D10, D11, D14
    ├── test_red_flags.py          # 10 unit tests for RF-001..RF-008, RF-009, policies & priority
    ├── test_irregular.py          # 15 tests for IRR-001..IRR-013, FIGO age boundaries & IRR-012
    ├── test_pathways_day3.py      # 14 branch tests for PATH-AMEN-01 and PATH-HMB-01
    └── test_engine_safety.py      # 5 safety invariant tests (Green lockout, Red lock-in, non-prescriptive text)
```

---

## 3. Installation & Setup

### Requirements:
* Python 3.10+ (tested and verified on Python 3.14.4).
* Standard libraries + `PyYAML` (`>= 6.0`).

### Quick Setup:
```bash
# From the repository root:
python3 -m unittest discover -s tests
```

---

## 4. CLI & Python API Usage

### 4.1. Command Line Interface (CLI)
You can run single patient evaluations directly via JSON string or file:

```bash
# Evaluate via inline JSON:
python3 -m src.cli '{"age": 25, "days_since_last_period": 110, "never_had_period": "no", "pregnancy_test_result": "negative", "days_since_last_unprotected_sex": 30, "pregnancy_test_days_ago": 5, "contraceptive_method_type": "none", "stopped_cocp_within_3_months": "no", "palpable_pelvic_lump": "no", "persistent_pelvic_pain_or_pressure": "no", "postpartum_delivery_timing": "no"}'

# Evaluate with clinical policy flags:
python3 -m src.cli patient.json --rf006-policy emergency --rf005-policy single_marker_emergency

# Enable candidate gap rules (RF-009, EP-001):
python3 -m src.cli patient.json --enable-candidate-rules
```

### 4.2. Python API
```python
from src import evaluate_patient

patient_data = {
    "age": 28,
    "self_reported_heavy_flow": "yes",
    "soaking_pad_hourly_2plus_hours": "yes",
    "fainting_or_near_fainting": "yes",
}

result = evaluate_patient(patient_data)
print(result["status"])        # "complete"
print(result["urgency"])       # {"level": "emergency", "colour": "red", ...}
print(result["reasons"])       # [{"rule": "RF-003", ...}, {"rule": "RF-004", ...}]
```

---

## 5. Core Engine Mechanics & Safety Invariants

### 5.1. Three-Valued Logic (`TRUE`, `FALSE`, `UNKNOWN`)
* Standard Boolean evaluations fail in clinical triage when a patient has not yet answered a safety question.
* The engine evaluates predicates to `TriState.TRUE`, `TriState.FALSE`, or `TriState.UNKNOWN`.
* Combinators follow Kleene 3-valued logic:
  * `all`: Returns `FALSE` if any term is `FALSE`. Returns `UNKNOWN` if no term is `FALSE` and any term is `UNKNOWN`.
  * `any`: Returns `TRUE` if any term is `TRUE`. Returns `UNKNOWN` if no term is `TRUE` and any term is `UNKNOWN`.

### 5.2. Red Lock-in Invariant
When an emergency Red rule fires (e.g. `RF-001`, `RF-003`, `RF-004`, `RF-007`), the engine **locks in the result at Emergency (Red)**. It can never be downgraded to Amber, Yellow, or Green by lower-urgency matching rules or non-critical missing inputs.

### 5.3. Strict Green Lockout
A `self_care` (Green) outcome for `IRR-001` strictly requires that **all** cycle parameters are confirmed normal and **all** red-flag questions are confirmed negative. If any parameter is `unknown` or missing, the engine **refuses to return Green**, returning `status: "need_more_info"`, `urgency.level: "none"`, and listing the unconfirmed fields in `missing_inputs`.

---

## 6. Day 3 Rule Inventory & Counts

| Category | IDs | Count | Governance Status |
|---|---|---:|---|
| **Baseline Red Flags** | `RF-001` to `RF-008` | 8 | Active implementation. Evaluated first. |
| **Safety Gates** | `GATE-001`, `GATE-002`, `GATE-003A`, `GATE-003B`, `GATE-004`, `GATE-005`, `GATE-006` | 7 | Active implementation. Evaluated in Step 0/Step 2. |
| **Irregular Periods Rules** | `IRR-001` to `IRR-013` (including `IRR-007A`) | 14 | Active implementation. Standalone & pathway terminals. |
| **Total Baseline Entries** | — | **29** | **All 29 baseline entries implemented & tested.** |
| **Candidate Gap Rules** | `RF-009`, `EP-001` | 2 | Encoded in YAML; **inactive by default** pending doctor approval. |
| **Total Definitions** | — | **31** | **31 total rule definitions accounted for.** |

### Pathways Implemented:
* **`PATH-AMEN-01` (8 steps):** Amenorrhea & Missed Periods (> 90 days or never menstruated). Features clean Day 4 PCOS deferral (`metadata.deferred_pathways: ["PATH-PCOS-01"]`).
* **`PATH-HMB-01` (6 steps):** Heavy & Abnormal Menstrual Bleeding. Features explicit single-cycle IMB gap terminal `PATH-HMB-01-TERM-IMB1` (`DISC-IMB1`).

---

## 7. Clinical Governance & Unresolved Decisions

Every rule in `rules.yaml` maintains two independent statuses:
1. `evidence_status`: `evidence_located` (guideline chapter located) vs `source_verified` (exact text passage checked).
2. `approval_status`: `mapping_pending_doctor_approval` (all 22 baseline clinical rules are currently pending formal doctor sign-off).

### Key Clinical Decisions Maintained:
* **`DEC-02` / `RF-005` (Pelvic Infection Severity):** CDC criteria are hospitalisation indicators. Engine supports `single_marker_emergency`, `combination_required`, or `None` (halts safely with `clinical_decision_required`).
* **`DEC-03` / `RF-006` (Early Pregnancy Bleeding + Pain):** NICE EPAS triage routes to Amber; Indian casualty practice routes to Red. Engine supports `clinic_visit`, `emergency`, or `None` (halts safely with `clinical_decision_required`).
* **`DEC-08` / `RF-009` & `EP-001` (Candidate Rules):** Non-pregnant acute severe pain and painless early pregnancy bleeding are candidate gap rules. Inactive by default; halt safely with `clinical_decision_required` pending doctor approval.
* **`DISC-IMB1` / `PATH-HMB-01` Step S4B:** Single-cycle intermenstrual bleeding without heavy flow routes to candidate terminal `PATH-HMB-01-TERM-IMB1` with `DISC-IMB1` recorded.

---

## 8. Doctor Fix Guide

Clinicians and medical directors can adjust rules directly in `rules/rules.yaml` without touching application code:

1. **Changing a numerical threshold:**
   * Locate the rule by ID (e.g. `IRR-001`).
   * Update the `value` in the `when` condition (e.g. change `cycle_variation_days` cutoff from `9` to `8`).
   * Update `source.number_checked` to document the change.
2. **Modifying patient advice or suggested tests:**
   * Edit `advice` (must remain non-prescriptive, e.g. "Please consult a healthcare professional").
   * Edit `doctor_may_suggest` (list of blood tests, imaging, or examinations the clinician may consider).
3. **Approving a rule:**
   * Change `approval_status` from `mapping_pending_doctor_approval` to `doctor_approved`.
4. **Verifying tests after modification:**
   * Run `python3 -m unittest discover -s tests`. All tests must pass before deploying.

