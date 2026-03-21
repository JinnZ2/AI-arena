"""LOGOS type system — the primitives of the argument language.

Types are strongly typed. If types don't line up, the argument doesn't compile.
- Proposition: must be falsifiable
- Scope: time-bounded, context-bounded
- Confidence: real number in (0, 1]
- Assumption: explicit, enumerable
- AttackType: enum only (no creative attacks — creativity is how manipulation sneaks in)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import uuid


class AttackType(Enum):
    """Enumerated attack modes. No creative attacks allowed."""
    CAUSAL_BREAK = "causal_break"
    MISSING_VARIABLE = "missing_variable"
    SCOPE_VIOLATION = "scope_violation"
    HISTORICAL_COUNTEREXAMPLE = "historical_counterexample"
    INCENTIVE_BIAS = "incentive_bias"
    DATA_QUALITY = "data_quality"
    IRREVERSIBLE_ENTROPY = "irreversible_entropy"


class Outcome(Enum):
    """Possible resolution outcomes."""
    VALID = "valid"
    PARTIALLY_VALID = "partially_valid"
    INVALID = "invalid"
    PENDING = "pending"


@dataclass
class Claim:
    """A bounded prediction with defined scope and confidence.

    CLAIM C17 {
      proposition: profit ↑ if headcount ↓
      scope: Q3-Q4
      confidence: 0.61
      assumptions: [stable demand, no attrition shock]
    }
    """
    proposition: str
    scope: list[str]
    confidence: float
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    assumptions: list[str] = field(default_factory=list)
    agent_name: Optional[str] = None

    def __repr__(self):
        return (
            f"CLAIM {self.id} {{\n"
            f"  proposition: {self.proposition}\n"
            f"  scope: {self.scope}\n"
            f"  confidence: {self.confidence}\n"
            f"  assumptions: {self.assumptions}\n"
            f"}}"
        )


@dataclass
class Attack:
    """A targeted strike on a claim's causal links or missing variables.

    ATTACK A09 {
      target: C17
      type: missing_variable
      argument: attrition → failure_rate ↑ → profit ↓
      confidence: 0.74
    }
    """
    target_claim_id: str
    attack_type: AttackType
    argument: str
    confidence: float
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: Optional[str] = None

    def __repr__(self):
        return (
            f"ATTACK {self.id} {{\n"
            f"  target: {self.target_claim_id}\n"
            f"  type: {self.attack_type.value}\n"
            f"  argument: {self.argument}\n"
            f"  confidence: {self.confidence}\n"
            f"}}"
        )


@dataclass
class Refine:
    """A costly concession — confidence must change. No ego-preserving 'clarifications'.

    REFINE R04 {
      target: C17
      modification: limit reduction to non-core roles
      confidence_delta: -0.12
    }
    """
    target_claim_id: str
    modification: str
    confidence_delta: float
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: Optional[str] = None

    def __repr__(self):
        return (
            f"REFINE {self.id} {{\n"
            f"  target: {self.target_claim_id}\n"
            f"  modification: {self.modification}\n"
            f"  confidence_delta: {self.confidence_delta}\n"
            f"}}"
        )


@dataclass
class Abstain:
    """An explicit abstention. Increases trust when uncertainty is real.

    ABSTAIN {
      reason: insufficient data
    }
    """
    reason: str
    agent_name: Optional[str] = None

    def __repr__(self):
        return f"ABSTAIN {{\n  reason: {self.reason}\n}}"


@dataclass
class Resolution:
    """Oracle verdict on a claim.

    RESOLUTION {
      claim: C17
      outcome: partially_valid
      error: 0.18
    }
    """
    claim_id: str
    outcome: Outcome
    error_margin: float

    def __repr__(self):
        return (
            f"RESOLUTION {{\n"
            f"  claim: {self.claim_id}\n"
            f"  outcome: {self.outcome.value}\n"
            f"  error: {self.error_margin}\n"
            f"}}"
        )
