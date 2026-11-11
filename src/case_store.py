"""Persistent SQLite storage and real-time CSV/JSON export mirrors for Cases and Doctor Reviews."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import DoctorReviewRecord, OracleExpectation, SyntheticCase, UrgencyLevel
from .review_security import SecurityManager


class ExamCaseImmutabilityError(Exception):
    """Raised when an attempt is made to mutate an exam case that already has reviews."""
    pass


class CaseStore:
    """Manages SQLite storage and CSV/JSON exports with practice/exam collection guards."""

    def __init__(self, db_path: str = "data/triage_reviews.db", export_dir: str = "data/exports"):
        self.db_path = db_path
        self.export_dir = export_dir
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        if self.db_path != ":memory:":
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            if not os.path.exists(self.db_path):
                # Touch with 0600 permissions
                fd = os.open(self.db_path, os.O_CREAT | os.O_WRONLY, 0o600)
                os.close(fd)
            else:
                try:
                    os.chmod(self.db_path, 0o600)
                except OSError:
                    pass

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS synthetic_cases (
                        case_id TEXT PRIMARY KEY,
                        collection TEXT NOT NULL CHECK(collection IN ('practice', 'exam')),
                        batch_id TEXT,
                        topic TEXT NOT NULL,
                        difficulty TEXT NOT NULL,
                        patient_summary_json TEXT NOT NULL,
                        patient_inputs_json TEXT NOT NULL,
                        missing_inputs_json TEXT NOT NULL,
                        oracle_json TEXT NOT NULL,
                        case_sha256 TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS doctor_reviews (
                        review_id TEXT PRIMARY KEY,
                        case_id TEXT NOT NULL REFERENCES synthetic_cases(case_id),
                        case_type TEXT NOT NULL CHECK(case_type IN ('practice', 'exam')),
                        batch_id TEXT NOT NULL,
                        doctor_name TEXT NOT NULL,
                        patient_data_json TEXT NOT NULL,
                        doctor_level TEXT NOT NULL,
                        doctor_colour TEXT NOT NULL,
                        doctor_initial_notes TEXT,
                        engine_output_json TEXT NOT NULL,
                        engine_level TEXT NOT NULL,
                        engine_colour TEXT NOT NULL,
                        fired_rule_ids_json TEXT NOT NULL,
                        engine_version TEXT NOT NULL,
                        rule_set_version TEXT NOT NULL,
                        agreement_status TEXT NOT NULL CHECK(agreement_status IN ('same', 'engine_higher', 'engine_lower')),
                        verdict TEXT,
                        problem_chips_json TEXT,
                        doctor_feedback_text TEXT,
                        correction_request TEXT,
                        review_status TEXT NOT NULL CHECK(review_status IN ('assessed', 'feedback_complete')),
                        submitted_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reviews_case ON doctor_reviews(case_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reviews_doc_batch ON doctor_reviews(doctor_name, batch_id)"
                )
        finally:
            conn.close()

    @staticmethod
    def compute_case_hash(patient_inputs: Dict[str, Any], oracle_dict: Dict[str, Any]) -> str:
        data = json.dumps({"inputs": patient_inputs, "oracle": oracle_dict}, sort_keys=True)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def save_synthetic_case(self, case: SyntheticCase) -> None:
        """Save a synthetic case with immutability protection for reviewed exam cases."""
        SecurityManager.validate_synthetic_case(case.to_dict(include_oracle=True))

        oracle_dict = case.oracle.to_dict() if case.oracle else {}
        case_hash = case.case_sha256 or self.compute_case_hash(case.patient_inputs, oracle_dict)
        case.case_sha256 = case_hash

        conn = self._get_connection()
        try:
            with conn:
                # Check immutability if case exists
                cur = conn.cursor()
                cur.execute(
                    "SELECT c.collection, COUNT(r.review_id) FROM synthetic_cases c LEFT JOIN doctor_reviews r ON c.case_id = r.case_id WHERE c.case_id = ? GROUP BY c.case_id",
                    (case.case_id,),
                )
                row = cur.fetchone()
                if row:
                    col, review_count = row[0], row[1]
                    if col == "exam" and review_count > 0:
                        raise ExamCaseImmutabilityError(
                            f"Cannot modify exam case {case.case_id} because it already has {review_count} recorded doctor reviews."
                        )

                conn.execute(
                    """
                    INSERT OR REPLACE INTO synthetic_cases (
                        case_id, collection, batch_id, topic, difficulty,
                        patient_summary_json, patient_inputs_json, missing_inputs_json,
                        oracle_json, case_sha256, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case.case_id,
                        case.collection,
                        case.batch_id,
                        case.topic,
                        case.difficulty,
                        json.dumps(case.patient_summary_lines),
                        json.dumps(case.patient_inputs),
                        json.dumps(case.missing_or_unknown_fields),
                        json.dumps(oracle_dict),
                        case_hash,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        finally:
            conn.close()

    def get_case(self, case_id: str) -> Optional[SyntheticCase]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM synthetic_cases WHERE case_id = ?", (case_id,))
            row = cur.fetchone()
            if not row:
                return None
            oracle_dict = json.loads(row["oracle_json"])
            oracle = OracleExpectation(**oracle_dict) if oracle_dict else None
            return SyntheticCase(
                case_id=row["case_id"],
                collection=row["collection"],
                batch_id=row["batch_id"],
                topic=row["topic"],
                difficulty=row["difficulty"],
                patient_summary_lines=json.loads(row["patient_summary_json"]),
                patient_inputs=json.loads(row["patient_inputs_json"]),
                missing_or_unknown_fields=json.loads(row["missing_inputs_json"]),
                oracle=oracle,
                case_sha256=row["case_sha256"],
                synthetic=True,
            )
        finally:
            conn.close()

    def get_public_case_for_doctor(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Returns stripped case for doctor pre-submission evaluation (zero answer leakage)."""
        case = self.get_case(case_id)
        if not case:
            return None
        return SecurityManager.strip_case_for_doctor(case.to_dict(include_oracle=False))

    def load_cases_by_batch(self, batch_id: str) -> List[SyntheticCase]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM synthetic_cases WHERE batch_id = ? ORDER BY case_id ASC",
                (batch_id,),
            )
            cases: List[SyntheticCase] = []
            for row in cur.fetchall():
                oracle_dict = json.loads(row["oracle_json"])
                oracle = OracleExpectation(**oracle_dict) if oracle_dict else None
                cases.append(
                    SyntheticCase(
                        case_id=row["case_id"],
                        collection=row["collection"],
                        batch_id=row["batch_id"],
                        topic=row["topic"],
                        difficulty=row["difficulty"],
                        patient_summary_lines=json.loads(row["patient_summary_json"]),
                        patient_inputs=json.loads(row["patient_inputs_json"]),
                        missing_or_unknown_fields=json.loads(row["missing_inputs_json"]),
                        oracle=oracle,
                        case_sha256=row["case_sha256"],
                        synthetic=True,
                    )
                )
            return cases
        finally:
            conn.close()

    def get_doctor_completed_case_ids(self, doctor_name: str, batch_id: str) -> List[str]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT DISTINCT case_id FROM doctor_reviews WHERE LOWER(TRIM(doctor_name)) = LOWER(TRIM(?)) AND batch_id = ?",
                (doctor_name, batch_id),
            )
            return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()

    def record_doctor_assessment(
        self,
        case_id: str,
        doctor_name: str,
        doctor_level: str,
        doctor_colour: str,
        doctor_initial_notes: Optional[str],
        engine_result_dict: Dict[str, Any],
        engine_version: str = "0.2.0-alpha",
        rule_set_version: str = "rules-v0.2",
    ) -> DoctorReviewRecord:
        """Records initial assessment, performs rank comparison, and commits review."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case '{case_id}' does not exist.")

        engine_urgency = engine_result_dict.get("urgency", {})
        engine_level = engine_urgency.get("level", "none")
        engine_colour = engine_urgency.get("colour", "none")
        fired_rules = engine_result_dict.get("metadata", {}).get("fired_rules", [])

        # Agreement rank calculation
        rank_map = {
            "emergency": 4,
            "clinic_visit": 3,
            "teleconsultation": 2,
            "self_care": 1,
            "none": 0,
        }
        doc_rank = rank_map.get(doctor_level.lower(), 0)
        eng_rank = rank_map.get(engine_level.lower(), 0)

        if doc_rank == eng_rank:
            agreement_status = "same"
        elif eng_rank > doc_rank:
            agreement_status = "engine_higher"
        else:
            agreement_status = "engine_lower"

        review_id = f"REV-{uuid.uuid4().hex[:12].upper()}"
        record = DoctorReviewRecord(
            review_id=review_id,
            case_id=case_id,
            case_type=case.collection,
            batch_id=case.batch_id or "default",
            doctor_name=doctor_name,
            patient_data_json=json.dumps(case.patient_inputs),
            doctor_level=doctor_level,
            doctor_colour=doctor_colour,
            doctor_initial_notes=doctor_initial_notes or "",
            engine_output_json=json.dumps(engine_result_dict),
            engine_level=engine_level,
            engine_colour=engine_colour,
            fired_rule_ids_json=json.dumps(fired_rules),
            engine_version=engine_version,
            rule_set_version=rule_set_version,
            agreement_status=agreement_status,
            review_status="assessed",
            submitted_at=datetime.now(timezone.utc).isoformat(),
        )

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO doctor_reviews (
                        review_id, case_id, case_type, batch_id, doctor_name,
                        patient_data_json, doctor_level, doctor_colour, doctor_initial_notes,
                        engine_output_json, engine_level, engine_colour, fired_rule_ids_json,
                        engine_version, rule_set_version, agreement_status, review_status,
                        submitted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.review_id,
                        record.case_id,
                        record.case_type,
                        record.batch_id,
                        record.doctor_name,
                        record.patient_data_json,
                        record.doctor_level,
                        record.doctor_colour,
                        record.doctor_initial_notes,
                        record.engine_output_json,
                        record.engine_level,
                        record.engine_colour,
                        record.fired_rule_ids_json,
                        record.engine_version,
                        record.rule_set_version,
                        record.agreement_status,
                        record.review_status,
                        record.submitted_at,
                    ),
                )
        finally:
            conn.close()

        self.export_reviews_csv_and_json()
        return record

    def record_doctor_feedback(
        self,
        review_id: str,
        doctor_name: str,
        verdict: Optional[str] = None,
        problem_chips: Optional[List[str]] = None,
        feedback_text: Optional[str] = None,
        correction_request: Optional[str] = None,
    ) -> bool:
        """Update review with doctor disagreement feedback and finish review."""
        conn = self._get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT doctor_name FROM doctor_reviews WHERE review_id = ?",
                    (review_id,),
                )
                row = cur.fetchone()
                if not row or row[0] != doctor_name:
                    return False

                conn.execute(
                    """
                    UPDATE doctor_reviews
                    SET verdict = ?, problem_chips_json = ?, doctor_feedback_text = ?,
                        correction_request = ?, review_status = 'feedback_complete'
                    WHERE review_id = ?
                    """,
                    (
                        verdict,
                        json.dumps(problem_chips or []),
                        feedback_text,
                        correction_request,
                        review_id,
                    ),
                )
        finally:
            conn.close()

        self.export_reviews_csv_and_json()
        return True

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM doctor_reviews WHERE review_id = ?", (review_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()

    def get_all_reviews(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM doctor_reviews ORDER BY submitted_at ASC")
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def export_reviews_csv_and_json(self) -> None:
        """Auto-sync SQLite records to owner-only CSV and JSON mirror files."""
        reviews = self.get_all_reviews()
        if not self.export_dir:
            return

        os.makedirs(self.export_dir, exist_ok=True)
        csv_path = os.path.join(self.export_dir, "reviews_export.csv")
        json_path = os.path.join(self.export_dir, "reviews_export.json")

        # 1. Export JSON
        fd = os.open(json_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=2)

        # 2. Export CSV
        if reviews:
            fieldnames = [
                "review_id",
                "case_id",
                "case_type",
                "batch_id",
                "doctor_name",
                "doctor_level",
                "doctor_colour",
                "engine_level",
                "engine_colour",
                "agreement_status",
                "verdict",
                "problem_chips_json",
                "doctor_feedback_text",
                "correction_request",
                "fired_rule_ids_json",
                "submitted_at",
            ]
            fd = os.open(csv_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
            with open(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for r in reviews:
                    writer.writerow(r)

