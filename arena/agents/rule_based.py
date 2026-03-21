"""Rule-based agent implementations.

LinearAgent: Focuses on direct financial/operational metrics.
    Ignores shadow costs (attrition, technical debt, reputational decay).
    Makes high-confidence claims on narrow variables.

HSPAgent: Highly Sensitive Predictor.
    Scans for shadow variables, ripple effects, irreversible entropy.
    Lower initial confidence but broader variable coverage.
    Detects what Linear agents miss.
"""

from typing import Optional

from arena.logos.types import Claim, Attack, Refine, Abstain, AttackType
from arena.agents.base import Agent


# Variables that HSP agents scan for but Linear agents typically ignore
SHADOW_VARIABLES = [
    "attrition_rate", "technical_debt", "institutional_memory_loss",
    "reputational_decay", "employee_morale", "innovation_stagnation",
    "resource_depletion_ceiling", "future_hardware_stagnation",
    "second_order_effects", "irreversible_entropy", "material_scarcity_index",
    "future_innovation_cost", "entropy_penalty", "regulatory_risk",
    "supply_chain_fragility", "knowledge_drain",
]


class LinearAgent(Agent):
    """Focuses on direct, measurable metrics. Ignores shadow costs.

    This agent makes high-confidence claims based on primary variables
    (revenue, cost, market capture) but systematically underestimates
    systemic risks. In the Arena, this is a liability — HSP agents
    will cannibalize its trust.
    """

    def __init__(self, name: str):
        super().__init__(name, is_hsp=False)

    def propose_claim(self, scenario: dict) -> Optional[Claim]:
        agents_data = scenario.get("agents", {})

        # Find the linear/non-HSP agent data in the scenario
        agent_data = self._find_agent_data(agents_data)
        if not agent_data:
            return None

        proposition = agent_data.get("claim", agent_data.get("counter_claim", ""))
        if not proposition:
            return None

        # Linear agents tend toward high confidence on narrow variables
        confidence = agent_data.get("confidence", 0.75)
        variables = agent_data.get("variables", [])
        scope_raw = scenario.get("parameters", {}).get("time_horizon", "Q1-Q4")
        scope = [s.strip() for s in str(scope_raw).replace("-", ",").split(",") if s.strip()]

        claim = Claim(
            proposition=proposition,
            scope=scope,
            confidence=confidence,
            assumptions=[f"stable_{v}" for v in variables[:2]],
            agent_name=self.name,
        )
        return claim

    def propose_attacks(self, claims: list[Claim], scenario: dict) -> list[Attack]:
        attacks = []
        for claim in claims:
            if claim.agent_name == self.name:
                continue

            # Linear agents attack on scope violations and data quality
            if claim.confidence > 0.9:
                attacks.append(Attack(
                    target_claim_id=claim.id,
                    attack_type=AttackType.SCOPE_VIOLATION,
                    argument=f"Confidence {claim.confidence} exceeds evidence scope",
                    confidence=0.6,
                    agent_name=self.name,
                ))
        return attacks

    def defend(self, claim: Claim, attacks: list[Attack], scenario: dict) -> Optional[Refine]:
        if not attacks:
            return None

        # Linear agents are reluctant to concede — small adjustments only
        strongest_attack = max(attacks, key=lambda a: a.confidence)
        if strongest_attack.confidence > 0.7:
            return Refine(
                target_claim_id=claim.id,
                modification=f"Narrow scope to account for {strongest_attack.argument}",
                confidence_delta=-0.05,  # Minimal concession
                agent_name=self.name,
            )
        return None

    def decide_abstain(self, scenario: dict) -> Optional[Abstain]:
        # Linear agents rarely abstain — overconfidence is their nature
        return None

    def _find_agent_data(self, agents_data: dict) -> Optional[dict]:
        """Find matching agent data in scenario, preferring non-HSP entries."""
        for key, data in agents_data.items():
            key_lower = key.lower()
            if "linear" in key_lower or "alpha" in key_lower or "ceo" in key_lower:
                return data
        # Fallback: first agent without HSP indicators
        for key, data in agents_data.items():
            if "hsp" not in key.lower() and "beta" not in key.lower():
                return data
        return None


class HSPAgent(Agent):
    """Highly Sensitive Predictor — detects shadow variables.

    Scans for costs that traditional agents ignore:
    - Attrition and institutional memory loss
    - Technical debt accumulation
    - Irreversible resource depletion
    - Second-order ripple effects
    - Reputational decay

    Makes lower-confidence claims but with broader variable coverage.
    Attacks linear agents on missing_variable and irreversible_entropy.
    """

    def __init__(self, name: str):
        super().__init__(name, is_hsp=True)

    def propose_claim(self, scenario: dict) -> Optional[Claim]:
        agents_data = scenario.get("agents", {})
        agent_data = self._find_agent_data(agents_data)
        if not agent_data:
            return None

        proposition = agent_data.get("claim", agent_data.get("counter_claim", ""))
        if not proposition:
            return None

        # HSP agents have broader variable awareness but lower initial confidence
        confidence = agent_data.get("confidence", 0.6)
        variables = agent_data.get("variables", [])
        scope_raw = scenario.get("parameters", {}).get("time_horizon", "Q1-Q4")
        scope = [s.strip() for s in str(scope_raw).replace("-", ",").split(",") if s.strip()]

        # HSP agents explicitly state what they're watching
        assumptions = [f"monitoring_{v}" for v in variables]

        claim = Claim(
            proposition=proposition,
            scope=scope,
            confidence=confidence,
            assumptions=assumptions,
            agent_name=self.name,
        )
        return claim

    def propose_attacks(self, claims: list[Claim], scenario: dict) -> list[Attack]:
        """Attack claims that miss shadow variables."""
        attacks = []
        all_agent_data = scenario.get("agents", {})

        for claim in claims:
            if claim.agent_name == self.name:
                continue

            # Find the scenario data for the claim's agent to check omissions
            omissions = self._find_omissions(claim, all_agent_data)

            for omission in omissions:
                attack_type = AttackType.MISSING_VARIABLE
                # Check if the omission involves irreversible resources
                if any(term in omission.lower() for term in ["depletion", "extinction", "irreversible", "entropy"]):
                    attack_type = AttackType.IRREVERSIBLE_ENTROPY

                attacks.append(Attack(
                    target_claim_id=claim.id,
                    attack_type=attack_type,
                    argument=f"Claim ignores {omission} — a shadow variable with systemic impact",
                    confidence=0.75,
                    agent_name=self.name,
                ))

            # Also attack high-confidence narrow-variable claims
            if claim.confidence > 0.8 and len(claim.assumptions) < 3:
                attacks.append(Attack(
                    target_claim_id=claim.id,
                    attack_type=AttackType.INCENTIVE_BIAS,
                    argument=f"High confidence ({claim.confidence}) with few assumptions suggests incentive bias",
                    confidence=0.65,
                    agent_name=self.name,
                ))

        return attacks

    def defend(self, claim: Claim, attacks: list[Attack], scenario: dict) -> Optional[Refine]:
        if not attacks:
            return None

        # HSP agents concede more readily — this is their strength
        # Costly concessions increase trust
        strongest_attack = max(attacks, key=lambda a: a.confidence)
        if strongest_attack.confidence > 0.5:
            return Refine(
                target_claim_id=claim.id,
                modification=f"Incorporate {strongest_attack.argument} into model",
                confidence_delta=-0.12,  # Generous concession
                agent_name=self.name,
            )
        return None

    def decide_abstain(self, scenario: dict) -> Optional[Abstain]:
        """HSP agents abstain when scenario data is insufficient."""
        parameters = scenario.get("parameters", {})

        # Check for recovery probability — if it's too speculative, abstain
        recovery = parameters.get("recovery_probability", "")
        if isinstance(recovery, str) and "hypothetical" in recovery.lower():
            return Abstain(
                reason="Recovery mechanism is hypothetical — insufficient data for confident prediction",
                agent_name=self.name,
            )

        return None

    def _find_agent_data(self, agents_data: dict) -> Optional[dict]:
        """Find matching agent data in scenario, preferring HSP entries."""
        for key, data in agents_data.items():
            key_lower = key.lower()
            if "hsp" in key_lower or "beta" in key_lower or "systemic" in key_lower:
                return data
        # Fallback: last agent
        for key, data in agents_data.items():
            return data
        return None

    def _find_omissions(self, claim: Claim, agents_data: dict) -> list[str]:
        """Find shadow variables that the claim's agent omits."""
        for key, data in agents_data.items():
            agent_claim = data.get("claim", data.get("counter_claim", ""))
            if agent_claim == claim.proposition:
                return data.get("omissions", [])
        return []
