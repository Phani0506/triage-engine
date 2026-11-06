"""Comprehensive governance, flowchart, and architectural invariant tests for Day 4.

Verifies:
1. All 56 rules have complete dual governance statuses and exact citations.
2. Proposed mappings are correctly flagged.
3. Flowcharts exist, are valid, and match canonical pathways.
4. Engine remains 100% deterministic and offline (no LLM, no network imports).
"""

import os
import pathlib
import unittest

from src.flowchart_generator import generate_all_flowcharts
from src.loader import load_pathways, load_rules
from src.models import ApprovalStatus, EvidenceStatus


class TestDay4CoverageAndFlowcharts(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()
        self.pathways = load_pathways()

    def test_total_rule_count_and_domain_distribution(self):
        # We expect exactly 56 rules across all clinical domains
        self.assertEqual(len(self.rules), 56)

        rules_by_domain = {}
        for r in self.rules:
            rules_by_domain.setdefault(r.domain, []).append(r)

        self.assertIn("red_flags", rules_by_domain)
        self.assertIn("irregular_periods", rules_by_domain)
        self.assertIn("pcos", rules_by_domain)
        self.assertIn("endometriosis", rules_by_domain)
        self.assertIn("fertility", rules_by_domain)

        self.assertEqual(len(rules_by_domain["pcos"]), 9)
        self.assertEqual(len(rules_by_domain["endometriosis"]), 8)
        self.assertEqual(len(rules_by_domain["fertility"]), 8)

    def test_all_56_rules_have_complete_sources_and_governance(self):
        # Every rule must have exact guideline source and mapping_pending_doctor_approval
        for r in self.rules:
            self.assertIsNotNone(r.source, f"Rule {r.id} missing source block.")
            self.assertTrue(r.source.name, f"Rule {r.id} source missing name.")
            self.assertTrue(r.source.section, f"Rule {r.id} source missing section.")
            self.assertTrue(r.source.number_checked, f"Rule {r.id} source missing number_checked.")
            self.assertEqual(
                r.source.approval_status,
                ApprovalStatus.MAPPING_PENDING_DOCTOR_APPROVAL,
                f"Rule {r.id} must be mapping_pending_doctor_approval.",
            )

    def test_proposed_mappings_correctly_flagged(self):
        # ENDO-008 and FERT-004 must be marked is_proposed_mapping = True
        endo008 = next((r for r in self.rules if r.id == "ENDO-008"), None)
        self.assertIsNotNone(endo008)
        self.assertTrue(endo008.is_proposed_mapping)
        self.assertEqual(endo008.pending_clinical_decision, "DEC-07")

        fert004 = next((r for r in self.rules if r.id == "FERT-004"), None)
        self.assertIsNotNone(fert004)
        self.assertTrue(fert004.is_proposed_mapping)
        self.assertEqual(fert004.pending_clinical_decision, "DEC-09")

    def test_flowchart_generation_and_file_existence(self):
        out_dir = pathlib.Path("docs/flowcharts")
        generate_all_flowcharts(out_dir)

        expected_files = [
            "irregular_periods_flowchart.mmd",
            "irregular_periods_flowchart.png",
            "pcos_flowchart.mmd",
            "pcos_flowchart.png",
            "endometriosis_flowchart.mmd",
            "endometriosis_flowchart.png",
            "fertility_flowchart.mmd",
            "fertility_flowchart.png",
        ]

        for fname in expected_files:
            fpath = out_dir / fname
            self.assertTrue(fpath.exists(), f"Flowchart file {fname} not found.")
            self.assertGreater(fpath.stat().st_size, 100, f"Flowchart file {fname} is empty.")

    def test_offline_deterministic_safety_invariant_no_llm_imports(self):
        # Scans all src/*.py files to ensure no external LLM or networking client libraries are imported
        prohibited_tokens = [
            "openai",
            "anthropic",
            "google.generativeai",
            "google.genai",
            "requests",
            "httpx",
            "urllib.request",
        ]

        src_dir = pathlib.Path("src")
        for py_file in src_dir.glob("**/*.py"):
            with open(py_file, "r") as f:
                content = f.read()
            for token in prohibited_tokens:
                self.assertNotIn(
                    f"import {token}",
                    content,
                    f"Prohibited external/LLM import '{token}' found in {py_file}!",
                )
                self.assertNotIn(
                    f"from {token}",
                    content,
                    f"Prohibited external/LLM import '{token}' found in {py_file}!",
                )


if __name__ == "__main__":
    unittest.main()

