"""Three-valued logic condition and predicate evaluator (TRUE, FALSE, UNKNOWN)."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from .models import TriState


class ConditionEvaluator:
    """Evaluates rule conditions against patient context using 3-valued logic."""

    @classmethod
    def evaluate(
        cls, condition: Dict[str, Any], context: Dict[str, Any]
    ) -> Tuple[TriState, Set[str]]:
        """
        Evaluates a condition block against context.
        Returns:
            Tuple of (TriState, Set of missing field names).
        """
        missing_fields: Set[str] = set()

        if not condition:
            return TriState.TRUE, missing_fields

        # Check combinators
        if "all" in condition:
            return cls._eval_all(condition["all"], context)

        if "any" in condition:
            return cls._eval_any(condition["any"], context)

        if "count_at_least" in condition:
            k = condition["count_at_least"]
            of_list = condition.get("of", [])
            return cls._eval_count_at_least(k, of_list, context)

        # Single atomic predicate
        if "field" in condition:
            return cls._eval_atomic(condition, context)

        return TriState.UNKNOWN, missing_fields

    @classmethod
    def _eval_all(
        cls, sub_conditions: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Tuple[TriState, Set[str]]:
        has_unknown = False
        all_missing: Set[str] = set()

        for sub in sub_conditions:
            res, missing = cls.evaluate(sub, context)
            if res == TriState.FALSE:
                # Definite failure overrides any unknown
                return TriState.FALSE, set()
            if res == TriState.UNKNOWN:
                has_unknown = True
                all_missing.update(missing)

        if has_unknown:
            return TriState.UNKNOWN, all_missing
        return TriState.TRUE, set()

    @classmethod
    def _eval_any(
        cls, sub_conditions: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Tuple[TriState, Set[str]]:
        has_unknown = False
        all_missing: Set[str] = set()

        for sub in sub_conditions:
            res, missing = cls.evaluate(sub, context)
            if res == TriState.TRUE:
                # Definite truth overrides any unknown
                return TriState.TRUE, set()
            if res == TriState.UNKNOWN:
                has_unknown = True
                all_missing.update(missing)

        if has_unknown:
            return TriState.UNKNOWN, all_missing
        return TriState.FALSE, set()

    @classmethod
    def _eval_count_at_least(
        cls, k: int, of_list: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Tuple[TriState, Set[str]]:
        true_count = 0
        unknown_count = 0
        missing_accum: Set[str] = set()

        for sub in of_list:
            res, missing = cls.evaluate(sub, context)
            if res == TriState.TRUE:
                true_count += 1
            elif res == TriState.UNKNOWN:
                unknown_count += 1
                missing_accum.update(missing)

        if true_count >= k:
            return TriState.TRUE, set()
        if (true_count + unknown_count) < k:
            return TriState.FALSE, set()

        return TriState.UNKNOWN, missing_accum

    @classmethod
    def _eval_atomic(
        cls, pred: Dict[str, Any], context: Dict[str, Any]
    ) -> Tuple[TriState, Set[str]]:
        field_name = pred["field"]
        op = pred.get("op", "==")
        target = pred.get("value")

        actual = context.get(field_name, "unknown")

        # Explicit check for unknown
        if actual == "unknown" or actual is None:
            if op == "==" and target == "unknown":
                return TriState.TRUE, set()
            if op == "!=" and target == "unknown":
                return TriState.FALSE, set()
            if op == "in" and isinstance(target, list) and "unknown" in target:
                return TriState.TRUE, set()
            if op == "not_in" and isinstance(target, list) and "unknown" in target:
                return TriState.FALSE, set()
            # For clinical comparisons against known targets, missing means UNKNOWN
            return TriState.UNKNOWN, {field_name}

        # Value is known
        try:
            if op == "==":
                matched = (actual == target)
            elif op == "!=":
                matched = (actual != target)
            elif op == ">":
                matched = (float(actual) > float(target))
            elif op == ">=":
                matched = (float(actual) >= float(target))
            elif op == "<":
                matched = (float(actual) < float(target))
            elif op == "<=":
                matched = (float(actual) <= float(target))
            elif op == "in":
                matched = (actual in target)
            elif op == "not_in":
                matched = (actual not in target)
            else:
                return TriState.UNKNOWN, {field_name}

            return (TriState.TRUE if matched else TriState.FALSE), set()
        except (ValueError, TypeError):
            return TriState.UNKNOWN, {field_name}

