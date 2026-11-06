# Women's Health Clinical Risk Triage Engine (v0.2 — Day 4 & Day 5 Complete)

A deterministic, offline, evidence-backed clinical risk triage engine for women's reproductive health (calibrated for women aged 18–40).

> [!IMPORTANT]
> **Codebase Isolation Guarantee:**
> This triage engine lives inside `triage-engine/` as a standalone, self-contained Python module. It has zero coupling, zero imports, and zero dependencies on the legacy `server/triage/` codebase or active production routes. All evaluations are 100% deterministic, offline, and operate without an LLM or external AI API.

---

## 1. Clinical Scope & Target Population

* **Target Population:** Reproductive-aged individuals (18 to 40 years).
* **Topics Covered:**
  1. **Red Flags & Acute Emergencies:** Ectopic pregnancy risk, hemoperitoneum, severe hemorrhage with instability, ovarian torsion, postpartum sepsis.
  2. **Irregular Periods:** Oligomenorrhea, polymenorrhea, secondary amenorrhea, heavy menstrual bleeding, recurrent intermenstrual bleeding, postcoital bleeding, outpatient PID.
  3. **PCOS:** Adult Rotterdam criteria, hyperandrogenism stratification, rapid virilization screening, Indian BMI cardiometabolic markers, prolonged cycle endometrial protection.
  4. **Endometriosis:** Severe cyclical dysmenorrhea, deep dyspareunia, cyclical bowel/urinary symptoms, chronic pelvic pain, failed first-line medical therapy, subfertility interaction.
  5. **Fertility:** Age & time-trying stratification (<35y/12m, >=35y/6m, 36-40y earlier consultation, 35y pending DEC-09), ovulatory dysfunction, tubal risk history, recurrent pregnancy loss (>=2), coital difficulty.
* **Non-Diagnostic Scope:** This engine performs **urgency triage and clinical risk stratification only**, sorting presentations into 4 clinical urgency levels to guide care navigation. It does NOT diagnose medical conditions or prescribe therapeutic regimens.
* **Separation of Concerns:** 
  * Clinical urgency (`level`: `emergency`, `clinic_visit`, `teleconsultation`, `self_care`, `none`) is strictly separated from processing status (`status`: `complete`, `need_more_info`, `out_of_scope`, `clinical_decision_required`, `deferred`).
  * Clinician physical examination requirements (`needs_physical_exam`, `physical_exam_reason`) are kept strictly separated from non-prescriptive patient advisory text (`doctor_may_suggest`).

---

## 2. Directory Structure

```text
triage-engine/
├── README.md                      # Comprehensive architecture, setup, rules, and governance guide
├── pyproject.toml                 # Packaging, Python >= 3.10 runtime specification & CLI entrypoints
├── .env.example                   # Token environment variable placeholders
├── .gitignore                     # Ignores .env, data/*.db, data/exports/
├── rules/
│   ├── inputs_schema.yaml         # 86 validated variables (72 patient P1..P72 + 14 derived D1..D14)
│   ├── rules.yaml                 # 56 complete clinical rules with sources & governance tags
│   └── pathways.yaml              # 4 decision pathways (PATH-AMEN-01, PATH-HMB-01, PATH-PCOS-01, PATH-ENDO-01, PATH-FERT-01)
├── docs/
│   └── flowcharts/                # 4 Mermaid (.mmd) and 4 high-res (.png) flowcharts
│       ├── irregular_periods.mmd / .png
│       ├── pcos.mmd / .png
│       ├── endometriosis.mmd / .png
│       └── fertility.mmd / .png
├── data/
│   ├── cases/
│   │   ├── practice_cases.json    # 40 practice cases across all 4 topics
│   │   ├── exam_cases_vault.json  # 30 immutable exam vault cases
│   │   └── batch1_cases.json      # 18 doctor review cases (Red Flags + PCOS)
│   ├── triage_reviews.db          # SQLite persistent database (0600 permissions)
│   └── exports/
│       ├── reviews_export.csv     # Auto-synced CSV mirror for Excel / Google Sheets
│       ├── reviews_export.json    # Auto-synced JSON backup
│       └── feedback_report.md     # Generated clinical feedback report
├── src/
│   ├── __init__.py                # Package exports: evaluate_patient, get_engine, TriageEngine
│   ├── cli.py                     # Offline CLI runner (JSON payload / file input, policy flags)
│   ├── engine.py                  # Orchestrator across all 4 domains + Green lockout
│   ├── evaluator.py               # 3-valued condition evaluator (TRUE, FALSE, UNKNOWN)
│   ├── gates.py                   # Pure evaluation of Gates 1-6 and Derived Variables D1-D14
│   ├── loader.py                  # Strict YAML loaders and SchemaRegistry with alias mappings
│   ├── models.py                  # Pure dataclasses and Enums (TriageResult, SyntheticCase, etc.)
│   ├── pathways.py                # Decision tree runner with safety routing and pending terminals
│   ├── flowchart_generator.py     # Deterministic Mermaid source & PIL PNG image renderer
│   ├── synthetic_generator.py     # Independent oracle-based synthetic patient case generator
│   ├── case_store.py              # SQLite storage with exam immutability & CSV/JSON export mirrors
│   ├── review_security.py         # 256-bit token authentication, role separation & anti-leakage guards
│   ├── review_server.py           # Zero-dependency mobile-first doctor review server
│   ├── feedback_report.py         # Feedback analytics, confusion matrix & safety report generator
│   └── static/
│       ├── review.html            # Mobile-first Doctor Review web interface
│       ├── review.css             # High-contrast, phone-friendly touch styles (58px+ buttons)
│       └── review.js              # Blind assessment, disagreement capture & progress sync
└── tests/
    ├── test_gates.py                          # Unit & boundary tests for Gates 1-6 and D1-D14
    ├── test_red_flags.py                      # 10 tests for RF-001..RF-009, policies & priority
    ├── test_irregular.py                      # 15 tests for IRR-001..IRR-013 & FIGO boundaries
    ├── test_pathways_day3.py                  # 14 tests for PATH-AMEN-01 and PATH-HMB-01
    ├── test_engine_safety.py                  # 5 safety invariant tests
    ├── test_pcos.py                           # Unit, boundary, signal & pathway tests for PCOS
    ├── test_endometriosis.py                  # Unit, signal & pathway tests for Endometriosis
    ├── test_fertility.py                      # Unit, age/duration & pathway tests for Fertility
    ├── test_day4_coverage_and_flowcharts.py   # Rule audit, offline check, flowchart tests
    ├── test_review_security.py                # Token, role, anti-leakage, bind & synthetic guards
    └── test_day5_review_and_generator.py      # Generator, exam immutability, review lifecycle
```

---

## 3. Installation & Setup

### Requirements:
* Python 3.10+ (tested and verified on Python 3.14.4).
* Standard libraries + `PyYAML` (`>= 6.0`) + `Pillow` (`PIL`).
* Zero external web frameworks required (runs with built-in `http.server`).

### Quick Verification:
```bash
# From triage-engine directory:
python3 -m unittest discover -s tests -v
# Ran 102 tests ... OK (100% passing)
```

---

## 4. Flowchart Generation

Generate both Mermaid diagram files (`.mmd`) and high-resolution clinician-reviewable images (`.png`):

```bash
python3 -m src.flowchart_generator
```

Outputs in `docs/flowcharts/`:
* `irregular_periods.mmd` and `irregular_periods.png`
* `pcos.mmd` and `pcos.png`
* `endometriosis.mmd` and `endometriosis.png`
* `fertility.mmd` and `fertility.png`

---

## 5. Synthetic Patient Generator

Generate fictional, seed-reproducible cases conforming to `inputs_schema.yaml` with independent clinical expectations:

```bash
# Generate Batch 1 (18 cases: Red Flags + PCOS) and commit to SQLite:
python3 -m src.synthetic_generator --batch-id batch1 --save-db

# Generate 40 practice cases:
python3 -m src.synthetic_generator --collection practice --count 40 --out data/cases/practice_cases.json --save-db

# Generate 30 exam vault cases:
python3 -m src.synthetic_generator --collection exam --count 30 --out data/cases/exam_cases_vault.json --save-db
```

---

## 6. Doctor Review Server & Mobile Workflow

### 6.1 Generate Secure Tokens
```bash
python3 -m src.review_security --generate-tokens
```

### 6.2 Start the Server
Export environment variables and start the server (binds to loopback `127.0.0.1` by default for security):

```bash
export TRIAGE_REVIEW_DOCTOR_TOKENS="dr_smitha:<token1>,dr_surbhi:<token2>,adarsh:<token3>"
export TRIAGE_REVIEW_ADMIN_TOKEN="<admin_token>"

python3 -m src.review_server --port 8080 --batch batch1
```

### 6.3 Doctor Mobile Workflow
1. Doctor opens private link: `http://127.0.0.1:8080/#t=<doctor-token>&batch=batch1`
2. **Blind Assessment:** Doctor sees 3–4 concise clinical lines; engine output and rule answers are **strictly hidden** before submission.
3. Doctor taps 1 of 4 urgency buttons: 🟢 Green, 🟡 Yellow, 🟠 Amber, 🔴 Red.
4. Doctor taps **Submit Assessment & Reveal Engine Result**.
5. **Engine Reveal & Agreement Banner:**
   * ✅ **Agreement:** Single-tap to advance to next case.
   * ⚠️ **Disagreement:** Structured questions appear ("Who is right?", problem chips, dynamic prompt: *"Why did you choose [Doctor Urgency] instead of [Engine Urgency]?"*).
6. Auto-saves to SQLite (`data/triage_reviews.db`) and exports real-time CSV (`data/exports/reviews_export.csv`).

---

## 7. Feedback Analytics & Reporting

Adarsh or administrators can view feedback reports via CLI or browser:

```bash
# Generate markdown report:
python3 -m src.feedback_report --batch batch1

# Or view via admin web endpoint:
# http://127.0.0.1:8080/report?batch=batch1 (using Authorization: Bearer <admin_token>)
```

The report computes:
* Total doctor reviews & agreement percentages.
* 4-level confusion matrix + "Need More Info / None".
* High-priority safety miss tracker (Red under-triage, false Green reassurance).
* Frequency table of rules appearing in disagreements.
* Doctor rationale and requested rule adjustments log.

---

## 8. Clinical Governance & Unresolved Decisions Preserved

Every rule definition in `rules/rules.yaml` retains:
* `evidence_status`: `evidence_located` vs `source_verified`.
* `approval_status`: Strictly maintained as `mapping_pending_doctor_approval` across all 56 rules until formal sign-off.

### Unresolved Clinical Decisions:
* **`DEC-01` (`RF-003` / `IRR-007A`):** Hourly soaking with hemodynamic instability (Red) vs stable (Amber).
* **`DEC-02` (`RF-005` / `IRR-013`):** Pelvic infection severity (single marker vs combination required).
* **`DEC-03` (`RF-006`):** Early pregnancy bleeding + pain (NICE Amber vs Indian casualty Red).
* **`DEC-06` (`PCOS-007`):** BMI screening cutoff (Indian 23.0 default vs WHO 25.0 global).
* **`DEC-07` (`ENDO-002` & `ENDO-008`):** `ENDO-008` 2-of-4 symptom cluster is a proposed mapping, **inactive by default** (`endo008_policy=None`).
* **`DEC-08` (`RF-009` & `EP-001`):** Candidate gap rules kept inactive by default.
* **`DEC-09` (`FERT-003` & `FERT-004`):** Age $\ge 35$ / 6 months (ASRM) vs Age $\ge 36$ earlier consultation (NICE). **Age 35 with <6 months trying halts at explicit pending terminal** (`PATH-FERT-01-TERM-AGE35`, `clinical_decision_required`, level: none).
* **`DEC-10` (`FERT-007`):** Recurrent pregnancy loss threshold set at $\ge 2$ miscarriages.
