"""Doctor review feedback analytics, confusion matrix, and safety report generator."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from .case_store import CaseStore


class FeedbackReportGenerator:
    """Computes clinical agreement metrics, confusion matrix, and safety-prioritized logs."""

    def __init__(self, case_store: Optional[CaseStore] = None, db_path: str = "data/triage_reviews.db"):
        self.case_store = case_store or CaseStore(db_path=db_path)

    def generate_markdown_report(self, batch_id: Optional[str] = None, exclude_test: bool = True) -> str:
        all_reviews = self.case_store.get_all_reviews()
        if exclude_test:
            test_patterns = ["testing", "test", "kohli", "trial"]
            reviews = [
                r for r in all_reviews
                if not any(tp in (r.get("doctor_name") or "").lower() for tp in test_patterns)
            ]
        else:
            reviews = all_reviews

        if batch_id:
            reviews = [r for r in reviews if r.get("batch_id") == batch_id]

        if not reviews:
            return (
                f"# Clinical Risk Triage Engine — Doctor Review Feedback Report\n\n"
                f"*No reviews recorded yet{' for batch ' + batch_id if batch_id else ''}.*\n"
            )

        total_reviews = len(reviews)
        agreed_count = sum(1 for r in reviews if r.get("agreement_status") == "same")
        engine_lower = [r for r in reviews if r.get("agreement_status") == "engine_lower"]
        engine_higher = [r for r in reviews if r.get("agreement_status") == "engine_higher"]
        disagreed_count = len(engine_lower) + len(engine_higher)

        agreement_pct = (agreed_count / total_reviews) * 100 if total_reviews else 0.0
        disagreement_pct = (disagreed_count / total_reviews) * 100 if total_reviews else 0.0

        # Confusion Matrix [doctor_level][engine_level]
        levels = ["emergency", "clinic_visit", "teleconsultation", "self_care"]
        engine_levels = ["emergency", "clinic_visit", "teleconsultation", "self_care", "none"]
        level_labels = {
            "emergency": "Red (Emergency)",
            "clinic_visit": "Amber (Clinic Visit)",
            "teleconsultation": "Yellow (Teleconsult)",
            "self_care": "Green (Self-Care)",
            "none": "Need More Info / None",
        }
        matrix: Dict[str, Dict[str, int]] = {dl: {el: 0 for el in engine_levels} for dl in levels}

        for r in reviews:
            dl = r.get("doctor_level", "").lower()
            el = r.get("engine_level", "").lower()
            if dl in matrix and el in matrix[dl]:
                matrix[dl][el] += 1


        # Safety Critical Misses:
        # 1. Doctor Red, Engine < Red
        # 2. Engine Green, Doctor > Green
        red_misses = [
            r for r in reviews
            if r.get("doctor_level", "").lower() == "emergency"
            and r.get("engine_level", "").lower() != "emergency"
        ]
        green_misses = [
            r for r in reviews
            if r.get("engine_level", "").lower() == "self_care"
            and r.get("doctor_level", "").lower() != "self_care"
        ]

        # Rule Disagreement Counts
        disagreement_rules: Counter[str] = Counter()
        for r in engine_lower + engine_higher:
            try:
                fired = json.loads(r.get("fired_rule_ids_json", "[]"))
                for rule_id in fired:
                    disagreement_rules[rule_id] += 1
            except Exception:
                pass

        # Build Markdown
        md: List[str] = []
        md.append("# Women's Health Clinical Risk Triage Engine — Doctor Feedback Analytics")
        if batch_id:
            md.append(f"**Target Batch:** `{batch_id}` | **Evaluated at:** {reviews[-1].get('submitted_at', '')}\n")
        else:
            md.append(f"**Total Aggregated Reviews:** {total_reviews}\n")

        # 1. Executive Summary
        md.append("## 1. Executive Summary")
        md.append(f"- **Total Doctor Reviews:** {total_reviews}")
        md.append(f"- **Exact Level Agreement:** {agreed_count} ({agreement_pct:.1f}%)")
        md.append(f"- **Disagreements:** {disagreed_count} ({disagreement_pct:.1f}%)")
        md.append(f"  - **Engine Under-triaged (Lower than Doctor):** {len(engine_lower)}")
        md.append(f"  - **Engine Over-triaged (Higher than Doctor):** {len(engine_higher)}")
        md.append(f"- **Critical Red Misses:** {len(red_misses)}")
        md.append(f"- **Critical Green Reassurance Misses:** {len(green_misses)}\n")

        # 2. Confusion Matrix
        md.append("## 2. Urgency Level Confusion Matrix")
        md.append("| Doctor Level \\ Engine Level | Red (Emergency) | Amber (Clinic Visit) | Yellow (Teleconsult) | Green (Self-Care) | Need More Info / None |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for dl in levels:
            row_vals = [str(matrix[dl][el]) for el in engine_levels]
            md.append(f"| **{level_labels[dl]}** | " + " | ".join(row_vals) + " |")
        md.append("")

        # 3. Critical Safety Misses Log
        md.append("## 3. High-Priority Safety Misses")
        if not red_misses and not green_misses:
            md.append("✅ **Zero critical safety misses detected.** No doctor Red under-triage or false Green self-care reassurance.\n")
        else:
            if red_misses:
                md.append("### 🚨 Critical Red Misses (Doctor Emergency, Engine Lower)")
                for r in red_misses:
                    md.append(f"- **Case:** `{r.get('case_id')}` | **Doctor:** {r.get('doctor_name')} | **Engine:** {r.get('engine_level')}")
                    md.append(f"  - *Doctor Notes:* {r.get('doctor_initial_notes') or 'None'}")
                    md.append(f"  - *Feedback:* {r.get('doctor_feedback_text') or 'None'}")
            if green_misses:
                md.append("### ⚠️ False Green Misses (Engine Self-Care, Doctor Higher)")
                for r in green_misses:
                    md.append(f"- **Case:** `{r.get('case_id')}` | **Doctor:** {r.get('doctor_name')} ({r.get('doctor_level')})")
                    md.append(f"  - *Doctor Notes:* {r.get('doctor_initial_notes') or 'None'}")
                    md.append(f"  - *Feedback:* {r.get('doctor_feedback_text') or 'None'}")
            md.append("")

        # 4. Frequent Rule Disagreements
        md.append("## 4. Rule Disagreement Frequency Table")
        if disagreement_rules:
            md.append("| Rule ID | Disagreement Count | Governance Note |")
            md.append("| :--- | :---: | :--- |")
            for rule_id, count in disagreement_rules.most_common(10):
                md.append(f"| `{rule_id}` | {count} | Requires clinical threshold review |")
        else:
            md.append("*No rule disagreements recorded.*")
        md.append("")

        # 5. Doctor Feedback & Requested Corrections
        md.append("## 5. Doctor Feedback & Requested Adjustments Log")
        has_feedback = False
        for r in reviews:
            text = r.get("doctor_feedback_text")
            chips = r.get("problem_chips_json")
            if text or (chips and chips != "[]"):
                has_feedback = True
                chips_list = json.loads(chips) if chips else []
                md.append(f"- **Case `{r.get('case_id')}`** ({r.get('doctor_name')}):")
                if chips_list:
                    md.append(f"  - *Problem Flags:* {', '.join(chips_list)}")
                if text:
                    md.append(f"  - *Doctor Rationale:* \"{text}\"")
                if r.get("correction_request"):
                    md.append(f"  - *Proposed Rule Change:* {r.get('correction_request')}")
        if not has_feedback:
            md.append("*No explicit doctor feedback text submitted yet.*")
        md.append("")

        return "\n".join(md)


def main() -> None:
    parser = argparse.ArgumentParser(description="Triage Feedback Report Generator")
    parser.add_argument("--batch", type=str, default=None, help="Batch ID (e.g. batch1)")
    parser.add_argument("--db-path", type=str, default="data/triage_reviews.db")
    parser.add_argument("--out", type=str, default="data/exports/feedback_report.md")
    args = parser.parse_args()

    gen = FeedbackReportGenerator(db_path=args.db_path)
    report_md = gen.generate_markdown_report(batch_id=args.batch)

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        # 0600 permissions
        fd = os.open(args.out, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with open(fd, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Report written to: {args.out}")

    print("\n" + report_md)


if __name__ == "__main__":
    main()
