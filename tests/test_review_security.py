"""Automated security tests verifying token enforcement, role separation, anti-leakage and HTTP guards."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from src.case_store import CaseStore
from src.review_security import RateLimiter, SecurityManager
from src.review_server import ReviewRequestHandler


class TestReviewSecurity(unittest.TestCase):
    def setUp(self):
        self.doc_token1 = SecurityManager.generate_token()
        self.doc_token2 = SecurityManager.generate_token()
        self.admin_token = SecurityManager.generate_token()

        self.sec = SecurityManager(
            doctor_tokens={"dr_smitha": self.doc_token1, "dr_surbhi": self.doc_token2},
            admin_token=self.admin_token,
        )

    def test_token_generation_entropy_and_length(self):
        tok = SecurityManager.generate_token()
        self.assertGreaterEqual(len(tok), 43)

    def test_startup_fails_closed_on_invalid_tokens(self):
        # Empty doctor tokens
        with self.assertRaises(ValueError):
            SecurityManager(doctor_tokens={}, admin_token=self.admin_token)

        # Missing admin token
        with self.assertRaises(ValueError):
            SecurityManager(doctor_tokens={"dr_smitha": self.doc_token1}, admin_token=None)

        # Token too short (<43 chars)
        with self.assertRaises(ValueError):
            SecurityManager(doctor_tokens={"dr_smitha": "short_token_123"}, admin_token=self.admin_token)

        # Duplicate doctor tokens
        with self.assertRaises(ValueError):
            SecurityManager(
                doctor_tokens={"dr1": self.doc_token1, "dr2": self.doc_token1},
                admin_token=self.admin_token,
            )

        # Identical doctor and admin token
        with self.assertRaises(ValueError):
            SecurityManager(
                doctor_tokens={"dr1": self.doc_token1},
                admin_token=self.doc_token1,
            )

    def test_authentication_roles_and_doctor_binding(self):
        # Valid doctor token 1
        auth1 = self.sec.authenticate_token(self.doc_token1, client_ip="127.0.0.1")
        self.assertTrue(auth1.authenticated)
        self.assertEqual(auth1.role, "doctor")
        self.assertEqual(auth1.doctor_name, "dr_smitha")

        # Valid doctor token 2
        auth2 = self.sec.authenticate_token(self.doc_token2, client_ip="127.0.0.1")
        self.assertTrue(auth2.authenticated)
        self.assertEqual(auth2.role, "doctor")
        self.assertEqual(auth2.doctor_name, "dr_surbhi")

        # Valid admin token
        auth_admin = self.sec.authenticate_token(self.admin_token, client_ip="127.0.0.1")
        self.assertTrue(auth_admin.authenticated)
        self.assertEqual(auth_admin.role, "admin")
        self.assertIsNone(auth_admin.doctor_name)

        # Invalid token
        auth_bad = self.sec.authenticate_token("invalid_token_candidate_at_least_43_characters_long_123", client_ip="127.0.0.1")
        self.assertFalse(auth_bad.authenticated)
        self.assertEqual(auth_bad.role, "anonymous")

    def test_token_expiry_handling(self):
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        expired_sec = SecurityManager(
            doctor_tokens={"dr_smitha": self.doc_token1},
            admin_token=self.admin_token,
            expires_at=past_date,
        )
        auth = expired_sec.authenticate_token(self.doc_token1, client_ip="127.0.0.1")
        self.assertFalse(auth.authenticated)

    def test_rate_limiter_lockout(self):
        rl = RateLimiter(max_failures=3, window_seconds=60, lockout_seconds=60)
        client_ip = "192.168.1.100"
        self.assertFalse(rl.is_locked(client_ip))

        rl.record_failure(client_ip)
        rl.record_failure(client_ip)
        self.assertFalse(rl.is_locked(client_ip))

        rl.record_failure(client_ip)  # 3rd failure triggers lockout
        self.assertTrue(rl.is_locked(client_ip))

    def test_anti_leakage_case_stripping(self):
        full_case = {
            "case_id": "BATCH1-001",
            "collection": "exam",
            "batch_id": "batch1",
            "topic": "red_flags",
            "difficulty": "high_risk",
            "patient_summary_lines": ["Line 1", "Line 2"],
            "patient_inputs": {"age": 28, "severe_lower_abdominal_pain": "yes"},
            "missing_or_unknown_fields": [],
            "synthetic": True,
            # Answers that MUST be stripped:
            "oracle": {"expected_level": "emergency", "expected_colour": "red"},
            "expected_level": "emergency",
            "expected_colour": "red",
            "engine_output": {"urgency": {"level": "emergency"}},
            "fired_rules": ["RF-001"],
        }

        stripped = SecurityManager.strip_case_for_doctor(full_case)

        # Allowed keys
        self.assertEqual(stripped["case_id"], "BATCH1-001")
        self.assertIn("patient_inputs", stripped)
        self.assertIn("patient_summary_lines", stripped)

        # Prohibited keys MUST be absent
        self.assertNotIn("oracle", stripped)
        self.assertNotIn("expected_level", stripped)
        self.assertNotIn("expected_colour", stripped)
        self.assertNotIn("engine_output", stripped)
        self.assertNotIn("fired_rules", stripped)

    def test_synthetic_case_guard(self):
        # Valid synthetic case
        SecurityManager.validate_synthetic_case({"case_id": "BATCH1-001", "synthetic": True})
        SecurityManager.validate_synthetic_case({"case_id": "PRAC-001", "synthetic": True})
        SecurityManager.validate_synthetic_case({"case_id": "EXAM-001", "synthetic": True})

        # Non-synthetic rejected
        with self.assertRaises(ValueError):
            SecurityManager.validate_synthetic_case({"case_id": "BATCH1-001", "synthetic": False})

        # Invalid prefix rejected
        with self.assertRaises(ValueError):
            SecurityManager.validate_synthetic_case({"case_id": "REAL-PATIENT-001", "synthetic": True})

    def test_security_headers_present(self):
        headers = SecurityManager.get_security_headers()
        self.assertEqual(headers["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("Content-Security-Policy", headers)


if __name__ == "__main__":
    unittest.main()

