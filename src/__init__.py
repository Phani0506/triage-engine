"""
Women's Health Clinical Risk Triage Engine (v0.1 Foundation).

Deterministic, rule-based, evidence-backed clinical triage engine for women aged 18-40.
"""

from typing import Any, Dict

from .engine import TriageEngine
from .models import TriageResult, TriageStatus, UrgencyColour, UrgencyLevel

_default_engine = None


def get_engine() -> TriageEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = TriageEngine()
    return _default_engine


def evaluate_patient(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Public helper API returning standard dictionary JSON contract."""
    engine = get_engine()
    result = engine.evaluate(inputs)
    return result.to_dict()


__all__ = [
    "TriageEngine",
    "TriageResult",
    "TriageStatus",
    "UrgencyLevel",
    "UrgencyColour",
    "evaluate_patient",
    "get_engine",
]

