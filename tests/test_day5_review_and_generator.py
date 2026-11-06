"""Automated integration tests for Day 5 Synthetic Generator, CaseStore, and Feedback Report."""

from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest

from src.case_store import CaseStore, ExamCaseImmutabilityError
from src.engine import TriageEngine
from src.feedback_report import FeedbackReportGenerator
from src.models import OracleExpectation, SyntheticCase
from src.synthetic_generator import ALL_BLUEPRINTS, SyntheticPatientGenerator


class TestDay5ReviewAndGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_reviews.db")
        self.export_dir = os.path.join(self.temp_dir.name, "exports")
        self.store = CaseStore(db_path=self.db_path, export_dir=self.export_dir)
        self.generator = SyntheticPatientGenerator(seed=2024)
        self.engine = TriageEngine()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_batch1_cases_generation_and_schema_conformity(self):
        cases = self.generator.generate_batch1_cases()
        self.assertEqual(len(cases), 18)

        for c in cases:
            self.assertTrue(c.case_id.startswith("BATCH1-"))
            self.assertEqual(c.collection, "exam")
            self.assertEqual(c.batch_id, "batch1")
            self.assertGreaterEqual(len(c.patient_summary_lines), 3)
            self.assertIn("age", c.patient_inputs)
            self.assertTrue(c.synthetic)
            self.assertIsNotNone(c.oracle)
            self.assertIn(c.oracle.expected_level, ["emergency", "clinic_visit", "teleconsultation", "self_care", "none", "need_more_info"])

    def test_practice_and_exam_collection_generation(self):
        practice_cases = self.generator.generate_collection("practice", count=40)
        self.assertEqual(len(practice_cases), 40)
        for c in practice_cases:
            self.assertTrue(c.case_id.startswith("PRAC-"))
            self.assertEqual(c.collection, "practice")

        exam_cases = self.generator.generate_collection("exam", count=30)
        self.assertEqual(len(exam_cases), 30)
        for c in exam_cases:
            self.assertTrue(c.case_id.startswith("EXAM-"))
            self.assertEqual(c.collection, "exam")

    def test_case_store_exam_immutability_guard(self):
        # Create an exam case
        case = self.generator.generate_case_from_blueprint(
            ALL_BLUEPRINTS[0],
            case_id="EXAM-999",
            collection="exam",
            batch_id="exam_vault",
        )
        self.store.save_synthetic_case(case)

        # Before any review, saving is permitted
        self.store.save_synthetic_case(case)

        # Record a doctor review on this exam case
        engine_dict = self.engine.evaluate(case.patient_inputs).to_dict()
        self.store.record_doctor_assessment(
            case_id="EXAM-999",
            doctor_name="dr_smitha",
            doctor_level="emergency",
            doctor_colour="red",
            doctor_initial_notes="Acute abdomen",
            engine_result_dict=engine_dict,
        )

        # Attempting to mutate reviewed exam case must raise ExamCaseImmutabilityError
        with self.assertRaises(ExamCaseImmutabilityError):
            self.store.save_synthetic_case(case)

    def test_end_to_end_doctor_review_lifecycle_and_exports(self):
        # 1. Setup case
        case = self.generator.generate_batch1_cases()[5]  # BATCH1-006 (PCOS Yellow)
        self.store.save_synthetic_case(case)

        # 2. Verify public view is stripped (Anti-leakage)
        public_case = self.store.get_public_case_for_doctor(case.case_id)
        self.assertNotIn("oracle", public_case)
        self.assertNotIn("expected_level", public_case)
        self.assertNotIn("engine_output", public_case)

        # 3. Doctor submits assessment
        engine_dict = self.engine.evaluate(case.patient_inputs).to_dict()
        review = self.store.record_doctor_assessment(
            case_id=case.case_id,
            doctor_name="dr_surbhi",
            doctor_level="teleconsultation",
            doctor_colour="yellow",
            doctor_initial_notes="Classic PCOS features",
            engine_result_dict=engine_dict,
        )
        self.assertEqual(review.agreement_status, "same")
        self.assertEqual(review.review_status, "assessed")

        # 4. Check auto-export CSV and JSON exists
        csv_path = os.path.join(self.export_dir, "reviews_export.csv")
        json_path = os.path.join(self.export_dir, "reviews_export.json")
        self.assertTrue(os.path.exists(csv_path))
        self.assertTrue(os.path.exists(json_path))

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["doctor_name"], "dr_surbhi")
            self.assertEqual(rows[0]["agreement_status"], "same")

        # 5. Doctor submits feedback on disagreement simulation
        # Add a disagreement review
        review2 = self.store.record_doctor_assessment(
            case_id=case.case_id,
            doctor_name="dr_smitha",
            doctor_level="clinic_visit",  # Doctor higher than engine Yellow
            doctor_colour="amber",
            doctor_initial_notes="Prefers in-person exam",
            engine_result_dict=engine_dict,
        )
        self.assertEqual(review2.agreement_status, "engine_lower")

        ok = self.store.record_doctor_feedback(
            review_id=review2.review_id,
            doctor_name="dr_smitha",
            verdict="doctor_is_right",
            problem_chips=["Level too low"],
            feedback_text="Needs pelvic ultrasound in clinic.",
        )
        self.assertTrue(ok)

        # Verify feedback updated in DB
        updated = self.store.get_review(review2.review_id)
        self.assertEqual(updated["review_status"], "feedback_complete")
        self.assertEqual(updated["verdict"], "doctor_is_right")
        self.assertIn("Level too low", updated["problem_chips_json"])

    def test_feedback_report_generation(self):
        # Generate 2 reviews
        cases = self.generator.generate_batch1_cases()
        for c in cases[:2]:
            self.store.save_synthetic_case(c)

        # Review 1: Agreement
        c1 = cases[0]
        res1 = self.engine.evaluate(c1.patient_inputs).to_dict()
        self.store.record_doctor_assessment(
            case_id=c1.case_id,
            doctor_name="adarsh",
            doctor_level="emergency",
            doctor_colour="red",
            doctor_initial_notes="",
            engine_result_dict=res1,
        )

        # Review 2: Disagreement
        c2 = cases[1]
        res2 = self.engine.evaluate(c2.patient_inputs).to_dict()
        self.store.record_doctor_assessment(
            case_id=c2.case_id,
            doctor_name="adarsh",
            doctor_level="clinic_visit",
            doctor_colour="amber",
            doctor_initial_notes="",
            engine_result_dict=res2,
        )

        reporter = FeedbackReportGenerator(case_store=self.store)
        md_report = reporter.generate_markdown_report()

        self.assertIn("Executive Summary", md_report)
        self.assertIn("Urgency Level Confusion Matrix", md_report)
        self.assertIn("- **Total Doctor Reviews:** 2", md_report)



if __name__ == "__main__":
    unittest.main()
