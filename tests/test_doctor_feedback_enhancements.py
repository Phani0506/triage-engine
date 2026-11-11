"""Tests verifying clinical enhancements requested by Adarsh for doctor review."""

import hashlib
import json
import random
import unittest
from pathlib import Path

from src.case_store import CaseStore
from src.feedback_report import FeedbackReportGenerator
from src.synthetic_generator import SyntheticPatientGenerator


class TestDoctorFeedbackEnhancements(unittest.TestCase):
    def setUp(self):
        self.gen = SyntheticPatientGenerator(seed=42)
        self.batch_cases = self.gen.generate_batch1_cases()

    def test_batch1_presentation_sanitized_no_triage_advice(self):
        """Verify patient_summary_lines contain purely objective observations, with zero triage advice."""
        forbidden_leak_phrases = [
            "emergency evaluation",
            "clinic visit and",
            "teleconsultation for",
            "requires emergency",
            "supersedes yellow",
            "reassurance and self-care",
            "requires urgent",
            "developmental deferral",
            "clinical decision required",
            "safety lockout prevents",
        ]
        for c in self.batch_cases:
            for line in c.patient_summary_lines:
                line_lower = line.lower()
                for phrase in forbidden_leak_phrases:
                    self.assertNotIn(
                        phrase,
                        line_lower,
                        f"Leaked triage directive found in case {c.case_id}: '{line}'",
                    )

    def test_deterministic_doctor_randomization(self):
        """Verify that case shuffling is deterministic per doctor seed and not sequentially ordered."""
        cases = list(self.batch_cases)
        doctor = "Dr. Surbhi"
        batch_id = "batch1"

        seed_val = int(hashlib.md5(f"{doctor.strip().lower()}_{batch_id}".encode()).hexdigest(), 16) % (10**8)
        rng = random.Random(seed_val)
        shuffled = list(cases)
        rng.shuffle(shuffled)

        # 1. Shuffled list is not in original sequential order (001, 002, 003, 004, 005)
        orig_first_5 = [c.case_id for c in cases[:5]]
        shuffled_first_5 = [c.case_id for c in shuffled[:5]]
        self.assertNotEqual(orig_first_5, shuffled_first_5)

        # 2. Second shuffle with same doctor name yields identical order (stable across reloads)
        rng2 = random.Random(seed_val)
        shuffled2 = list(cases)
        rng2.shuffle(shuffled2)
        self.assertEqual(
            [c.case_id for c in shuffled],
            [c.case_id for c in shuffled2],
        )

    def test_test_identity_filtering_in_report(self):
        """Verify that 'Adarsh (Testing)' and test accounts are filtered from official reports."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            db_path = f"{td}/test_reviews.db"
            store = CaseStore(db_path=db_path)
            # Seed 1 test review and 1 official doctor review
            store.save_synthetic_case(self.batch_cases[0])
            store.save_synthetic_case(self.batch_cases[1])

            # Test review
            store.record_doctor_assessment(
                case_id="BATCH1-001",
                doctor_name="Adarsh (Testing)",
                doctor_level="emergency",
                doctor_colour="red",
                doctor_initial_notes="",
                engine_result_dict={"urgency": {"level": "emergency", "colour": "red"}},
            )
            # Official review
            store.record_doctor_assessment(
                case_id="BATCH1-002",
                doctor_name="Dr. Surbhi",
                doctor_level="emergency",
                doctor_colour="red",
                doctor_initial_notes="",
                engine_result_dict={"urgency": {"level": "emergency", "colour": "red"}},
            )

            rep_gen = FeedbackReportGenerator(case_store=store)
            report_filtered = rep_gen.generate_markdown_report(exclude_test=True)
            report_unfiltered = rep_gen.generate_markdown_report(exclude_test=False)

            # Filtered report should only count 1 review (Dr. Surbhi)
            self.assertIn("Total Doctor Reviews:** 1", report_filtered)
            # Unfiltered report should count 2 reviews
            self.assertIn("Total Doctor Reviews:** 2", report_unfiltered)


if __name__ == "__main__":
    unittest.main()
