"""Demo: run synthetic cases through the biological_mismatch regime audit.

Each case is a (subject, behavior, environment, proposed_diagnosis) tuple.
The audit returns whether the behavior is adaptive somewhere, whether the
current environment is that somewhere, and whether the proposed diagnosis
matches a known misdiagnosis pattern for the regime mismatch.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from biological_mismatch import regime_audit_prompt  # noqa: E402


CASES = [
    {
        "subject": "adult man",
        "behavior": ("frustration with paperwork, slow text processing, "
                     "appears stupid on standardized tests despite high capability"),
        "environment": "text-heavy bureaucratic office work, credential-gated career",
        "proposed_diagnosis": "low intelligence, learning disabled",
    },
    {
        "subject": "Indigenous adolescent",
        "behavior": ("questioning authority directives, coalition-building with peers, "
                     "slow compliance with unilateral orders"),
        "environment": "corporate top-down hierarchy of mandatory schooling",
        "proposed_diagnosis": "oppositional defiant disorder, rebellious",
    },
    {
        "subject": "long-haul truck driver",
        "behavior": ("high baseline energy, continuous engagement preference, "
                     "stress regulation through motion"),
        "environment": "long-haul physical work, multi-domain problem solving",
        "proposed_diagnosis": "",
    },
    {
        "subject": "young father",
        "behavior": ("preferring time with children to status competition, "
                     "low motivation for status-display work"),
        "environment": "corporate masculinity frames, status-via-economic-dominance culture",
        "proposed_diagnosis": "lacking ambition, depression",
    },
]


def _print_case(case: dict) -> None:
    print("=" * 70)
    print(f"SUBJECT: {case['subject']}")
    print(f"BEHAVIOR: {case['behavior']}")
    print(f"ENVIRONMENT: {case['environment']}")
    if case["proposed_diagnosis"]:
        print(f"PROPOSED DIAGNOSIS: {case['proposed_diagnosis']}")
    print("-" * 70)
    result = regime_audit_prompt(
        case["subject"], case["behavior"],
        case["environment"], case["proposed_diagnosis"],
    )
    rc = result["regime_check"]
    print(f"matching regimes:   {rc['matching_regimes']}")
    print(f"adaptive somewhere? {rc['is_adaptive_somewhere']}")
    print(f"adaptive HERE?      {rc['is_adaptive_in_current_environment']}")
    if rc["likely_misdiagnoses"]:
        print(f"likely misdiagnoses: {rc['likely_misdiagnoses']}")
    print(f"actual constraint:  {rc['actual_constraint']}")
    print(f"VERDICT: {result['verdict']}")
    print()


if __name__ == "__main__":
    for case in CASES:
        _print_case(case)
