"""Oracle system — reality is the final voter.

Oracle types:
- SimulationOracle: Model-based verification using scenario parameters
- (Future) EmpiricalOracle: Real-world data from APIs
- (Future) HybridOracle: Combined simulation + empirical
- (Future) NegativeOracle: Falsification-focused

Oracles are independent: they don't know who submitted claims or their trust.
Multiple oracles compose with max(error) constraint.
"""

from abc import ABC, abstractmethod
from arena.logos.types import Claim, Resolution, Outcome


class Oracle(ABC):
    """Abstract oracle interface. Oracles provide ground truth for claim resolution."""

    @abstractmethod
    def resolve(self, claim: Claim, scenario_params: dict) -> Resolution:
        """Evaluate a claim against reality. Returns a Resolution."""
        ...


class SimulationOracle(Oracle):
    """Resolves claims by checking them against scenario parameters.

    Evaluates whether the claim's proposition accounts for the variables
    in the scenario. Claims that ignore critical variables (omissions)
    get penalized. Claims with high confidence but narrow variable coverage
    get marked as partially valid or invalid.
    """

    def resolve(self, claim: Claim, scenario_params: dict) -> Resolution:
        """Simulate resolution based on scenario data.

        Logic:
        1. Check how many scenario variables the claim accounts for
        2. Check for omissions (variables the claim ignores)
        3. High confidence + omissions = invalid (the Arena's core mechanic)
        4. Modest confidence + good coverage = valid
        """
        # Extract scenario metadata
        parameters = scenario_params.get("parameters", {})
        agents_data = scenario_params.get("agents", {})
        resolution_criteria = scenario_params.get("resolution_criteria", {})

        # Find the agent data matching this claim
        claim_agent_data = None
        for agent_key, agent_data in agents_data.items():
            agent_claim = agent_data.get("claim", agent_data.get("counter_claim", ""))
            if agent_claim == claim.proposition:
                claim_agent_data = agent_data
                break

        if claim_agent_data is None:
            # Can't match claim to scenario agent — resolve as pending
            return Resolution(
                claim_id=claim.id,
                outcome=Outcome.PENDING,
                error_margin=0.5,
            )

        # Count variables the claim considers vs total scenario variables
        claim_variables = set(claim_agent_data.get("variables", []))
        all_variables = set()
        for agent_data in agents_data.values():
            all_variables.update(agent_data.get("variables", []))

        omissions = claim_agent_data.get("omissions", [])

        # Coverage: what fraction of all known variables does this agent consider?
        coverage = len(claim_variables) / max(len(all_variables), 1)

        # Penalty for known omissions
        omission_penalty = len(omissions) * 0.15

        # Check for irreversibility (circularity = 0 means irreversible)
        circularity = parameters.get("material_circularity", 1.0)
        if isinstance(circularity, str):
            try:
                circularity = float(circularity)
            except ValueError:
                circularity = 1.0

        irreversibility_penalty = (1.0 - circularity) * 0.2

        # Total error: combination of missing coverage, omissions, and irreversibility
        error = min(1.0, (1.0 - coverage) * 0.4 + omission_penalty + irreversibility_penalty)

        # Determine outcome
        confidence_error_gap = claim.confidence - (1.0 - error)

        if confidence_error_gap > 0.3:
            # Massively overconfident given the evidence
            outcome = Outcome.INVALID
        elif confidence_error_gap > 0.1:
            outcome = Outcome.PARTIALLY_VALID
        elif error < 0.2:
            outcome = Outcome.VALID
        else:
            outcome = Outcome.PARTIALLY_VALID

        return Resolution(
            claim_id=claim.id,
            outcome=outcome,
            error_margin=round(error, 3),
        )


class CompositeOracle(Oracle):
    """Composes multiple oracles. Error = max(individual errors)."""

    def __init__(self, oracles: list[Oracle]):
        self.oracles = oracles

    def resolve(self, claim: Claim, scenario_params: dict) -> Resolution:
        if not self.oracles:
            return Resolution(claim_id=claim.id, outcome=Outcome.PENDING, error_margin=1.0)

        resolutions = [oracle.resolve(claim, scenario_params) for oracle in self.oracles]

        # Composite error = max of all oracle errors
        max_error = max(r.error_margin for r in resolutions)

        # Outcome = worst case across oracles
        priority = {Outcome.INVALID: 0, Outcome.PARTIALLY_VALID: 1, Outcome.VALID: 2, Outcome.PENDING: 3}
        worst_outcome = min(resolutions, key=lambda r: priority.get(r.outcome, 3)).outcome

        return Resolution(
            claim_id=claim.id,
            outcome=worst_outcome,
            error_margin=max_error,
        )
