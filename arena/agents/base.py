"""Abstract agent interface for AI Arena.

Agents are participants in the Arena. They:
1. Propose claims based on scenario data
2. Attack other agents' claims
3. Defend their own claims via refinements
4. May abstain when uncertain

The interface is designed to be backend-agnostic:
- Rule-based agents use heuristics
- LLM agents use language model calls
- Both implement the same interface
"""

from abc import ABC, abstractmethod
from typing import Optional

from arena.logos.types import Claim, Attack, Refine, Abstain, AttackType
from arena.trust import TrustState


class Agent(ABC):
    """Abstract agent in the Arena."""

    def __init__(self, name: str, is_hsp: bool = False):
        self.name = name
        self.is_hsp = is_hsp
        self.trust = TrustState()

    @abstractmethod
    def propose_claim(self, scenario: dict) -> Optional[Claim]:
        """Given a scenario, propose a claim or return None to abstain.

        The agent examines the scenario data and formulates a falsifiable
        prediction with bounded scope and confidence.
        """
        ...

    @abstractmethod
    def propose_attacks(self, claims: list[Claim], scenario: dict) -> list[Attack]:
        """Given other agents' claims, propose attacks on weak points.

        Returns a list of attacks (limited by attack budget).
        """
        ...

    @abstractmethod
    def defend(self, claim: Claim, attacks: list[Attack], scenario: dict) -> Optional[Refine]:
        """Given attacks on own claim, optionally refine.

        May return a Refine (costly concession) or None (stand firm).
        Costly concessions increase trust.
        """
        ...

    @abstractmethod
    def decide_abstain(self, scenario: dict) -> Optional[Abstain]:
        """Decide whether to abstain from this round.

        Returns Abstain if uncertain, None to participate.
        Honest abstention increases trust.
        """
        ...

    def __repr__(self):
        role = "HSP" if self.is_hsp else "Linear"
        return f"Agent({self.name}, {role}, trust={self.trust.score:.3f})"
