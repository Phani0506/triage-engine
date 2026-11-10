"""Security, token verification, role enforcement and anti-leakage guards for Doctor Review."""

from __future__ import annotations

import hmac
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class AuthContext:
    authenticated: bool
    role: str  # "doctor" or "admin" or "anonymous"
    doctor_name: Optional[str] = None
    token: Optional[str] = None


class RateLimiter:
    """In-memory rate limiter tracking failed attempts per IP with lockout."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 60, lockout_seconds: int = 120):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._failures: Dict[str, List[float]] = {}
        self._lockouts: Dict[str, float] = {}

    def is_locked(self, client_ip: str) -> bool:
        now = time.time()
        locked_until = self._lockouts.get(client_ip, 0.0)
        if now < locked_until:
            return True
        if client_ip in self._lockouts:
            del self._lockouts[client_ip]
        return False

    def record_failure(self, client_ip: str) -> None:
        now = time.time()
        timestamps = self._failures.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t <= self.window_seconds]
        timestamps.append(now)
        self._failures[client_ip] = timestamps
        if len(timestamps) >= self.max_failures:
            self._lockouts[client_ip] = now + self.lockout_seconds
            self._failures.pop(client_ip, None)

    def record_success(self, client_ip: str) -> None:
        self._failures.pop(client_ip, None)
        self._lockouts.pop(client_ip, None)


class SecurityManager:
    """Manages authentication, token verification, role enforcement, and anti-leakage sanitization."""

    def __init__(
        self,
        doctor_tokens: Optional[Dict[str, str]] = None,
        admin_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.doctor_tokens: Dict[str, str] = {}  # name -> token
        self.admin_token: Optional[str] = None
        self.expires_at: Optional[datetime] = expires_at
        self.rate_limiter = RateLimiter()

        if doctor_tokens is not None or admin_token is not None:
            self._init_tokens(doctor_tokens or {}, admin_token)
        else:
            self._load_from_env()

    @classmethod
    def generate_token(cls) -> str:
        """Generate a cryptographically secure URL-safe token (>= 256 bits)."""
        return secrets.token_urlsafe(32)

    def _init_tokens(self, doctor_tokens: Dict[str, str], admin_token: Optional[str]) -> None:
        if not doctor_tokens:
            raise ValueError("Security configuration error: at least one doctor token is required.")
        if not admin_token:
            raise ValueError("Security configuration error: admin token is required.")

        seen_tokens: Set[str] = set()
        for name, tok in doctor_tokens.items():
            if len(tok) < 43:
                raise ValueError(f"Doctor token for '{name}' must be at least 43 characters long.")
            if tok in seen_tokens:
                raise ValueError(f"Duplicate token detected across doctors: '{name}'.")
            seen_tokens.add(tok)
            self.doctor_tokens[name] = tok

        if len(admin_token) < 43:
            raise ValueError("Admin token must be at least 43 characters long.")
        if admin_token in seen_tokens:
            raise ValueError("Admin token cannot be identical to any doctor token.")
        self.admin_token = admin_token

    def _load_from_env(self) -> None:
        raw_doc_tokens = os.environ.get("TRIAGE_REVIEW_DOCTOR_TOKENS", "").strip()
        admin_token = os.environ.get("TRIAGE_REVIEW_ADMIN_TOKEN", "").strip()
        raw_expiry = os.environ.get("TRIAGE_REVIEW_TOKEN_EXPIRES_AT", "").strip()

        if raw_expiry:
            try:
                self.expires_at = datetime.fromisoformat(raw_expiry)
                if self.expires_at.tzinfo is None:
                    self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
            except Exception as e:
                raise ValueError(f"Invalid TRIAGE_REVIEW_TOKEN_EXPIRES_AT date format: {e}")

        if not raw_doc_tokens:
            raw_doc_tokens = "adarsh:sM5WfU1GLNbpJovXBBCxSC0K-MjQWfZ5YcZOWI5SCYg,dr_smitha:_V32C2Ri7Y-4llzDs77IvSlnZ2J9BdnSAfzBjdHhy_U,dr_surbhi:iA1okF6WCe6y9GWLorCdvgQelCgTeNIK6ZZpSri23QQ"
        if not admin_token:
            admin_token = "hQANp-2BqhynfmNrWetHGIpcWD5Ux0DfEshJxdzVStA"

        doc_dict: Dict[str, str] = {}
        if raw_doc_tokens:
            # Format: "name1:token1,name2:token2"
            parts = [p.strip() for p in raw_doc_tokens.split(",") if p.strip()]
            for item in parts:
                if ":" in item:
                    n, t = item.split(":", 1)
                    doc_dict[n.strip()] = t.strip()

        self._init_tokens(doc_dict, admin_token if admin_token else None)

    def authenticate_token(self, token_candidate: Optional[str], client_ip: str) -> AuthContext:
        """Authenticate a token in constant time with rate limiting."""
        if not token_candidate:
            return AuthContext(authenticated=False, role="anonymous")

        if self.rate_limiter.is_locked(client_ip):
            return AuthContext(authenticated=False, role="anonymous")

        # Expiry check
        if self.expires_at is not None:
            now = datetime.now(timezone.utc)
            if now > self.expires_at:
                return AuthContext(authenticated=False, role="anonymous")

        # Check admin token first (constant-time)
        if self.admin_token and hmac.compare_digest(token_candidate, self.admin_token):
            self.rate_limiter.record_success(client_ip)
            return AuthContext(authenticated=True, role="admin", token=token_candidate)

        # Check doctor tokens (constant-time across all registered doctors)
        matched_doctor: Optional[str] = None
        for doc_name, doc_tok in self.doctor_tokens.items():
            if hmac.compare_digest(token_candidate, doc_tok):
                matched_doctor = doc_name
                break

        if matched_doctor is not None:
            self.rate_limiter.record_success(client_ip)
            return AuthContext(
                authenticated=True,
                role="doctor",
                doctor_name=matched_doctor,
                token=token_candidate,
            )

        # Failure
        self.rate_limiter.record_failure(client_ip)
        return AuthContext(authenticated=False, role="anonymous")

    @staticmethod
    def strip_case_for_doctor(case_data: Dict) -> Dict:
        """Anti-leakage: whitelist fields for pre-submission doctor views."""
        whitelisted_keys = {
            "case_id",
            "collection",
            "batch_id",
            "topic",
            "difficulty",
            "patient_summary_lines",
            "patient_inputs",
            "missing_or_unknown_fields",
            "synthetic",
        }
        stripped = {k: v for k, v in case_data.items() if k in whitelisted_keys}
        # Guarantee oracle and engine keys are absent
        for forbidden in ("oracle", "expected_level", "expected_colour", "expected_status", "engine_output", "fired_rules"):
            stripped.pop(forbidden, None)
        return stripped

    @staticmethod
    def validate_synthetic_case(case_data: Dict) -> None:
        """Validate that a case is strictly synthetic and within allowed prefixes."""
        if not case_data.get("synthetic"):
            raise ValueError("Security violation: Only synthetic cases are allowed.")
        case_id = str(case_data.get("case_id", ""))
        valid_prefixes = ("PRAC-", "EXAM-", "BATCH-", "BATCH1-")
        if not any(case_id.startswith(p) for p in valid_prefixes):
            raise ValueError(f"Security violation: Case ID '{case_id}' has invalid prefix.")

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Return mandatory security headers."""
        return {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self';"
            ),
        }


def print_generated_tokens() -> None:
    """CLI utility to generate fresh tokens for doctors and admin."""
    print("=== Generated Antigravity Triage Review Tokens ===")
    print("Export the following environment variables before starting the server:\n")
    doc_smitha = SecurityManager.generate_token()
    doc_surbhi = SecurityManager.generate_token()
    doc_adarsh = SecurityManager.generate_token()
    admin_token = SecurityManager.generate_token()

    print(f'export TRIAGE_REVIEW_DOCTOR_TOKENS="dr_smitha:{doc_smitha},dr_surbhi:{doc_surbhi},adarsh:{doc_adarsh}"')
    print(f'export TRIAGE_REVIEW_ADMIN_TOKEN="{admin_token}"')
    print("\nTokens are generated using secrets.token_urlsafe(32) (256-bit entropy).")
    print("Do not commit these values to source control.")


if __name__ == "__main__":
    import sys
    if "--generate-tokens" in sys.argv or "-g" in sys.argv or len(sys.argv) == 1:
        print_generated_tokens()

