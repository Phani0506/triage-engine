"""Zero-dependency phone-friendly Doctor Review HTTP server with token security."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import random
import ssl
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .case_store import CaseStore
from .engine import TriageEngine
from .feedback_report import FeedbackReportGenerator
from .review_security import AuthContext, SecurityManager


class ReviewRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests with security authentication, anti-leakage filters and role separation."""

    server_version = "AntigravityReviewServer/0.2.0"

    @property
    def security_manager(self) -> SecurityManager:
        return self.server.security_manager  # type: ignore

    @property
    def case_store(self) -> CaseStore:
        return self.server.case_store  # type: ignore

    @property
    def triage_engine(self) -> TriageEngine:
        return self.server.triage_engine  # type: ignore

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def _get_auth_token(self) -> Optional[str]:
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        tok = self.headers.get("X-Review-Token")
        if tok:
            return tok.strip()
        # Fallback to query param if not in header (e.g. initial static browser load)
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if "token" in qs and qs["token"]:
            return qs["token"][0].strip()
        return None

    def _authenticate(self) -> AuthContext:
        token = self._get_auth_token()
        client_ip = self._client_ip()
        return self.security_manager.authenticate_token(token, client_ip)

    def _send_security_headers(self, content_type: str = "application/json") -> None:
        self.send_header("Content-Type", content_type)
        for h, val in SecurityManager.get_security_headers().items():
            self.send_header(h, val)

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self._send_security_headers("application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json({"error": message, "status": status}, status=status)

    def _check_https_enforcement(self) -> bool:
        if getattr(self.server, "trust_proxy_https", False):
            proto = self.headers.get("X-Forwarded-Proto", "").lower()
            if proto != "https":
                self.send_response(HTTPStatus.FORBIDDEN)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"HTTPS is required. Plain HTTP requests are forbidden.")
                return False
        return True

    def do_GET(self) -> None:
        if not self._check_https_enforcement():
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Static assets (HTML, CSS, JS) - Open to browser, JS uses token in fragment / storage
        if path in ("/", "/index.html"):
            return self._serve_static_file("review.html", "text/html; charset=utf-8")
        if path == "/review.css":
            return self._serve_static_file("review.css", "text/css; charset=utf-8")
        if path == "/review.js":
            return self._serve_static_file("review.js", "application/javascript; charset=utf-8")

        # API Auth check
        auth = self._authenticate()
        if not auth.authenticated:
            return self._send_error_json(HTTPStatus.UNAUTHORIZED, "Authentication required. Provide valid token.")

        # API: Auth status
        if path == "/api/auth/verify":
            return self._send_json({
                "authenticated": True,
                "role": auth.role,
                "doctor_name": auth.doctor_name,
            })

        # API: List cases for a batch (Doctor or Admin)
        if path.startswith("/api/batches/") and "/cases" in path:
            batch_id = path.split("/")[3]
            cases = self.case_store.load_cases_by_batch(batch_id)
            completed_ids: list[str] = []
            doc_query = query.get("doctor", [None])[0]
            target_doctor = doc_query or auth.doctor_name
            if target_doctor:
                completed_ids = self.case_store.get_doctor_completed_case_ids(target_doctor, batch_id)
                # Deterministic pseudo-random shuffle per doctor to interleave urgencies naturally
                seed_val = int(hashlib.md5(f"{target_doctor.strip().lower()}_{batch_id}".encode()).hexdigest(), 16) % (10**8)
                rng = random.Random(seed_val)
                rng.shuffle(cases)
            summaries = [
                {
                    "case_id": c.case_id,
                    "topic": c.topic,
                    "difficulty": c.difficulty,
                }
                for c in cases
            ]
            return self._send_json({
                "batch_id": batch_id,
                "cases": summaries,
                "completed_case_ids": completed_ids,
                "total_cases": len(cases),
            })

        # API: Get single case (Anti-leakage: stripped case for doctor review)
        if path.startswith("/api/cases/"):
            case_id = path.split("/")[3]
            stripped_case = self.case_store.get_public_case_for_doctor(case_id)
            if not stripped_case:
                return self._send_error_json(HTTPStatus.NOT_FOUND, f"Case '{case_id}' not found.")
            return self._send_json(stripped_case)

        # Admin routes: Report and Analytics (Forbidden to doctor role)
        if path in ("/report", "/api/admin/report"):
            if auth.role != "admin":
                return self._send_error_json(HTTPStatus.FORBIDDEN, "Access denied: Admin role required.")
            batch_id = query.get("batch", [None])[0]
            include_test = query.get("include_test", ["false"])[0].lower() in ("true", "1", "yes")
            rep_gen = FeedbackReportGenerator(case_store=self.case_store)
            report_text = rep_gen.generate_markdown_report(batch_id=batch_id, exclude_test=not include_test)
            if path == "/report":
                # Render formatted HTML report wrapper
                html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Antigravity Triage Feedback Report</title>
<style>body{{font-family:sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;line-height:1.5;}}
pre{{background:#f8fafc;padding:1rem;border:1px solid #cbd5e1;border-radius:6px;overflow-x:auto;}}</style>
</head><body><pre>{report_text}</pre></body></html>"""
                payload = html_body.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self._send_security_headers("text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            return self._send_json({"report_markdown": report_text})

        if path == "/api/admin/reviews":
            if auth.role != "admin":
                return self._send_error_json(HTTPStatus.FORBIDDEN, "Access denied: Admin role required.")
            reviews = self.case_store.get_all_reviews()
            return self._send_json({"reviews": reviews, "count": len(reviews)})

        return self._send_error_json(HTTPStatus.NOT_FOUND, f"Endpoint '{path}' not found.")

    def do_POST(self) -> None:
        if not self._check_https_enforcement():
            return

        parsed = urlparse(self.path)
        path = parsed.path

        auth = self._authenticate()
        if not auth.authenticated:
            return self._send_error_json(HTTPStatus.UNAUTHORIZED, "Authentication required.")

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 1024 * 1024:  # 1MB limit
            return self._send_error_json(HTTPStatus.BAD_REQUEST, "Payload too large.")

        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            return self._send_error_json(HTTPStatus.BAD_REQUEST, "Invalid JSON body.")

        # 1. Submit initial blind assessment (Doctor only)
        if path == "/api/reviews/submit-assessment":
            if auth.role != "doctor":
                return self._send_error_json(HTTPStatus.FORBIDDEN, "Only doctors can submit assessments.")

            case_id = payload.get("case_id")
            doctor_level = payload.get("doctor_level")
            doctor_colour = payload.get("doctor_colour")
            initial_notes = payload.get("doctor_initial_notes", "")

            if not case_id or not doctor_level or not doctor_colour:
                return self._send_error_json(HTTPStatus.BAD_REQUEST, "Missing required assessment fields.")

            case = self.case_store.get_case(case_id)
            if not case:
                return self._send_error_json(HTTPStatus.NOT_FOUND, f"Case '{case_id}' not found.")

            # Run deterministic engine server-side AFTER doctor level is received
            engine_result = self.triage_engine.evaluate(case.patient_inputs)
            engine_dict = engine_result.to_dict()

            doctor_name = (payload.get("doctor_name") or auth.doctor_name or "Doctor").strip()
            record = self.case_store.record_doctor_assessment(
                case_id=case_id,
                doctor_name=doctor_name,
                doctor_level=doctor_level,
                doctor_colour=doctor_colour,
                doctor_initial_notes=initial_notes,
                engine_result_dict=engine_dict,
            )

            # Return revealed engine result
            return self._send_json({
                "review_id": record.review_id,
                "case_id": case_id,
                "agreement_status": record.agreement_status,
                "engine_level": record.engine_level,
                "engine_colour": record.engine_colour,
                "reasons": engine_dict.get("reasons", []),
                "advice": engine_dict.get("advice", ""),
                "doctor_may_suggest": engine_dict.get("doctor_may_suggest", []),
                "fired_rules": engine_dict.get("metadata", {}).get("fired_rules", []),
            })

        # 2. Submit post-reveal disagreement feedback (Doctor only)
        if path == "/api/reviews/submit-feedback":
            if auth.role != "doctor":
                return self._send_error_json(HTTPStatus.FORBIDDEN, "Only doctors can submit feedback.")

            review_id = payload.get("review_id")
            verdict = payload.get("verdict")
            problem_chips = payload.get("problem_chips", [])
            feedback_text = payload.get("feedback_text", "")
            correction_request = payload.get("correction_request")

            if not review_id:
                return self._send_error_json(HTTPStatus.BAD_REQUEST, "Missing review_id.")

            doctor_name = (payload.get("doctor_name") or auth.doctor_name or "Doctor").strip()
            ok = self.case_store.record_doctor_feedback(
                review_id=review_id,
                doctor_name=doctor_name,
                verdict=verdict,
                problem_chips=problem_chips,
                feedback_text=feedback_text,
                correction_request=correction_request,
            )
            if not ok:
                return self._send_error_json(HTTPStatus.FORBIDDEN, "Could not update review feedback.")

            return self._send_json({"success": True, "review_id": review_id})

        return self._send_error_json(HTTPStatus.NOT_FOUND, f"Endpoint '{path}' not found.")

    def _serve_static_file(self, filename: str, content_type: str) -> None:
        """Serve whitelisted static files from src/static directory with path-traversal prevention."""
        clean_name = os.path.basename(filename)
        static_dir = Path(__file__).parent / "static"
        file_path = (static_dir / clean_name).resolve()

        if not file_path.is_file() or not str(file_path).startswith(str(static_dir.resolve())):
            return self._send_error_json(HTTPStatus.NOT_FOUND, "Static asset not found.")

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self._send_security_headers(content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error reading asset: {e}")


def run_review_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    batch_id: str = "batch1",
    tls_cert: Optional[str] = None,
    tls_key: Optional[str] = None,
    trust_proxy_https: bool = False,
    db_path: str = "data/triage_reviews.db",
) -> None:
    """Starts the secured ThreadingHTTPServer."""
    # Loopback-only bind guard
    is_loopback = host in ("127.0.0.1", "localhost", "::1")
    if not is_loopback and not (tls_cert and tls_key) and not trust_proxy_https:
        raise ValueError(
            f"Refusing to bind to non-loopback address '{host}' without TLS or --trust-proxy-https. "
            "Security invariant requires loopback-first binding or HTTPS termination."
        )

    security_manager = SecurityManager()
    case_store = CaseStore(db_path=db_path)
    triage_engine = TriageEngine()

    # Auto-seed default batch cases if starting on fresh cloud database
    existing_cases = case_store.load_cases_by_batch(batch_id)
    if not existing_cases:
        from .synthetic_generator import SyntheticPatientGenerator
        print(f"Fresh database detected. Auto-seeding {batch_id} cases...")
        gen = SyntheticPatientGenerator(seed=42)
        batch_cases = gen.generate_batch1_cases()
        for c in batch_cases:
            case_store.save_synthetic_case(c)
        print(f"Successfully seeded {len(batch_cases)} cases into {db_path}!")

    server = ThreadingHTTPServer((host, port), ReviewRequestHandler)
    server.security_manager = security_manager  # type: ignore
    server.case_store = case_store  # type: ignore
    server.triage_engine = triage_engine  # type: ignore
    server.trust_proxy_https = trust_proxy_https  # type: ignore

    if tls_cert and tls_key:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=tls_cert, keyfile=tls_key)
        server.socket = context.wrap_socket(server.socket, server_side=True)

    proto = "https" if (tls_cert and tls_key) else "http"
    print(f"============================================================")
    print(f" Antigravity Women's Health Triage Doctor Review Server")
    print(f" Running at: {proto}://{host}:{port}/")
    print(f" Default Batch: {batch_id}")
    print(f" Bound to loopback: {is_loopback}")
    print(f" Security: Cryptographic Token Auth Active")
    print(f"============================================================")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReview server stopped gracefully.")
        server.server_close()


def main() -> None:
    env_port = int(os.environ.get("PORT", "8080"))
    env_host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    trust_proxy = bool(os.environ.get("PORT") or os.environ.get("TRUST_PROXY_HTTPS"))

    parser = argparse.ArgumentParser(description="Antigravity Doctor Review Server")
    parser.add_argument("--host", type=str, default=env_host)
    parser.add_argument("--port", type=int, default=env_port)
    parser.add_argument("--batch", type=str, default="batch1")
    parser.add_argument("--tls-cert", type=str, default=None)
    parser.add_argument("--tls-key", type=str, default=None)
    parser.add_argument("--trust-proxy-https", action="store_true", default=trust_proxy)
    parser.add_argument("--db-path", type=str, default="data/triage_reviews.db")
    args = parser.parse_args()

    run_review_server(
        host=args.host,
        port=args.port,
        batch_id=args.batch,
        tls_cert=args.tls_cert,
        tls_key=args.tls_key,
        trust_proxy_https=args.trust_proxy_https,
        db_path=args.db_path,
    )


if __name__ == "__main__":
    main()

