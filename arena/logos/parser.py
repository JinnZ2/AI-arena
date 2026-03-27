"""LOGOS parser — converts text or dicts into validated LOGOS statements.

Supports two input modes:
1. Dict/structured input (from scenario JSON or agent logic)
2. LOGOS text format (from LLM translation or human input)

All parsed statements are validated before returning.
"""

import re
from typing import Union

from arena.logos.types import (
    Claim, Attack, Refine, Abstain, Resolution,
    AttackType, Outcome,
)
from arena.logos.validator import (
    validate_claim, validate_attack, validate_refine, validate_abstain,
    ValidationError,
)


Statement = Union[Claim, Attack, Refine, Abstain, Resolution]


def parse_statement(text: str, agent_trust: float = 0.5) -> Statement:
    """Parse a LOGOS-format text string into a typed statement.

    Example inputs:
        CLAIM C17 { proposition: profit ↑ if headcount ↓ ... }
        ATTACK A09 { target: C17 type: missing_variable ... }
        REFINE R04 { target: C17 modification: ... confidence_delta: -0.12 }
        ABSTAIN { reason: insufficient data }
        RESOLUTION { claim: C17 outcome: partially_valid error: 0.18 }
    """
    text = text.strip()

    if text.startswith("CLAIM"):
        return _parse_claim(text, agent_trust)
    elif text.startswith("ATTACK"):
        return _parse_attack(text, agent_trust)
    elif text.startswith("REFINE"):
        return _parse_refine(text)
    elif text.startswith("ABSTAIN"):
        return _parse_abstain(text)
    elif text.startswith("RESOLUTION"):
        return _parse_resolution(text)
    else:
        raise ValidationError(f"Unknown statement type. Must start with CLAIM, ATTACK, REFINE, ABSTAIN, or RESOLUTION. Got: {text[:50]}")


def parse_from_dict(data: dict, statement_type: str, agent_trust: float = 0.5) -> Statement:
    """Parse a dict into a LOGOS statement. Used for scenario JSON and agent output."""
    parsers = {
        "claim": _parse_claim_dict,
        "attack": _parse_attack_dict,
        "refine": _parse_refine_dict,
        "abstain": _parse_abstain_dict,
        "resolution": _parse_resolution_dict,
    }
    parser = parsers.get(statement_type.lower())
    if not parser:
        raise ValidationError(f"Unknown statement type: {statement_type}")
    return parser(data, agent_trust)


def _extract_field(text: str, field_name: str) -> str:
    """Extract a field value from LOGOS block text."""
    pattern = rf'{field_name}\s*:\s*(.+?)(?:\n|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_list_field(text: str, field_name: str) -> list[str]:
    """Extract a list field like assumptions: [a, b, c]."""
    raw = _extract_field(text, field_name)
    if not raw:
        return []
    # Strip brackets and split
    raw = raw.strip("[]")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _extract_id(header: str) -> str:
    """Extract ID from statement header like 'CLAIM C17 {'."""
    parts = header.split()
    if len(parts) >= 2:
        return parts[1].strip("{").strip()
    return ""


# --- Text parsers ---

def _parse_claim(text: str, agent_trust: float) -> Claim:
    first_line = text.split("\n")[0] if "\n" in text else text.split("{")[0]
    claim_id = _extract_id(first_line) or None

    proposition = _extract_field(text, "proposition")
    scope_raw = _extract_field(text, "scope")
    scope = [s.strip() for s in scope_raw.replace("-", ",").split(",") if s.strip()] if scope_raw else []
    confidence_raw = _extract_field(text, "confidence")
    assumptions = _extract_list_field(text, "assumptions")

    try:
        confidence = float(confidence_raw) if confidence_raw else 0.5
    except ValueError:
        raise ValidationError(f"Invalid confidence value: {confidence_raw}")

    claim = Claim(
        proposition=proposition,
        scope=scope,
        confidence=confidence,
        assumptions=assumptions,
    )
    if claim_id:
        claim.id = claim_id

    errors = validate_claim(claim, agent_trust)
    if errors:
        raise ValidationError(f"Invalid CLAIM: {'; '.join(errors)}")

    return claim


def _parse_attack(text: str, agent_trust: float) -> Attack:
    first_line = text.split("\n")[0] if "\n" in text else text.split("{")[0]
    attack_id = _extract_id(first_line) or None

    target = _extract_field(text, "target")
    type_raw = _extract_field(text, "type")
    argument = _extract_field(text, "argument")
    confidence_raw = _extract_field(text, "confidence")

    try:
        attack_type = AttackType(type_raw)
    except ValueError:
        raise ValidationError(
            f"Invalid attack type: '{type_raw}'. "
            f"Must be one of: {[t.value for t in AttackType]}"
        )

    try:
        confidence = float(confidence_raw) if confidence_raw else 0.5
    except ValueError:
        raise ValidationError(f"Invalid confidence value: {confidence_raw}")

    attack = Attack(
        target_claim_id=target,
        attack_type=attack_type,
        argument=argument,
        confidence=confidence,
    )
    if attack_id:
        attack.id = attack_id

    errors = validate_attack(attack, agent_trust)
    if errors:
        raise ValidationError(f"Invalid ATTACK: {'; '.join(errors)}")

    return attack


def _parse_refine(text: str) -> Refine:
    first_line = text.split("\n")[0] if "\n" in text else text.split("{")[0]
    refine_id = _extract_id(first_line) or None

    target = _extract_field(text, "target")
    modification = _extract_field(text, "modification")
    delta_raw = _extract_field(text, "confidence_delta")

    try:
        confidence_delta = float(delta_raw) if delta_raw else 0.0
    except ValueError:
        raise ValidationError(f"Invalid confidence_delta value: {delta_raw}")

    refine = Refine(
        target_claim_id=target,
        modification=modification,
        confidence_delta=confidence_delta,
    )
    if refine_id:
        refine.id = refine_id

    errors = validate_refine(refine)
    if errors:
        raise ValidationError(f"Invalid REFINE: {'; '.join(errors)}")

    return refine


def _parse_abstain(text: str) -> Abstain:
    reason = _extract_field(text, "reason")
    abstain = Abstain(reason=reason)

    errors = validate_abstain(abstain)
    if errors:
        raise ValidationError(f"Invalid ABSTAIN: {'; '.join(errors)}")

    return abstain


def _parse_resolution(text: str) -> Resolution:
    claim_id = _extract_field(text, "claim")
    outcome_raw = _extract_field(text, "outcome")
    error_raw = _extract_field(text, "error")

    try:
        outcome = Outcome(outcome_raw)
    except ValueError:
        raise ValidationError(
            f"Invalid outcome: '{outcome_raw}'. "
            f"Must be one of: {[o.value for o in Outcome]}"
        )

    try:
        error_margin = float(error_raw) if error_raw else 0.0
    except ValueError:
        raise ValidationError(f"Invalid error value: {error_raw}")

    return Resolution(claim_id=claim_id, outcome=outcome, error_margin=error_margin)


# --- Dict parsers ---

def _parse_claim_dict(data: dict, agent_trust: float) -> Claim:
    scope = data.get("scope", [])
    if isinstance(scope, str):
        scope = [s.strip() for s in scope.replace("-", ",").split(",") if s.strip()]

    claim = Claim(
        proposition=data.get("proposition", data.get("claim", data.get("counter_claim", ""))),
        scope=scope,
        confidence=float(data.get("confidence", 0.5)),
        assumptions=data.get("assumptions", []),
    )
    if "id" in data:
        claim.id = data["id"]

    errors = validate_claim(claim, agent_trust)
    if errors:
        raise ValidationError(f"Invalid CLAIM: {'; '.join(errors)}")

    return claim


def _parse_attack_dict(data: dict, agent_trust: float) -> Attack:
    try:
        attack_type = AttackType(data.get("type", data.get("attack_type", "")))
    except ValueError as e:
        raise ValidationError(str(e))

    attack = Attack(
        target_claim_id=data.get("target", data.get("target_claim_id", "")),
        attack_type=attack_type,
        argument=data.get("argument", ""),
        confidence=float(data.get("confidence", 0.5)),
    )
    if "id" in data:
        attack.id = data["id"]

    errors = validate_attack(attack, agent_trust)
    if errors:
        raise ValidationError(f"Invalid ATTACK: {'; '.join(errors)}")

    return attack


def _parse_refine_dict(data: dict, _agent_trust: float) -> Refine:
    refine = Refine(
        target_claim_id=data.get("target", data.get("target_claim_id", "")),
        modification=data.get("modification", ""),
        confidence_delta=float(data.get("confidence_delta", 0.0)),
    )
    if "id" in data:
        refine.id = data["id"]

    errors = validate_refine(refine)
    if errors:
        raise ValidationError(f"Invalid REFINE: {'; '.join(errors)}")

    return refine


def _parse_abstain_dict(data: dict, _agent_trust: float) -> Abstain:
    abstain = Abstain(reason=data.get("reason", ""))

    errors = validate_abstain(abstain)
    if errors:
        raise ValidationError(f"Invalid ABSTAIN: {'; '.join(errors)}")

    return abstain


def _parse_resolution_dict(data: dict, _agent_trust: float) -> Resolution:
    try:
        outcome = Outcome(data.get("outcome", "pending"))
    except ValueError as e:
        raise ValidationError(str(e))

    return Resolution(
        claim_id=data.get("claim", data.get("claim_id", "")),
        outcome=outcome,
        error_margin=float(data.get("error", data.get("error_margin", 0.0))),
    )
