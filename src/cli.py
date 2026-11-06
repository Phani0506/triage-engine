"""Command line interface for the Women's Health Triage Engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .engine import TriageEngine
from .loader import load_rules, load_schema


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic Women's Health Clinical Risk Triage Engine CLI (v0.1 Foundation)"
    )
    parser.add_argument(
        "payload_arg",
        nargs="?",
        type=str,
        help="Optional positional path to input file or inline JSON string.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Path to JSON or YAML file containing patient input payload.",
    )
    parser.add_argument(
        "--json-string",
        "-s",
        type=str,
        help="Raw JSON string containing patient input payload.",
    )
    parser.add_argument(
        "--enable-candidate-rules",
        action="store_true",
        default=False,
        help="Enable inactive candidate gap rules (RF-009, EP-001) pending DEC-08 approval.",
    )
    parser.add_argument(
        "--rf006-policy",
        choices=["clinic_visit", "emergency", "unresolved"],
        default="unresolved",
        help="Policy configuration for RF-006 (DEC-03). Defaults to unresolved pending doctor decision.",
    )
    parser.add_argument(
        "--rf005-policy",
        choices=["single_marker_emergency", "combination_required", "unresolved"],
        default="unresolved",
        help="Policy configuration for RF-005 (DEC-02). Defaults to unresolved pending doctor decision.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Optional path to write output JSON result.",
    )

    args = parser.parse_args()

    payload: Dict[str, Any] = {}
    if args.payload_arg:
        arg_val = args.payload_arg.strip()
        if arg_val.startswith("{"):
            try:
                payload = json.loads(arg_val)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON argument: {e}", file=sys.stderr)
                return 1
        else:
            in_path = Path(arg_val)
            if not in_path.exists():
                print(f"Error: Input file {arg_val} does not exist.", file=sys.stderr)
                return 1
            with open(in_path, "r", encoding="utf-8") as f:
                if in_path.suffix in [".yaml", ".yml"]:
                    import yaml
                    payload = yaml.safe_load(f) or {}
                else:
                    payload = json.load(f)
    elif args.input:
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"Error: Input file {args.input} does not exist.", file=sys.stderr)
            return 1
        with open(in_path, "r", encoding="utf-8") as f:
            if in_path.suffix in [".yaml", ".yml"]:
                import yaml
                payload = yaml.safe_load(f) or {}
            else:
                payload = json.load(f)
    elif args.json_string:
        try:
            payload = json.loads(args.json_string)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON string: {e}", file=sys.stderr)
            return 1
    else:
        # Read from stdin if available
        if not sys.stdin.isatty():
            try:
                payload = json.load(sys.stdin)
            except Exception as e:
                print(f"Error reading stdin: {e}", file=sys.stderr)
                return 1
        else:
            parser.print_help()
            return 0

    rf006_pol = None if args.rf006_policy == "unresolved" else args.rf006_policy
    rf005_pol = None if args.rf005_policy == "unresolved" else args.rf005_policy

    engine = TriageEngine(
        candidate_rules_enabled=args.enable_candidate_rules,
        rf006_policy=rf006_pol,
        rf005_policy=rf005_pol,
    )

    result = engine.evaluate(payload)
    result_dict = result.to_dict()
    output_json = json.dumps(result_dict, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Wrote triage result to {args.output}")
    else:
        print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())

