"""LOGOS validator — enforces the type system.

Validates that LOGOS statements conform to the grammar:
- Propositions must be falsifiable (contain causal relationship)
- Confidence must be in (0, 1]
- Scope must be non-empty and time-bounded
- Attack types must be from the enum
- Refinements must change confidence (no ego-preserving clarifications)
- Trust-weighted parsing: low-trust agents face stricter rules
"""

from arena.logos.types import Claim, Attack, Refine, Abstain, AttackType


class ValidationError(Exception):
    """Raised when a LOGOS statement fails validation."""
    pass


# Causal indicators that suggest a proposition is falsifiable
CAUSAL_INDICATORS = [
    "->", "→", "↑", "↓", "if", "then", "causes", "leads to",
    "increases", "decreases", "reduces", "improves", "worsens",
    "results in", "prevents", "enables", "blocks",
]


def validate_claim(claim: Claim, agent_trust: float = 0.5) -> list[str]:
    """Validate a claim against LOGOS type rules.

    Returns list of validation errors (empty = valid).
    Trust-weighted: low-trust agents face stricter rules.
    """
    errors = []

    # Confidence must be in (0, 1]
    if claim.confidence <= 0 or claim.confidence > 1:
        errors.append(f"Confidence {claim.confidence} must be in (0, 1]")

    # Proposition must not be empty
    if not claim.proposition or not claim.proposition.strip():
        errors.append("Proposition cannot be empty")

    # Proposition should be falsifiable (contain causal relationship)
    prop_lower = claim.proposition.lower()
    has_causal = any(ind in prop_lower for ind in CAUSAL_INDICATORS)
    if not has_causal:
        errors.append(
            f"Proposition may not be falsifiable — no causal indicator found. "
            f"Use causal language (e.g., 'A → B', 'if X then Y')"
        )

    # Scope must be non-empty
    if not claim.scope:
        errors.append("Scope must be non-empty and time-bounded")

    # Trust-weighted constraints
    if agent_trust < 0.3:
        # Low-trust agents: narrower scope, higher evidence bar
        if claim.confidence > 0.7:
            errors.append(
                f"Low-trust agent (trust={agent_trust:.2f}) cannot make "
                f"high-confidence claims (confidence={claim.confidence}). Max: 0.7"
            )
        if len(claim.scope) > 2:
            errors.append(
                f"Low-trust agent (trust={agent_trust:.2f}) limited to "
                f"scope of 2 periods. Got: {len(claim.scope)}"
            )
        if not claim.assumptions:
            errors.append(
                "Low-trust agents must explicitly state assumptions"
            )

    return errors


def validate_attack(attack: Attack, agent_trust: float = 0.5) -> list[str]:
    """Validate an attack against LOGOS type rules."""
    errors = []

    # Attack type must be valid enum
    if not isinstance(attack.attack_type, AttackType):
        errors.append(
            f"Invalid attack type: {attack.attack_type}. "
            f"Must be one of: {[t.value for t in AttackType]}"
        )

    # Confidence must be in (0, 1]
    if attack.confidence <= 0 or attack.confidence > 1:
        errors.append(f"Confidence {attack.confidence} must be in (0, 1]")

    # Argument must not be empty
    if not attack.argument or not attack.argument.strip():
        errors.append("Attack argument cannot be empty")

    # Target must exist
    if not attack.target_claim_id:
        errors.append("Attack must target a specific claim")

    return errors


def validate_refine(refine: Refine, original_confidence: float = None) -> list[str]:
    """Validate a refinement against LOGOS type rules.

    Refinements MUST change confidence. No ego-preserving clarifications.
    """
    errors = []

    # Confidence delta must not be zero
    if refine.confidence_delta == 0:
        errors.append(
            "Refinement must change confidence (confidence_delta cannot be 0). "
            "No ego-preserving clarifications allowed."
        )

    # Modification must not be empty
    if not refine.modification or not refine.modification.strip():
        errors.append("Refinement modification cannot be empty")

    # If we know original confidence, check resulting confidence stays in bounds
    if original_confidence is not None:
        new_confidence = original_confidence + refine.confidence_delta
        if new_confidence <= 0 or new_confidence > 1:
            errors.append(
                f"Resulting confidence {new_confidence:.2f} "
                f"(original {original_confidence} + delta {refine.confidence_delta}) "
                f"must be in (0, 1]"
            )

    return errors


def validate_abstain(abstain: Abstain) -> list[str]:
    """Validate an abstention."""
    errors = []

    if not abstain.reason or not abstain.reason.strip():
        errors.append("Abstention must include a reason")

    return errors
