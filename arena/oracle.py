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
from arena.thermodynamics import (
    SystemLedger, Domain, build_ledger_from_scenario,
    ImperfectionChecker, EquilibriumChecker,
)


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


class ClosedSystemOracle(Oracle):
    """Resolves claims using thermodynamic accounting.

    First law: margin doesn't come from nothing. Every company gain is
    a cost transfer from workers, community, environment, or infrastructure.

    This oracle:
    1. Builds a SystemLedger from scenario cost_transfer data
    2. Checks if the claim accounts for where costs actually go
    3. Penalizes claims that show gains without showing losses
    4. Penalizes irreversible entropy (destroyed resources, lost knowledge)
    5. Reports the full system accounting in the resolution

    A claim that says "we save $4M" is INVALID if the ledger shows
    $6M in external costs. The margin didn't appear — it was extracted.
    """

    def __init__(self, include_simulation: bool = True):
        self._simulation = SimulationOracle() if include_simulation else None

    def resolve(self, claim: Claim, scenario_params: dict) -> Resolution:
        ledger = build_ledger_from_scenario(scenario_params)

        # If no cost_transfers defined, fall back to simulation oracle
        if not ledger.transfers:
            if self._simulation:
                return self._simulation.resolve(claim, scenario_params)
            return Resolution(claim_id=claim.id, outcome=Outcome.PENDING, error_margin=0.5)

        # Find which agent this claim belongs to
        agents_data = scenario_params.get("agents", {})
        claim_agent_data = None
        claim_agent_key = None
        for agent_key, agent_data in agents_data.items():
            agent_claim = agent_data.get("claim", agent_data.get("counter_claim", ""))
            if agent_claim == claim.proposition:
                claim_agent_data = agent_data
                claim_agent_key = agent_key
                break

        if claim_agent_data is None:
            return Resolution(claim_id=claim.id, outcome=Outcome.PENDING, error_margin=0.5)

        # Parse time horizon for temporal projection
        params = scenario_params.get("parameters", {})
        time_horizon_raw = str(params.get("time_horizon", "12 Months"))
        # Extract months from strings like "18 Months", "Q3-Q4" (6 months), "25 Years"
        horizon_months = _parse_time_horizon(time_horizon_raw)

        # Core thermodynamic analysis (at t=0 for conservation check)
        company_gain = ledger.company_gain
        external_cost = ledger.external_cost
        net_system = ledger.net_system_value
        total_entropy = ledger.total_entropy
        conservation_error = ledger.conservation_error

        # Temporal analysis: project costs to the scenario's time horizon
        company_gain_at_horizon = ledger.company_gain_at(horizon_months)
        external_cost_at_horizon = ledger.external_cost_at(horizon_months)
        net_system_at_horizon = ledger.net_system_value_at(horizon_months)
        entropy_at_horizon = sum(
            e.magnitude_at_month(horizon_months) for e in ledger.entropy_events
        )

        # How much of the real picture does this agent's claim capture?
        claim_variables = set(claim_agent_data.get("variables", []))
        omissions = claim_agent_data.get("omissions", [])

        # Penalty components
        # 1. Conservation violation: agent claims gain without accounting for source
        conservation_penalty = 0.0
        if company_gain > 0 and external_cost > 0:
            # How much of the external cost does this agent acknowledge?
            has_external_vars = any(
                v in str(claim_variables).lower()
                for v in ["attrition", "community", "health", "environment",
                          "entropy", "infrastructure", "morale", "knowledge"]
            )
            if not has_external_vars:
                # Agent claims gain but ignores where it comes from
                conservation_penalty = min(0.4, external_cost / max(company_gain, 1) * 0.2)

        # 2. Entropy penalty: irreversible destruction
        entropy_penalty = min(0.3, total_entropy * 0.5)

        # 3. Omission penalty (same as SimulationOracle)
        omission_penalty = len(omissions) * 0.12

        # 4. Net system value check: if net < 0, the action destroys value system-wide
        net_value_penalty = 0.0
        if net_system < 0:
            # The claim proposes something that destroys net value
            # Penalty scales with how negative the net is
            net_value_penalty = min(0.3, abs(net_system) / max(abs(company_gain), 1) * 0.15)

        # 5. Temporal penalty: the longer the horizon, the worse compounding costs get
        temporal_penalty = 0.0
        if horizon_months > 0 and external_cost_at_horizon > external_cost:
            # Costs are growing over time — the claim ignores compounding damage
            growth_ratio = external_cost_at_horizon / max(external_cost, 1)
            temporal_penalty = min(0.3, (growth_ratio - 1.0) * 0.1)

        # 6. Third Law (Imperfection): no zero-loss, no perfect efficiency
        imperfection_penalty, imperfection_violations = ImperfectionChecker.check_claim(
            claim.confidence, list(claim_variables), omissions
        )

        # 7. Le Chatelier (Equilibrium Resistance): large disturbances create counterforces
        equilibrium_penalty = 0.0
        equilibrium_msg = None
        disturbance = params.get("disturbance_magnitude", 0.0)
        if isinstance(disturbance, str):
            try:
                disturbance = float(disturbance)
            except ValueError:
                disturbance = 0.0
        if disturbance > 0:
            # Check if agent models counterforce variables
            counterforce_vars = {"attrition_rate", "employee_morale", "institutional_memory_loss",
                                 "reputational_decay", "knowledge_drain", "resistance",
                                 "second_order_effects", "counterforce"}
            counterforce_modeled = bool(claim_variables & counterforce_vars)
            rate = float(params.get("rate_of_change", 1.0))
            equilibrium_penalty, equilibrium_msg = EquilibriumChecker.check_claim(
                disturbance, counterforce_modeled, rate
            )

        # Total error
        error = min(1.0, conservation_penalty + entropy_penalty + omission_penalty
                    + net_value_penalty + temporal_penalty
                    + imperfection_penalty + equilibrium_penalty)

        # Determine outcome
        confidence_error_gap = claim.confidence - (1.0 - error)

        if confidence_error_gap > 0.3:
            outcome = Outcome.INVALID
        elif confidence_error_gap > 0.1:
            outcome = Outcome.PARTIALLY_VALID
        elif error < 0.2:
            outcome = Outcome.VALID
        else:
            outcome = Outcome.PARTIALLY_VALID

        # Build system accounting string
        accounting = ledger.summary()
        accounting += f"\n\n{ledger.temporal_projection()}"
        accounting += f"\n\nClaim Analysis ({claim_agent_key or 'unknown'}):"
        accounting += f"\n  Conservation penalty: {conservation_penalty:.3f}"
        accounting += f"\n  Entropy penalty:      {entropy_penalty:.3f}"
        accounting += f"\n  Omission penalty:     {omission_penalty:.3f}"
        accounting += f"\n  Net value penalty:    {net_value_penalty:.3f}"
        accounting += f"\n  Temporal penalty:     {temporal_penalty:.3f} (horizon: {horizon_months} months)"
        accounting += f"\n  Imperfection penalty: {imperfection_penalty:.3f}"
        accounting += f"\n  Equilibrium penalty:  {equilibrium_penalty:.3f}"
        accounting += f"\n  Total error:          {error:.3f}"

        for v in imperfection_violations:
            accounting += f"\n\n  >> {v}"

        if equilibrium_msg:
            accounting += f"\n\n  >> {equilibrium_msg}"

        if company_gain > 0 and external_cost > company_gain:
            accounting += (
                f"\n\n  >> THE MARGIN IS A LIE: Company shows +{company_gain:,.0f} "
                f"but external systems absorb -{external_cost:,.0f}. "
                f"Net system value: {net_system:,.0f}"
            )

        if external_cost_at_horizon > external_cost * 1.5:
            accounting += (
                f"\n\n  >> TEMPORAL AMPLIFICATION: External costs grow from "
                f"{external_cost:,.0f} to {external_cost_at_horizon:,.0f} "
                f"over {horizon_months} months. The bill compounds."
            )

        return Resolution(
            claim_id=claim.id,
            outcome=outcome,
            error_margin=round(error, 3),
            system_accounting=accounting,
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


def _parse_time_horizon(raw: str) -> float:
    """Parse a time horizon string into months.

    Handles: '12 Months', '18 Months', '25 Years', 'Q3-Q4' (6 months),
    '36 Months', plain numbers.
    """
    raw = raw.strip().lower()
    import re

    # "25 years" -> 300
    match = re.search(r'(\d+)\s*year', raw)
    if match:
        return float(match.group(1)) * 12

    # "18 months" -> 18
    match = re.search(r'(\d+)\s*month', raw)
    if match:
        return float(match.group(1))

    # "Q3-Q4" -> ~6 months
    if 'q' in raw:
        quarters = re.findall(r'q(\d)', raw)
        if len(quarters) >= 2:
            return (int(quarters[-1]) - int(quarters[0]) + 1) * 3
        return 3  # single quarter

    # Plain number
    match = re.search(r'(\d+)', raw)
    if match:
        return float(match.group(1))

    return 12  # Default 12 months
