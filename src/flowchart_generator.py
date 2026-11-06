"""Flowchart generator for clinical decision pathways.

Generates both Mermaid (.mmd) source files and clean rendered PNG diagrams
for the four clinical triage topics:
1. Irregular Periods (PATH-AMEN-01 & PATH-HMB-01)
2. Polycystic Ovary Syndrome (PATH-PCOS-01)
3. Endometriosis & Pelvic Pain (PATH-ENDO-01)
4. Fertility & Preconception (PATH-FERT-01)
"""

from __future__ import annotations

import pathlib
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from .loader import load_pathways, load_rules
from .models import Pathway, Rule, UrgencyColour, UrgencyLevel


def get_colour_hex(level: Optional[UrgencyLevel]) -> str:
    if level == UrgencyLevel.EMERGENCY:
        return "#dc2626"  # Red
    elif level == UrgencyLevel.CLINIC_VISIT:
        return "#d97706"  # Amber
    elif level == UrgencyLevel.TELECONSULTATION:
        return "#ca8a04"  # Yellow
    elif level == UrgencyLevel.SELF_CARE:
        return "#16a34a"  # Green
    return "#475569"  # Slate / Grey


def generate_mermaid_pcos(pathway: Pathway, rules_by_id: Dict[str, Rule]) -> str:
    lines = [
        "flowchart TD",
        "    classDef red fill:#dc2626,stroke:#991b1b,stroke-width:2px,color:#fff;",
        "    classDef amber fill:#d97706,stroke:#92400e,stroke-width:2px,color:#fff;",
        "    classDef yellow fill:#ca8a04,stroke:#854d0e,stroke-width:2px,color:#fff;",
        "    classDef green fill:#16a34a,stroke:#166534,stroke-width:2px,color:#fff;",
        "    classDef grey fill:#475569,stroke:#1e293b,stroke-width:2px,color:#fff;",
        "    classDef decision fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;",
        "",
        '    START(["Patient Presents with PCOS / Hyperandrogenism Symptoms"]):::decision',
        '    S1{"S1: Rapid Virilisation Signs?<br/>(voice deepening, clitoromegaly)"}:::decision',
        '    S2{"S2: Amenorrhea >= 90 days?<br/>(non-pregnant, no contraception)"}:::decision',
        '    S3{"S3: Age Cohort?<br/>(Age < 20 years)"}:::decision',
        '    S4{"S4: Adolescent Diagnostic Criteria?<br/>(Both Ovulatory Dysfunction & Androgen Excess)"}:::decision',
        '    S4B{"S4B: Adolescent Single Feature?<br/>(Cycle Irregularity OR Androgen Excess Alone)"}:::decision',
        '    S5{"S5: Adult Clinical Diagnostic Criteria?<br/>(Both Ovulatory Dysfunction & Androgen Excess)"}:::decision',
        '    S5B{"S5B: Adult Ultrasound Criteria?<br/>(PCOM on Ultrasound + Ovulatory or Androgen Sign)"}:::decision',
        '    S5C{"S5C: Isolated Hyperandrogenism?<br/>(Excess hair, cystic acne, or alopecia with regular cycles)"}:::decision',
        '    S5D{"S5D: Prior Established PCOS Diagnosis?<br/>(Routine monitoring & metabolic screening)"}:::decision',
        '    S6{"S6: Normal Ovulatory Cycles & No Androgen Excess?"}:::decision',
        "",
        '    T_RED["PCOS-001 (Emergency)<br/>Immediate Oncology/Endocrine Exclusion"]:::red',
        '    T_PCOS5["PCOS-005 (Clinic Visit / Amber)<br/>Endometrial Protection Assessment"]:::amber',
        '    T_PCOS4["PCOS-004 (Teleconsultation / Yellow)<br/>Adolescent Suspected PCOS"]:::yellow',
        '    T_PCOS7["PCOS-007 (Teleconsultation / Yellow)<br/>Adolescent At-Risk of PCOS (DEC-06)"]:::yellow',
        '    T_PCOS2["PCOS-002 (Teleconsultation / Yellow)<br/>Adult Suspected PCOS"]:::yellow',
        '    T_PCOS3["PCOS-003 (Teleconsultation / Yellow)<br/>Adult PCOS with Ultrasound PCOM"]:::yellow',
        '    T_PCOS6["PCOS-006 (Teleconsultation / Yellow)<br/>Isolated Clinical Hyperandrogenism"]:::yellow',
        '    T_PCOS8["PCOS-008 (Teleconsultation / Yellow)<br/>PCOS Routine Management"]:::yellow',
        '    T_GREEN["PCOS-009 (Self-Care / Green)<br/>Normal Cycle, No Androgen Signs"]:::green',
        '    T_MORE["Need More Information<br/>(Strict Green Lockout / Missing Data)"]:::grey',
        "",
        "    START --> S1",
        "    S1 -- Yes --> T_RED",
        "    S1 -- No --> S2",
        "    S1 -- Unknown --> T_MORE",
        "    S2 -- Yes --> T_PCOS5",
        "    S2 -- No --> S3",
        "    S2 -- Unknown --> T_MORE",
        "    S3 -- Adolescent (<20) --> S4",
        "    S3 -- Adult (>=20) --> S5",
        "    S4 -- Yes --> T_PCOS4",
        "    S4 -- No --> S4B",
        "    S4B -- Yes --> T_PCOS7",
        "    S4B -- No --> S6",
        "    S5 -- Yes --> T_PCOS2",
        "    S5 -- No --> S5B",
        "    S5B -- Yes --> T_PCOS3",
        "    S5B -- No --> S5C",
        "    S5C -- Yes --> T_PCOS6",
        "    S5C -- No --> S5D",
        "    S5D -- Yes --> T_PCOS8",
        "    S5D -- No --> S6",
        "    S6 -- All Negative Confirmed --> T_GREEN",
        "    S6 -- Missing / Incomplete --> T_MORE",
    ]
    return "\n".join(lines)


def generate_mermaid_endometriosis(pathway: Pathway, rules_by_id: Dict[str, Rule]) -> str:
    lines = [
        "flowchart TD",
        "    classDef red fill:#dc2626,stroke:#991b1b,stroke-width:2px,color:#fff;",
        "    classDef amber fill:#d97706,stroke:#92400e,stroke-width:2px,color:#fff;",
        "    classDef yellow fill:#ca8a04,stroke:#854d0e,stroke-width:2px,color:#fff;",
        "    classDef green fill:#16a34a,stroke:#166534,stroke-width:2px,color:#fff;",
        "    classDef grey fill:#475569,stroke:#1e293b,stroke-width:2px,color:#fff;",
        "    classDef decision fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;",
        "",
        '    START(["Patient Presents with Pelvic Pain or Endometriosis Symptoms"]):::decision',
        '    S1{"S1: Chronic Pelvic Pain >= 6 Months<br/>OR Palpable Pelvic Mass?"}:::decision',
        '    S2{"S2: Prior Endometriosis Medical Treatment Failed?"}:::decision',
        '    S3{"S3: Endometriosis Symptoms with Concurrent Subfertility?"}:::decision',
        '    S4{"S4: Proposed Multi-Symptom Cluster?<br/>(>= 2 of 4 cardinal symptoms - DEC-07)"}:::decision',
        '    S5{"S5: Deep Dyspareunia OR Cyclical Bowel / Bladder Symptoms?"}:::decision',
        '    S6{"S6: Severe Cyclical Dysmenorrhea Affecting Daily Life?"}:::decision',
        '    S7{"S7: Known Endometriosis Diagnosis for Routine Follow-up?"}:::decision',
        '    S8{"S8: Normal Menses with All Endometriosis Symptoms Absent?"}:::decision',
        "",
        '    T_ENDO4["ENDO-004 (Clinic Visit / Amber)<br/>Chronic Pelvic Pain / Mass Evaluation"]:::amber',
        '    T_ENDO5["ENDO-005 (Clinic Visit / Amber)<br/>Specialist Referral (Failed First-line Therapy)"]:::amber',
        '    T_ENDO6["ENDO-006 (Clinic Visit / Amber)<br/>Specialist Infertility / Endometriosis Workup"]:::amber',
        '    T_ENDO8["ENDO-008 (Proposed Mapping / DEC-07)<br/>Multi-symptom Presentation (Doctor Approval Required)"]:::grey',
        '    T_ENDO3["ENDO-003 (Teleconsultation / Yellow)<br/>Deep Dyspareunia / Cyclical Extragenital Pain"]:::yellow',
        '    T_ENDO2["ENDO-002 (Teleconsultation / Yellow)<br/>Severe Cyclical Dysmenorrhea"]:::yellow',
        '    T_ENDO7["ENDO-007 (Teleconsultation / Yellow)<br/>Confirmed Endometriosis Routine Care"]:::yellow',
        '    T_ENDO1["ENDO-001 (Self-Care / Green)<br/>Normal Menses, Pain Free"]:::green',
        '    T_MORE["Need More Information<br/>(Unknown Never Auto-Escalated - REV-2)"]:::grey',
        "",
        "    START --> S1",
        "    S1 -- Yes --> T_ENDO4",
        "    S1 -- No --> S2",
        "    S1 -- Unknown --> T_MORE",
        "    S2 -- Yes --> T_ENDO5",
        "    S2 -- No --> S3",
        "    S2 -- Unknown --> T_MORE",
        "    S3 -- Yes --> T_ENDO6",
        "    S3 -- No --> S4",
        "    S3 -- Unknown --> T_MORE",
        "    S4 -- Yes (if approved) --> T_ENDO8",
        "    S4 -- No / Policy Pending --> S5",
        "    S4 -- Unknown --> T_MORE",
        "    S5 -- Yes --> T_ENDO3",
        "    S5 -- No --> S6",
        "    S5 -- Unknown --> T_MORE",
        "    S6 -- Yes --> T_ENDO2",
        "    S6 -- No --> S7",
        "    S6 -- Unknown --> T_MORE",
        "    S7 -- Yes --> T_ENDO7",
        "    S7 -- No --> S8",
        "    S7 -- Unknown --> T_MORE",
        "    S8 -- All Negative Confirmed --> T_ENDO1",
        "    S8 -- Missing / Incomplete --> T_MORE",
    ]
    return "\n".join(lines)


def generate_mermaid_fertility(pathway: Pathway, rules_by_id: Dict[str, Rule]) -> str:
    lines = [
        "flowchart TD",
        "    classDef red fill:#dc2626,stroke:#991b1b,stroke-width:2px,color:#fff;",
        "    classDef amber fill:#d97706,stroke:#92400e,stroke-width:2px,color:#fff;",
        "    classDef yellow fill:#ca8a04,stroke:#854d0e,stroke-width:2px,color:#fff;",
        "    classDef green fill:#16a34a,stroke:#166534,stroke-width:2px,color:#fff;",
        "    classDef grey fill:#475569,stroke:#1e293b,stroke-width:2px,color:#fff;",
        "    classDef decision fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;",
        "",
        '    START(["Patient Trying to Conceive or History of Pregnancy Loss"]):::decision',
        '    S1{"S1: Recurrent Pregnancy Loss?<br/>(>= 2 miscarriages OR second-trimester loss)"}:::decision',
        '    S2{"S2: Tubal Risk Factor History?<br/>(PID, ectopic, or tubal/pelvic surgery - D9)"}:::decision',
        '    S2B{"S2B: Inability to Have Penetrative Intercourse?<br/>(Vaginismus, severe dyspareunia)"}:::decision',
        '    S2C{"S2C: Concurrent Endometriosis Suspicion?<br/>(Disabling pain, deep dyspareunia - D13)"}:::decision',
        '    S3{"S3: Ovulatory Dysfunction / Irregular Cycles?<br/>(Oligomenorrhea or amenorrhea - D12)"}:::decision',
        '    S4{"S4: Age < 35 AND Trying >= 12 Months?<br/>(Standard Infertility Investigation Threshold)"}:::decision',
        '    S4B{"S4B: Age >= 35 AND Trying >= 6 Months?<br/>(ASRM Earlier Fertility Evaluation Threshold)"}:::decision',
        '    S4C{"S4C: Age 35 AND Trying < 6 Months?<br/>(Pending Clinical Governance Decision DEC-09)"}:::decision',
        '    S4D{"S4D: Age 36-40 AND Trying < 6 Months?<br/>(NICE NG257 Earlier Consultation Option)"}:::decision',
        '    S5{"S5: Age < 35, Trying < 12 Months, All Risk Factors Negative?"}:::decision',
        "",
        '    T_FERT7["FERT-007 (Clinic Visit / Amber)<br/>Recurrent Miscarriage Panel (DEC-10)"]:::amber',
        '    T_FERT6["FERT-006 (Clinic Visit / Amber)<br/>Tubal Factor Evaluation & Patency"]:::amber',
        '    T_FERT8["FERT-008 (Clinic Visit / Amber)<br/>Specialist Coital / Pelvic Assessment"]:::amber',
        '    T_ENDO6["ENDO-006 (Clinic Visit / Amber)<br/>Concurrent Endometriosis & Fertility Review"]:::amber',
        '    T_FERT5["FERT-005 (Teleconsultation / Yellow)<br/>Ovulatory Disorder / Induction Assessment"]:::yellow',
        '    T_FERT2["FERT-002 (Teleconsultation / Yellow)<br/>Formal Infertility Workup (Age <35, >=12m)"]:::yellow',
        '    T_FERT3["FERT-003 (Teleconsultation / Yellow)<br/>Earlier Fertility Workup (Age >=35, >=6m)"]:::yellow',
        '    T_AGE35["PATH-FERT-01-TERM-AGE35 (Pending Decision)<br/>No Auto-Yellow/Green; DEC-09 Required"]:::grey',
        '    T_FERT4["FERT-004 (Teleconsultation / Yellow)<br/>Earlier Specialist Consultation (Age 36-40, Proposed)"]:::yellow',
        '    T_FERT1["FERT-001 (Self-Care / Green)<br/>Normal Conception Timeline & Preconception Care"]:::green',
        '    T_MORE["Need More Information<br/>(Unknown Never Auto-Escalated - REV-2)"]:::grey',
        "",
        "    START --> S1",
        "    S1 -- Yes --> T_FERT7",
        "    S1 -- No --> S2",
        "    S1 -- Unknown --> T_MORE",
        "    S2 -- Yes --> T_FERT6",
        "    S2 -- No --> S2B",
        "    S2 -- Unknown --> T_MORE",
        "    S2B -- Yes --> T_FERT8",
        "    S2B -- No --> S2C",
        "    S2B -- Unknown --> T_MORE",
        "    S2C -- Yes --> T_ENDO6",
        "    S2C -- No --> S3",
        "    S2C -- Unknown --> T_MORE",
        "    S3 -- Yes --> T_FERT5",
        "    S3 -- No --> S4",
        "    S3 -- Unknown --> T_MORE",
        "    S4 -- Yes --> T_FERT2",
        "    S4 -- No --> S4B",
        "    S4 -- Unknown --> T_MORE",
        "    S4B -- Yes --> T_FERT3",
        "    S4B -- No --> S4C",
        "    S4B -- Unknown --> T_MORE",
        "    S4C -- Yes --> T_AGE35",
        "    S4C -- No --> S4D",
        "    S4C -- Unknown --> T_MORE",
        "    S4D -- Yes --> T_FERT4",
        "    S4D -- No --> S5",
        "    S4D -- Unknown --> T_MORE",
        "    S5 -- Confirmed Normal --> T_FERT1",
        "    S5 -- Missing / Incomplete --> T_MORE",
    ]
    return "\n".join(lines)


def generate_mermaid_irregular(rules_by_id: Dict[str, Rule]) -> str:
    lines = [
        "flowchart TD",
        "    classDef red fill:#dc2626,stroke:#991b1b,stroke-width:2px,color:#fff;",
        "    classDef amber fill:#d97706,stroke:#92400e,stroke-width:2px,color:#fff;",
        "    classDef yellow fill:#ca8a04,stroke:#854d0e,stroke-width:2px,color:#fff;",
        "    classDef green fill:#16a34a,stroke:#166534,stroke-width:2px,color:#fff;",
        "    classDef grey fill:#475569,stroke:#1e293b,stroke-width:2px,color:#fff;",
        "    classDef decision fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;",
        "",
        '    START(["Patient Presents with Menstrual Cycle Irregularity / Abnormal Bleeding"]):::decision',
        '    RF{"Red Flag Triage Check:<br/>Hemodynamic instability, acute abdomen, soaking hourly?"}:::decision',
        '    AMEN{"Amenorrhea Gate:<br/>Days Since Last Period > 90 OR Never Menstruated?"}:::decision',
        '    HMB{"Abnormal Bleeding Gate:<br/>Heavy flow, duration > 8 days, or intermenstrual bleeding?"}:::decision',
        '    FIGO{"FIGO Cycle Parameters:<br/>Cycle length 24-38 days, variation <= 7-9 days, normal duration?"}:::decision',
        "",
        '    PATH_AMEN["PATH-AMEN-01 (Amenorrhea Pathway)<br/>Primary/Secondary Amenorrhea, Pregnancy Exclusion, FHA"]:::decision',
        '    PATH_HMB["PATH-HMB-01 (Heavy/Abnormal Bleeding Pathway)<br/>PCB, Recurrent IMB, Symptomatic Anemia, Flooding"]:::decision',
        "",
        '    T_RED["Emergency Red Flags (RF-001..RF-008)<br/>Immediate In-Person Emergency Evaluation"]:::red',
        '    T_AMBER["Clinic Visit (Amber)<br/>IRR-007 (IMB 2+ cycles), IRR-007A, IRR-008, IRR-009, IRR-010"]:::amber',
        '    T_YELLOW["Teleconsultation (Yellow)<br/>IRR-002, IRR-003, IRR-004, IRR-005, IRR-006, IRR-011"]:::yellow',
        '    T_GREEN["IRR-001 (Self-Care / Green)<br/>Normal FIGO Menstrual Regularity"]:::green',
        '    T_MORE["Need More Information<br/>(Strict Green Lockout & Pregnancy Gating)"]:::grey',
        "",
        "    START --> RF",
        "    RF -- Red Flag Positive --> T_RED",
        "    RF -- Cleared --> AMEN",
        "    AMEN -- Yes --> PATH_AMEN",
        "    AMEN -- No --> HMB",
        "    HMB -- Yes --> PATH_HMB",
        "    HMB -- No --> FIGO",
        "    FIGO -- FIGO Normal Verified --> T_GREEN",
        "    FIGO -- FIGO Irregular Length (<24 or >38) --> T_YELLOW",
        "    FIGO -- Missing Parameters --> T_MORE",
        "    PATH_AMEN --> T_AMBER",
        "    PATH_AMEN --> T_YELLOW",
        "    PATH_AMEN --> T_MORE",
        "    PATH_HMB --> T_AMBER",
        "    PATH_HMB --> T_YELLOW",
        "    PATH_HMB --> T_MORE",
    ]
    return "\n".join(lines)


def render_flowchart_image(
    title: str,
    subtitle: str,
    steps_data: List[Tuple[str, str, str, str, str]],  # (step_id, question, yes_target, no_target, unk_target)
    terminals_data: Dict[str, Tuple[str, str, UrgencyLevel]],  # id -> (name, detail, level)
    output_png_path: pathlib.Path,
):
    """Renders a polished, publication-quality hierarchical flowchart diagram as PNG."""
    width = 1400
    row_height = 90
    top_margin = 140
    bottom_margin = 160
    total_steps = len(steps_data)
    height = top_margin + (total_steps * row_height) + bottom_margin

    img = Image.new("RGB", (width, height), color="#f8fafc")  # Slate-50 background
    draw = ImageDraw.Draw(img)

    # Header Banner
    draw.rectangle([0, 0, width, 100], fill="#0f172a")  # Slate-900
    draw.text((40, 22), title, fill="#ffffff")
    draw.text((40, 58), subtitle, fill="#94a3b8")

    # Legend at bottom
    legend_y = height - 120
    draw.rectangle([40, legend_y, width - 40, height - 30], fill="#ffffff", outline="#cbd5e1", width=1)
    draw.text((55, legend_y + 15), "CLINICAL TRIAGE LEGEND:", fill="#0f172a")

    legend_items = [
        ("Emergency (Red)", "#dc2626"),
        ("Clinic Visit (Amber)", "#d97706"),
        ("Teleconsultation (Yellow)", "#ca8a04"),
        ("Self-Care (Green)", "#16a34a"),
        ("Need More Info / Policy (Grey)", "#475569"),
    ]
    lx = 280
    for label, col in legend_items:
        draw.rectangle([lx, legend_y + 15, lx + 18, legend_y + 33], fill=col)
        draw.text((lx + 26, legend_y + 15), label, fill="#334155")
        lx += 220

    # Draw step nodes and connections
    step_x = 80
    step_w = 460
    step_h = 58

    term_x = 760
    term_w = 560
    term_h = 58

    y = top_margin
    for i, (sid, question, yes_target, no_target, unk_target) in enumerate(steps_data):
        curr_y = y + (i * row_height)

        # Decision Node
        draw.rounded_rectangle([step_x, curr_y, step_x + step_w, curr_y + step_h], radius=6, fill="#ffffff", outline="#64748b", width=2)
        draw.text((step_x + 12, curr_y + 8), f"[{sid}]", fill="#0f172a")
        # Split question if too long
        q_lines = [question[:65], question[65:130]] if len(question) > 65 else [question]
        draw.text((step_x + 60, curr_y + 8), q_lines[0], fill="#1e293b")
        if len(q_lines) > 1:
            draw.text((step_x + 60, curr_y + 28), q_lines[1], fill="#475569")

        # If yes_target is a terminal
        if yes_target in terminals_data:
            t_name, t_detail, t_level = terminals_data[yes_target]
            col = get_colour_hex(t_level)

            # Arrow from step to terminal
            draw.line([step_x + step_w, curr_y + 29, term_x, curr_y + 29], fill="#64748b", width=2)
            draw.polygon([(term_x, curr_y + 29), (term_x - 8, curr_y + 24), (term_x - 8, curr_y + 34)], fill="#64748b")
            draw.text((step_x + step_w + 15, curr_y + 10), "Yes", fill="#16a34a")

            # Terminal Card
            draw.rounded_rectangle([term_x, curr_y, term_x + term_w, curr_y + term_h], radius=6, fill=col, outline="#334155", width=1)
            draw.text((term_x + 14, curr_y + 8), f"{yes_target}: {t_name}", fill="#ffffff")
            draw.text((term_x + 14, curr_y + 30), t_detail, fill="#f1f5f9")

        # Arrow down to next step (for "No")
        if i < total_steps - 1:
            draw.line([step_x + 70, curr_y + step_h, step_x + 70, curr_y + row_height], fill="#64748b", width=2)
            draw.polygon([(step_x + 70, curr_y + row_height), (step_x + 65, curr_y + row_height - 8), (step_x + 75, curr_y + row_height - 8)], fill="#64748b")
            draw.text((step_x + 78, curr_y + step_h + 4), "No", fill="#dc2626")

    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_png_path, "PNG")


def generate_all_flowcharts(output_dir: pathlib.Path = pathlib.Path("docs/flowcharts")):
    """Generates 4 MMD and 4 PNG flowchart artifacts from canonical YAML rules and pathways."""
    output_dir.mkdir(parents=True, exist_ok=True)

    pathways = load_pathways()
    rules = load_rules()
    rules_by_id = {r.id: r for r in rules}
    pathways_by_id = {p.id: p for p in pathways}

    # 1. PCOS Flowchart
    pcos_pw = pathways_by_id.get("PATH-PCOS-01")
    if pcos_pw:
        mmd_pcos = generate_mermaid_pcos(pcos_pw, rules_by_id)
        with open(output_dir / "pcos_flowchart.mmd", "w") as f:
            f.write(mmd_pcos)

        pcos_steps = [
            ("S1", "Rapid virilisation signs (deepening voice, clitoromegaly)?", "PCOS-005", "S2", "need_more_info"),
            ("S2", "Prolonged amenorrhea >= 90 days with PCOS features?", "PCOS-008", "S3", "need_more_info"),
            ("S3", "Age cohort: Is the patient an adolescent under 20 years?", "S4", "S5", "need_more_info"),
            ("S4", "Adolescent: Both ovulatory dysfunction AND clinical androgen excess?", "PCOS-004", "S4B", "need_more_info"),
            ("S4B", "Adolescent: Single Rotterdam feature (at risk of PCOS per DEC-06)?", "PCOS-007", "S6", "need_more_info"),
            ("S5", "Adult: Both ovulatory dysfunction AND clinical androgen excess?", "PCOS-003", "S5B", "need_more_info"),
            ("S5B", "Adult: Isolated acne or hair thinning with ovulatory dysfunction?", "PCOS-004", "S5C", "need_more_info"),
            ("S5C", "Isolated clinical hyperandrogenism with regular ovulatory cycles?", "PCOS-006", "S5D", "need_more_info"),
            ("S5D", "PCOS with cardiometabolic risk markers (BMI >= 23 / acanthosis)?", "PCOS-007", "S6", "need_more_info"),
            ("S6", "Normal cycles with confirmed absence of androgen excess signs?", "PCOS-009", "need_more_info", "need_more_info"),
        ]
        pcos_terminals = {
            "PCOS-005": ("Rapid Virilisation Warning Sign", "In-person assessment to rule out androgen-secreting neoplasm", UrgencyLevel.CLINIC_VISIT),
            "PCOS-008": ("Prolonged Amenorrhea in PCOS", "Progestin withdrawal discussion for endometrial protection", UrgencyLevel.TELECONSULTATION),
            "PCOS-004": ("Ovulatory Dysfunction + Acne/Alopecia", "Weaker clinical hyperandrogenism predictor panel", UrgencyLevel.TELECONSULTATION),
            "PCOS-007": ("Cardiometabolic Risk Screening", "Fasting lipids and glucose tolerance check (DEC-06)", UrgencyLevel.TELECONSULTATION),
            "PCOS-003": ("Adult Rotterdam Phenotype", "Ovulatory dysfunction + clinical hirsutism", UrgencyLevel.TELECONSULTATION),
            "PCOS-006": ("Regular Cycles + Hirsutism", "Isolated idiopathic hirsutism management", UrgencyLevel.TELECONSULTATION),
            "PCOS-009": ("Normal Cycle / No PCOS", "Normal ovulatory cycles; no hyperandrogenism signs", UrgencyLevel.SELF_CARE),
        }
        render_flowchart_image(
            "TOPIC 2: POLYCYSTIC OVARY SYNDROME (PCOS) TRIAGE PATHWAY",
            "Reference: 2023 International Evidence-based PCOS Guideline (Monash / Endocrine Society)",
            pcos_steps,
            pcos_terminals,
            output_dir / "pcos_flowchart.png",
        )

    # 2. Endometriosis Flowchart
    endo_pw = pathways_by_id.get("PATH-ENDO-01")
    if endo_pw:
        mmd_endo = generate_mermaid_endometriosis(endo_pw, rules_by_id)
        with open(output_dir / "endometriosis_flowchart.mmd", "w") as f:
            f.write(mmd_endo)

        endo_steps = [
            ("S1", "Chronic pelvic pain >= 6 months OR palpable pelvic mass/fullness?", "ENDO-004", "S2", "need_more_info"),
            ("S2", "Symptoms persist after first-line hormonal / NSAID treatment failed?", "ENDO-005", "S3", "need_more_info"),
            ("S3", "Endometriosis suspicion signal with concurrent subfertility?", "ENDO-006", "S4", "need_more_info"),
            ("S4", "Proposed 2-of-4 symptom combination (DEC-07 pending doctor review)?", "ENDO-008", "S5", "need_more_info"),
            ("S5", "Deep dyspareunia OR cyclical bowel / cyclical urinary symptoms?", "ENDO-003", "S6", "need_more_info"),
            ("S6", "Severe cyclical dysmenorrhea that interferes with daily activities?", "ENDO-002", "S7", "need_more_info"),
            ("S7", "Known established endometriosis for routine primary care review?", "ENDO-007", "S8", "need_more_info"),
            ("S8", "Are period pain and all endometriosis symptoms confirmed absent?", "ENDO-001", "need_more_info", "need_more_info"),
        ]
        endo_terminals = {
            "ENDO-004": ("Chronic Pelvic Pain / Mass", "In-person bimanual exam and pelvic ultrasound", UrgencyLevel.CLINIC_VISIT),
            "ENDO-005": ("Failed First-Line Medical Treatment", "Specialist gynecology referral & secondary imaging", UrgencyLevel.CLINIC_VISIT),
            "ENDO-006": ("Endometriosis with Subfertility", "Coordinated early fertility & pelvic assessment", UrgencyLevel.CLINIC_VISIT),
            "ENDO-008": ("Multi-Symptom Cluster (DEC-07)", "Proposed 2-of-4 symptom mapping pending doctor approval", UrgencyLevel.CLINIC_VISIT),
            "ENDO-003": ("Deep Dyspareunia / Extragenital", "Clinical review for deep infiltrating endometriosis signs", UrgencyLevel.TELECONSULTATION),
            "ENDO-002": ("Severe Disabling Dysmenorrhea", "First-line medical therapy (NSAIDs/hormonal contraception)", UrgencyLevel.TELECONSULTATION),
            "ENDO-007": ("Confirmed Endometriosis Routine Care", "Routine symptom monitoring and treatment optimization", UrgencyLevel.TELECONSULTATION),
            "ENDO-001": ("Normal Menses / Pain Free", "No cardinal endometriosis symptoms reported", UrgencyLevel.SELF_CARE),
        }
        render_flowchart_image(
            "TOPIC 3: ENDOMETRIOSIS & CHRONIC PELVIC PAIN TRIAGE PATHWAY",
            "Reference: NICE NG73 (Endometriosis: diagnosis and management) & ESHRE Endometriosis Guideline",
            endo_steps,
            endo_terminals,
            output_dir / "endometriosis_flowchart.png",
        )

    # 3. Fertility Flowchart
    fert_pw = pathways_by_id.get("PATH-FERT-01")
    if fert_pw:
        mmd_fert = generate_mermaid_fertility(fert_pw, rules_by_id)
        with open(output_dir / "fertility_flowchart.mmd", "w") as f:
            f.write(mmd_fert)

        fert_steps = [
            ("S1", "Recurrent pregnancy loss (>= 2 miscarriages or second-trimester loss)?", "FERT-007", "S2", "need_more_info"),
            ("S2", "Tubal factor risk history (prior PID, ectopic, or tubal/pelvic surgery)?", "FERT-006", "S2B", "need_more_info"),
            ("S2B", "Inability to have penetrative vaginal intercourse (coital difficulties)?", "FERT-008", "S2C", "need_more_info"),
            ("S2C", "Concurrent disabling period pain or endometriosis suspicion signal (D13)?", "ENDO-006", "S3", "need_more_info"),
            ("S3", "Ovulatory dysfunction pattern or irregular cycles while trying (D12)?", "FERT-005", "S4", "need_more_info"),
            ("S4", "Age under 35 AND trying to conceive for 12 months or longer?", "FERT-002", "S4B", "need_more_info"),
            ("S4B", "Age 35 or older AND trying to conceive for 6 months or longer?", "FERT-003", "S4C", "need_more_info"),
            ("S4C", "Age 35 AND trying < 6 months (pending clinical decision DEC-09)?", "PATH-FERT-01-TERM-AGE35", "S4D", "need_more_info"),
            ("S4D", "Age 36 to 40 AND trying < 6 months (NICE earlier consultation option)?", "FERT-004", "S5", "need_more_info"),
            ("S5", "Age < 35, trying < 12 months, all fertility risk factors negative?", "FERT-001", "need_more_info", "need_more_info"),
        ]
        fert_terminals = {
            "FERT-007": ("Recurrent Pregnancy Loss", "In-person antiphospholipid & anatomical evaluation (DEC-10)", UrgencyLevel.CLINIC_VISIT),
            "FERT-006": ("High-Risk Tubal Factor History", "In-person patency investigation (HyCoSy / HSG)", UrgencyLevel.CLINIC_VISIT),
            "FERT-008": ("Inability to Have Intercourse", "In-person psychosexual & pelvic floor evaluation", UrgencyLevel.CLINIC_VISIT),
            "ENDO-006": ("Concurrent Endometriosis & Fertility", "Specialist fertility & endometriosis assessment", UrgencyLevel.CLINIC_VISIT),
            "FERT-005": ("Subfertility with Ovulatory Disorder", "Hormonal profile, ovulation induction workup", UrgencyLevel.TELECONSULTATION),
            "FERT-002": ("Formal Infertility Workup", "Standard investigation after 12 months trying (NICE / ASRM)", UrgencyLevel.TELECONSULTATION),
            "FERT-003": ("Earlier Fertility Evaluation (>=35)", "Investigation after 6 months trying at age 35+ (ASRM)", UrgencyLevel.TELECONSULTATION),
            "PATH-FERT-01-TERM-AGE35": ("Age 35 Trying < 6 Months", "Pending clinical decision (DEC-09); no auto-Yellow/Green", UrgencyLevel.NONE),
            "FERT-004": ("Earlier Consultation (Age 36-40)", "Proposed earlier discussion pending doctor approval (DEC-09)", UrgencyLevel.TELECONSULTATION),
            "FERT-001": ("Normal Conception Window", "Preconception counseling & 400 mcg folic acid daily", UrgencyLevel.SELF_CARE),
        }
        render_flowchart_image(
            "TOPIC 4: FERTILITY & PRECONCEPTION CLINICAL TRIAGE PATHWAY",
            "Reference: NICE NG257 (Fertility problems), ASRM Guidelines, & ESHRE Recurrent Loss Guideline",
            fert_steps,
            fert_terminals,
            output_dir / "fertility_flowchart.png",
        )

    # 4. Irregular Periods Flowchart
    mmd_irr = generate_mermaid_irregular(rules_by_id)
    with open(output_dir / "irregular_periods_flowchart.mmd", "w") as f:
        f.write(mmd_irr)

    irr_steps = [
        ("RF", "Emergency Red Flags (instability, acute abdomen, soaking hourly pad)?", "RF-003", "S1", "need_more_info"),
        ("S1", "Amenorrhea Gate: Days since last period > 90 OR never menstruated?", "IRR-004", "S2", "need_more_info"),
        ("S2", "Abnormal Bleeding: Intermenstrual bleeding for 2+ cycles or persistent pain?", "IRR-007", "S3", "need_more_info"),
        ("S3", "Postcoital Bleeding: Any vaginal bleeding during or after intercourse?", "IRR-008", "S4", "need_more_info"),
        ("S4", "Heavy Menstrual Bleeding with symptomatic anemia (pallor, fatigue)?", "IRR-009", "S5", "need_more_info"),
        ("S5", "Acute stable heavy flooding or passing clots > 2.5 cm?", "IRR-007A", "S6", "need_more_info"),
        ("S6", "Uncomplicated Heavy Menstrual Bleeding (> 8 days or heavy flow)?", "IRR-005", "S7", "need_more_info"),
        ("S7", "FIGO Normal Menstrual Regularity (length 24-38d, variation <= 7-9d)?", "IRR-001", "need_more_info", "need_more_info"),
    ]
    irr_terminals = {
        "RF-003": ("Emergency Red Flag", "Hemodynamic instability or active hemorrhage", UrgencyLevel.EMERGENCY),
        "IRR-004": ("Secondary Amenorrhea", "Absence of menses > 90 days; pregnancy exclusion required", UrgencyLevel.TELECONSULTATION),
        "IRR-007": ("Recurrent Intermenstrual Bleeding", "In-person bimanual exam and transvaginal ultrasound", UrgencyLevel.CLINIC_VISIT),
        "IRR-008": ("Postcoital Bleeding", "In-person speculum examination and cervical screening check", UrgencyLevel.CLINIC_VISIT),
        "IRR-009": ("HMB with Symptomatic Anemia", "In-person CBC/ferritin and clinical evaluation", UrgencyLevel.CLINIC_VISIT),
        "IRR-007A": ("Acute Stable Heavy Menstrual Bleeding", "Oral tranexamic acid / progestin protocol review", UrgencyLevel.CLINIC_VISIT),
        "IRR-005": ("Uncomplicated Heavy Menstrual Bleeding", "First-line primary care therapy (LNG-IUS / tranexamic acid)", UrgencyLevel.TELECONSULTATION),
        "IRR-001": ("FIGO Normal Menstrual Regularity", "Cycle length 24-38 days with normal age-stratified variation", UrgencyLevel.SELF_CARE),
    }
    render_flowchart_image(
        "TOPIC 1: IRREGULAR & ABNORMAL MENSTRUAL BLEEDING TRIAGE PATHWAY",
        "Reference: FIGO Menstrual Disorders Committee (2018) & NICE NG88 (Heavy menstrual bleeding)",
        irr_steps,
        irr_terminals,
        output_dir / "irregular_periods_flowchart.png",
    )

    print(f"All 4 flowcharts successfully generated in {output_dir}")


if __name__ == "__main__":
    generate_all_flowcharts()

