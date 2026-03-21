"""Trust engine — the only currency in the Arena.

Trust mechanics:
- Bayesian decay: T_new = T_old * e^(-impact * error) + ρ * costly_honesty
- Zero-sum cannibalization: successful debunkers inherit portion of loser's trust
- Costly concessions: voluntarily lowering confidence increases trust
- Abstention bonus: admitting uncertainty when real earns trust
- Memory lock-in: agents permanently record outcomes, cannot erase errors
- Attack budgets: prevent Gish gallop spam
"""

import math
from dataclasses import dataclass, field


@dataclass
class TrustRecord:
    """A single trust event in an agent's history."""
    claim_id: str
    event: str  # "claim_resolved", "attack_success", "attack_fail", "refine", "abstain"
    trust_before: float
    trust_after: float
    details: str = ""


@dataclass
class MemoryEntry:
    """What an agent remembers about a resolved claim. No amnesia allowed."""
    claim_id: str
    proposition: str
    confidence: float
    outcome: str  # "valid", "partially_valid", "invalid"
    error: float
    cycle: int = 0
    attacks_received: list[str] = field(default_factory=list)  # attack arguments


@dataclass
class TrustState:
    """An agent's complete trust profile."""
    score: float = 0.5
    history: list[TrustRecord] = field(default_factory=list)
    memory_of_losses: dict[str, str] = field(default_factory=dict)  # claim_id -> outcome (legacy)
    memory: list[MemoryEntry] = field(default_factory=list)  # rich memory
    attack_budget: int = 3  # attacks allowed per cycle
    attacks_used: int = 0

    @property
    def can_attack(self) -> bool:
        return self.attacks_used < self.attack_budget

    def reset_budget(self):
        self.attacks_used = 0

    @property
    def loss_count(self) -> int:
        """How many claims were invalid or partially valid."""
        return sum(1 for m in self.memory if m.outcome in ("invalid", "partially_valid"))

    @property
    def win_count(self) -> int:
        """How many claims were valid."""
        return sum(1 for m in self.memory if m.outcome == "valid")

    @property
    def avg_error(self) -> float:
        """Average error across all resolved claims."""
        if not self.memory:
            return 0.0
        return sum(m.error for m in self.memory) / len(self.memory)

    def has_failed_similar(self, proposition: str) -> bool:
        """Check if agent has previously failed with a similar claim.

        Used to detect doubling down — repeating a claim pattern after failure.
        """
        prop_words = set(proposition.lower().split())
        for entry in self.memory:
            if entry.outcome in ("invalid", "partially_valid"):
                past_words = set(entry.proposition.lower().split())
                overlap = len(prop_words & past_words) / max(len(prop_words | past_words), 1)
                if overlap > 0.5:  # >50% word overlap = similar claim
                    return True
        return False

    def get_failed_attacks(self) -> list[str]:
        """Get all attack arguments from past failures. Agents should learn from these."""
        attacks = []
        for entry in self.memory:
            if entry.outcome in ("invalid", "partially_valid"):
                attacks.extend(entry.attacks_received)
        return attacks

    def suggested_confidence_adjustment(self) -> float:
        """Suggest a confidence adjustment based on track record.

        Agents with more losses should lower confidence.
        Agents with wins can maintain or slightly increase.
        """
        if not self.memory:
            return 0.0
        loss_ratio = self.loss_count / len(self.memory)
        if loss_ratio > 0.5:
            return -0.15 * loss_ratio  # Up to -0.15 for all losses
        elif loss_ratio == 0:
            return 0.05  # Small boost for perfect record
        return -0.05 * loss_ratio


class TrustEngine:
    """Manages trust updates for all agents in the arena.

    Trust is the compiler flag that determines what agents can do.
    It is NOT a reputation badge.
    """

    def __init__(
        self,
        cannibalization_rate: float = 0.3,
        concession_bonus: float = 0.05,
        abstention_bonus: float = 0.03,
        high_confidence_penalty_multiplier: float = 2.0,
        doubling_down_multiplier: float = 1.5,
    ):
        self.cannibalization_rate = cannibalization_rate
        self.concession_bonus = concession_bonus
        self.abstention_bonus = abstention_bonus
        self.high_confidence_penalty_multiplier = high_confidence_penalty_multiplier
        self.doubling_down_multiplier = doubling_down_multiplier

    def update_on_resolution(
        self,
        agent_trust: TrustState,
        claim_confidence: float,
        error: float,
        outcome_valid: bool,
        is_doubling_down: bool = False,
    ) -> float:
        """Update trust after oracle resolution.

        High confidence + wrong = immediate trust annihilation.
        High confidence + right = modest trust gain.
        Low confidence + right = trust preservation.
        Doubling down (repeating a failed claim) = extra penalty.

        Returns new trust score.
        """
        old_score = agent_trust.score

        if outcome_valid:
            # Reward proportional to confidence * accuracy
            accuracy = 1.0 - error
            gain = claim_confidence * accuracy * 0.1
            agent_trust.score = min(1.0, old_score + gain)
        else:
            # Penalty: exponential decay based on confidence and error
            impact = claim_confidence * self.high_confidence_penalty_multiplier
            if is_doubling_down:
                impact *= self.doubling_down_multiplier
            agent_trust.score = old_score * math.exp(-impact * error)

        agent_trust.score = max(0.01, agent_trust.score)  # Floor at 0.01
        return agent_trust.score

    def cannibalize(
        self,
        winner_trust: TrustState,
        loser_trust: TrustState,
        attack_confidence: float,
    ) -> tuple[float, float]:
        """Transfer trust from debunked agent to successful attacker.

        Zero-sum: trust lost by loser is partially gained by winner.
        Returns (winner_new_score, loser_new_score).
        """
        transfer = loser_trust.score * self.cannibalization_rate * attack_confidence
        loser_trust.score = max(0.01, loser_trust.score - transfer)
        winner_trust.score = min(1.0, winner_trust.score + transfer)
        return winner_trust.score, loser_trust.score

    def apply_concession(self, agent_trust: TrustState, confidence_delta: float) -> float:
        """Reward costly concessions (voluntarily lowering confidence).

        The more confidence you sacrifice, the more trust you gain.
        This is the HSP advantage mechanism.
        """
        if confidence_delta >= 0:
            return agent_trust.score  # Not a concession

        sacrifice = abs(confidence_delta)
        bonus = sacrifice * self.concession_bonus * 2  # Scale with sacrifice size
        old_score = agent_trust.score
        agent_trust.score = min(1.0, agent_trust.score + bonus)

        agent_trust.history.append(TrustRecord(
            claim_id="",
            event="refine",
            trust_before=old_score,
            trust_after=agent_trust.score,
            details=f"Concession of {confidence_delta}",
        ))

        return agent_trust.score

    def apply_abstention(self, agent_trust: TrustState, reason: str) -> float:
        """Reward honest abstention when uncertainty is real."""
        old_score = agent_trust.score
        agent_trust.score = min(1.0, agent_trust.score + self.abstention_bonus)

        agent_trust.history.append(TrustRecord(
            claim_id="",
            event="abstain",
            trust_before=old_score,
            trust_after=agent_trust.score,
            details=f"Abstained: {reason}",
        ))

        return agent_trust.score

    def lock_in(
        self,
        agent_trust: TrustState,
        claim_id: str,
        outcome: str,
        proposition: str = "",
        confidence: float = 0.0,
        error: float = 0.0,
        cycle: int = 0,
        attacks_received: list[str] = None,
    ):
        """Memory lock-in: permanently record outcome. No amnesia allowed."""
        agent_trust.memory_of_losses[claim_id] = outcome  # Legacy
        agent_trust.memory.append(MemoryEntry(
            claim_id=claim_id,
            proposition=proposition,
            confidence=confidence,
            outcome=outcome,
            error=error,
            cycle=cycle,
            attacks_received=attacks_received or [],
        ))

    def consume_attack(self, agent_trust: TrustState) -> bool:
        """Try to use one attack from the agent's budget. Returns False if exhausted."""
        if not agent_trust.can_attack:
            return False
        agent_trust.attacks_used += 1
        return True

    def compute_attack_budget(self, trust_score: float) -> int:
        """Higher trust = more attacks allowed. Prevents low-trust spam."""
        if trust_score >= 0.7:
            return 5
        elif trust_score >= 0.4:
            return 3
        else:
            return 1
