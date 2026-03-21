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

    With memory: Linear agents slowly learn to lower confidence after
    repeated failures, but they resist concessions and rarely adapt
    their fundamental approach.
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

        # Memory-driven adaptation: slowly lower confidence after failures
        # Linear agents are stubborn — they adjust less than HSP agents
        adjustment = self.trust.suggested_confidence_adjustment() * 0.5  # Half the suggested
        confidence = max(0.1, min(1.0, confidence + adjustment))

        # Build assumptions, incorporating lessons from past attacks
        assumptions = [f"stable_{v}" for v in variables[:2]]
        failed_attacks = self.trust.get_failed_attacks()
        if failed_attacks:
            # Linear agents grudgingly acknowledge ONE past criticism
            assumptions.append(f"noted_{failed_attacks[-1][:30]}")

        claim = Claim(
            proposition=proposition,
            scope=scope,
            confidence=confidence,
            assumptions=assumptions,
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

            # Memory: if we've seen similar claims fail before, attack on data quality
            if self.trust.has_failed_similar(claim.proposition):
                attacks.append(Attack(
                    target_claim_id=claim.id,
                    attack_type=AttackType.DATA_QUALITY,
                    argument=f"Similar claims have previously been invalidated in this arena",
                    confidence=0.55,
                    agent_name=self.name,
                ))

        return attacks

    def defend(self, claim: Claim, attacks: list[Attack], scenario: dict) -> Optional[Refine]:
        if not attacks:
            return None

        strongest_attack = max(attacks, key=lambda a: a.confidence)

        # Memory-driven: concede more readily after repeated losses
        concession_threshold = 0.7
        concession_size = -0.05  # Minimal by default

        if self.trust.loss_count > 2:
            # After 2+ losses, start conceding at lower thresholds
            concession_threshold = 0.5
            concession_size = -0.08
        elif self.trust.loss_count > 0:
            concession_size = -0.06

        if strongest_attack.confidence > concession_threshold:
            return Refine(
                target_claim_id=claim.id,
                modification=f"Narrow scope to account for {strongest_attack.argument}",
                confidence_delta=concession_size,
                agent_name=self.name,
            )
        return None

    def decide_abstain(self, scenario: dict) -> Optional[Abstain]:
        # Memory-driven: after many losses, even Linear agents learn caution
        if self.trust.loss_count >= 3 and self.trust.score < 0.3:
            return Abstain(
                reason="Track record suggests insufficient model coverage — reducing exposure",
                agent_name=self.name,
            )
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

    With memory: HSP agents actively incorporate past attack arguments
    into new claims, lower confidence proactively after partial failures,
    and sharpen attacks based on what worked before.
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

        # Memory-driven adaptation: HSP agents fully incorporate lessons
        adjustment = self.trust.suggested_confidence_adjustment()
        confidence = max(0.1, min(1.0, confidence + adjustment))

        # HSP agents explicitly state what they're watching
        assumptions = [f"monitoring_{v}" for v in variables]

        # Memory: incorporate lessons from past attacks into assumptions
        failed_attacks = self.trust.get_failed_attacks()
        for attack_arg in failed_attacks[-3:]:  # Learn from up to 3 recent attacks
            short_lesson = attack_arg[:40].strip()
            assumptions.append(f"learned: {short_lesson}")

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

                # Memory: increase confidence on attack types that succeeded before
                attack_confidence = 0.75
                if self.trust.win_count > 0:
                    attack_confidence = min(0.90, 0.75 + 0.03 * self.trust.win_count)

                attacks.append(Attack(
                    target_claim_id=claim.id,
                    attack_type=attack_type,
                    argument=f"Claim ignores {omission} — a shadow variable with systemic impact",
                    confidence=attack_confidence,
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

            # Memory: if we've seen similar claims fail, attack with historical evidence
            if self.trust.memory:
                for entry in self.trust.memory:
                    if entry.outcome == "valid":
                        # Our past claims were validated — use them as counterexamples
                        prop_words = set(claim.proposition.lower().split())
                        past_words = set(entry.proposition.lower().split())
                        if len(prop_words & past_words) > 2:
                            attacks.append(Attack(
                                target_claim_id=claim.id,
                                attack_type=AttackType.HISTORICAL_COUNTEREXAMPLE,
                                argument=f"Prior validated analysis contradicts this claim's assumptions",
                                confidence=0.70,
                                agent_name=self.name,
                            ))
                            break  # One historical attack per claim

        return attacks

    def defend(self, claim: Claim, attacks: list[Attack], scenario: dict) -> Optional[Refine]:
        if not attacks:
            return None

        # HSP agents concede readily — this is their strength
        strongest_attack = max(attacks, key=lambda a: a.confidence)

        # Memory-driven: concede even more generously if we have losses
        base_concession = -0.12
        if self.trust.loss_count > 0:
            base_concession = -0.15  # More generous after failures

        if strongest_attack.confidence > 0.5:
            return Refine(
                target_claim_id=claim.id,
                modification=f"Incorporate {strongest_attack.argument} into model",
                confidence_delta=base_concession,
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

        # Memory: abstain if average error is too high (we're consistently wrong)
        if len(self.trust.memory) >= 3 and self.trust.avg_error > 0.4:
            return Abstain(
                reason=f"Average error rate {self.trust.avg_error:.2f} too high — recalibrating model",
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
