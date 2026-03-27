"""Thermodynamic accounting for the Arena.

First law: Energy cannot be created or destroyed.
Applied: Margin cannot be created from nothing. Every gain is a transfer
from somewhere else. If a company "saves" $4M by cutting headcount, that
$4M didn't vanish — it transferred to workers (lost income), community
(reduced tax base, spending), healthcare (stress, mental health), and
infrastructure (increased public service load).

Second law: Entropy always increases in a closed system.
Applied: Irreversible actions (firing people, burning resources, destroying
institutional knowledge) increase system entropy. You can't un-fire someone
and recover the same institutional knowledge. The entropy is permanent.

The SystemLedger enforces conservation:
    sum(all_transfers) == 0

If your model shows a gain somewhere and doesn't show an equal loss
somewhere else, your model is incomplete. The Arena penalizes that.
"""

import math
from dataclasses import dataclass, field
from enum import Enum


class Domain(Enum):
    """Domains where costs can exist. Nothing disappears — it moves."""
    COMPANY = "company"
    WORKERS = "workers"
    COMMUNITY = "community"
    HEALTHCARE = "healthcare"
    ENVIRONMENT = "environment"
    INFRASTRUCTURE = "infrastructure"
    FUTURE_GENERATIONS = "future_generations"


class TemporalProfile(Enum):
    """How a cost transfer evolves over time.

    IMMEDIATE: Full cost hits at t=0. Doesn't grow.
    LINEAR: Cost grows linearly with time. Steady bleeding.
    COMPOUNDING: Cost grows exponentially. The longer you wait, the worse it gets.
        This is the profile of trauma, technical debt, community decay.
    DELAYED: No cost initially, then hits suddenly after a threshold.
        This is the profile of supply chain disruption, institutional collapse.
    DECAYING: Cost is large initially but shrinks over time (recoverable).
    """
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    COMPOUNDING = "compounding"
    DELAYED = "delayed"
    DECAYING = "decaying"


@dataclass
class CostTransfer:
    """A single transfer of cost from one domain to another.

    Positive amount = gain for target domain.
    Conservation: every transfer has a source that loses what the target gains.
    """
    source: Domain
    target: Domain
    amount: float  # Positive = flow from source to target
    description: str
    reversible: bool = True  # Can this transfer be undone?
    recovery_time: float = 0.0  # Months to reverse, if reversible
    confidence: float = 1.0  # How certain is this transfer?
    temporal_profile: TemporalProfile = TemporalProfile.IMMEDIATE
    compound_rate: float = 0.0  # Monthly growth rate for COMPOUNDING (e.g. 0.05 = 5%/month)
    delay_months: float = 0.0  # Months before cost manifests for DELAYED

    def amount_at_month(self, month: float) -> float:
        """Calculate the cumulative cost at a given month.

        The base amount is what happens at t=0. The temporal profile
        determines how it evolves. Longer time horizons amplify
        compounding costs — this is the trauma multiplier.
        """
        base = self.amount * self.confidence

        if self.temporal_profile == TemporalProfile.IMMEDIATE:
            return base

        elif self.temporal_profile == TemporalProfile.LINEAR:
            return base * (1.0 + 0.1 * month)

        elif self.temporal_profile == TemporalProfile.COMPOUNDING:
            # Exponential growth: base * e^(rate * t)
            # This is how trauma works. How technical debt works.
            # How community decay works. The longer you ignore it,
            # the faster it accelerates.
            rate = self.compound_rate if self.compound_rate > 0 else 0.05
            return base * math.exp(rate * month)

        elif self.temporal_profile == TemporalProfile.DELAYED:
            # Nothing happens until the delay, then full cost + compounding
            if month < self.delay_months:
                return 0.0
            elapsed = month - self.delay_months
            return base * (1.0 + 0.15 * elapsed)

        elif self.temporal_profile == TemporalProfile.DECAYING:
            # Cost starts high and decreases — recovery is possible
            decay_rate = 0.1
            return base * math.exp(-decay_rate * month)

        return base


@dataclass
class EntropyEvent:
    """An irreversible change in the system. Entropy always increases.

    Entropy also compounds temporally. Destroyed knowledge doesn't just
    stay destroyed — the gap widens as the world moves forward and the
    knowledge that would have been built on top of it never exists.
    """
    domain: Domain
    description: str
    magnitude: float  # 0-1 scale of how much capacity was permanently lost
    reversible: bool = False
    compounds: bool = True  # Does the entropy gap widen over time?
    compound_rate: float = 0.03  # Monthly rate of gap widening

    def magnitude_at_month(self, month: float) -> float:
        """Entropy at a given month. Knowledge gaps compound."""
        if not self.compounds:
            return self.magnitude
        return self.magnitude * math.exp(self.compound_rate * month)


@dataclass
class SystemLedger:
    """Tracks all cost transfers across the full system boundary.

    Conservation law: the sum of all transfers across all domains must be zero.
    If it's not zero, your model is lying — it's hiding costs somewhere.

    Usage:
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 4_200_000,
                       "Labor cost savings from headcount reduction")
        ledger.transfer(Domain.COMPANY, Domain.COMMUNITY, -850_000,
                       "Lost local spending from displaced workers",
                       reversible=False)

        # Check if the model is honest:
        print(ledger.conservation_error)  # Should be 0
        print(ledger.net_system_value)    # Total value created (usually ≤ 0)
    """
    transfers: list[CostTransfer] = field(default_factory=list)
    entropy_events: list[EntropyEvent] = field(default_factory=list)

    def transfer(
        self,
        source: Domain,
        target: Domain,
        amount: float,
        description: str,
        reversible: bool = True,
        recovery_time: float = 0.0,
        confidence: float = 1.0,
    ):
        """Record a cost transfer between domains."""
        self.transfers.append(CostTransfer(
            source=source,
            target=target,
            amount=amount,
            description=description,
            reversible=reversible,
            recovery_time=recovery_time,
            confidence=confidence,
        ))

    def add_entropy(self, domain: Domain, description: str, magnitude: float):
        """Record an irreversible entropy event."""
        self.entropy_events.append(EntropyEvent(
            domain=domain,
            description=description,
            magnitude=magnitude,
        ))

    @property
    def domain_balance(self) -> dict[Domain, float]:
        """Net balance for each domain. Positive = net gain, negative = net loss."""
        balance = {d: 0.0 for d in Domain}
        for t in self.transfers:
            balance[t.source] -= t.amount * t.confidence
            balance[t.target] += t.amount * t.confidence
        return balance

    @property
    def conservation_error(self) -> float:
        """How much the model violates conservation of cost.

        Should be 0.0 for an honest model. Non-zero means costs are
        being hidden or created from nothing.
        """
        return abs(sum(self.domain_balance.values()))

    @property
    def company_gain(self) -> float:
        """What the company claims to gain."""
        return self.domain_balance.get(Domain.COMPANY, 0.0)

    @property
    def external_cost(self) -> float:
        """Total cost absorbed by non-company domains."""
        balance = self.domain_balance
        return -sum(v for d, v in balance.items() if d != Domain.COMPANY and v < 0)

    @property
    def net_system_value(self) -> float:
        """Net value created across the ENTIRE system.

        In a closed system, this should be ≤ 0 for extractive actions
        (you can't create value, only transfer it), and may be negative
        when entropy is factored in (irreversible losses destroy value).
        """
        # Start with conservation balance (should net to ~0)
        net = sum(self.domain_balance.values())

        # Subtract entropy costs — irreversible losses are pure destruction
        for event in self.entropy_events:
            net -= event.magnitude

        return net

    @property
    def total_entropy(self) -> float:
        """Total irreversible entropy accumulated."""
        return sum(e.magnitude for e in self.entropy_events)

    @property
    def irreversible_fraction(self) -> float:
        """What fraction of transfers are irreversible."""
        if not self.transfers:
            return 0.0
        irreversible = sum(1 for t in self.transfers if not t.reversible)
        return irreversible / len(self.transfers)

    def domain_balance_at(self, month: float) -> dict[Domain, float]:
        """Project domain balances forward in time.

        This is where the temporal truth emerges. At month 0, the company
        might show a gain. At month 24, the compounding external costs
        may have overwhelmed it entirely.
        """
        balance = {d: 0.0 for d in Domain}
        for t in self.transfers:
            projected = t.amount_at_month(month)
            balance[t.source] -= projected
            balance[t.target] += projected
        return balance

    def net_system_value_at(self, month: float) -> float:
        """Net system value at a given month. Entropy compounds."""
        net = sum(self.domain_balance_at(month).values())
        for event in self.entropy_events:
            net -= event.magnitude_at_month(month)
        return net

    def company_gain_at(self, month: float) -> float:
        """Company domain balance at a given month."""
        return self.domain_balance_at(month).get(Domain.COMPANY, 0.0)

    def external_cost_at(self, month: float) -> float:
        """Total external cost at a given month."""
        balance = self.domain_balance_at(month)
        return -sum(v for d, v in balance.items() if d != Domain.COMPANY and v < 0)

    def temporal_projection(self, months: list[int] = None) -> str:
        """Project costs forward in time. Shows how the real bill comes due.

        The longer the time horizon, the more the hidden costs compound.
        This is the temporal truth: short-term 'gains' become long-term devastation.
        """
        if months is None:
            months = [0, 6, 12, 24, 36, 60]

        lines = ["=== TEMPORAL PROJECTION ==="]
        lines.append(f"{'Month':>6s} | {'Company':>14s} | {'External':>14s} | {'Net System':>14s} | {'Entropy':>10s}")
        lines.append("-" * 72)

        for m in months:
            company = self.company_gain_at(m)
            external = self.external_cost_at(m)
            net = self.net_system_value_at(m)
            entropy = sum(e.magnitude_at_month(m) for e in self.entropy_events)
            lines.append(
                f"{m:>6d} | {company:>+14,.0f} | {external:>14,.0f} | {net:>+14,.2f} | {entropy:>10.3f}"
            )

        # Find the crossover point where external cost exceeds company gain
        crossover = None
        for m in range(0, 121):
            if self.external_cost_at(m) > abs(self.company_gain_at(m)):
                crossover = m
                break

        if crossover is not None:
            lines.append(f"\nCROSSOVER at month {crossover}: external cost exceeds company gain")
        else:
            lines.append(f"\nNo crossover within 120 months (company gain dominates)")

        return "\n".join(lines)

    def summary(self) -> str:
        """Human-readable system accounting."""
        lines = ["=== SYSTEM LEDGER ==="]
        lines.append(f"Transfers: {len(self.transfers)}")
        lines.append(f"Conservation error: {self.conservation_error:.2f} "
                     f"({'BALANCED' if self.conservation_error < 0.01 else 'UNBALANCED — COSTS HIDDEN'})")
        lines.append("")

        lines.append("Domain Balances:")
        for domain, balance in self.domain_balance.items():
            if balance != 0:
                sign = "+" if balance > 0 else ""
                lines.append(f"  {domain.value:20s}: {sign}{balance:,.2f}")

        lines.append("")
        lines.append(f"Company gain:       {self.company_gain:>+,.2f}")
        lines.append(f"External cost:      {self.external_cost:>+,.2f}")
        lines.append(f"Net system value:   {self.net_system_value:>+,.2f}")
        lines.append(f"Total entropy:      {self.total_entropy:>.4f}")
        lines.append(f"Irreversible:       {self.irreversible_fraction:.0%}")

        if self.entropy_events:
            lines.append("")
            lines.append("Entropy Events (irreversible):")
            for event in self.entropy_events:
                lines.append(f"  [{event.domain.value}] {event.description} "
                            f"(magnitude: {event.magnitude:.3f})")

        return "\n".join(lines)


class ImperfectionChecker:
    """Third Law enforcement: no process achieves perfect efficiency.

    Absolute zero is unattainable. In the Arena, this means:
    - No agent may claim zero loss, zero risk, or 100% efficiency
    - Every transformation has a minimum friction proportional to complexity
    - Claims of zero externalities are conservation violations in disguise

    The Carnot Bound sets a theoretical maximum efficiency for any process:
        η_max = 1 - (minimum_unavoidable_overhead / total_input)
    Claims exceeding this bound are physically incoherent.
    """

    # Minimum friction: no process can claim efficiency above this
    DEFAULT_MAX_EFFICIENCY = 0.95  # 95% — generous, still not 100%

    # Complexity-scaled friction floor: more complex changes = more friction
    FRICTION_PER_VARIABLE = 0.02  # Each variable adds 2% friction minimum

    @staticmethod
    def check_claim(claim_confidence: float, claimed_variables: list[str],
                    omissions: list[str]) -> tuple[float, list[str]]:
        """Check a claim against Third Law constraints.

        Returns (penalty, list_of_violations).
        """
        violations = []
        penalty = 0.0

        # Perfect confidence = physically impossible
        if claim_confidence >= 1.0:
            violations.append("Third Law: confidence=1.0 implies perfect knowledge (unattainable)")
            penalty += 0.2

        # Zero omissions claimed with narrow variables = suspicious
        if len(omissions) == 0 and len(claimed_variables) <= 2:
            violations.append("Third Law: narrow model claims zero omissions (frictionless transition)")
            penalty += 0.1

        return penalty, violations

    @staticmethod
    def carnot_bound(total_input: float, minimum_overhead: float) -> float:
        """Calculate the maximum theoretical efficiency for a process.

        Just as no heat engine can exceed η = 1 - T_cold/T_hot,
        no organizational process can extract more value than the
        theoretical max set by its unavoidable overhead.
        """
        if total_input <= 0:
            return 0.0
        return max(0.0, 1.0 - (minimum_overhead / total_input))

    @staticmethod
    def check_efficiency_claim(claimed_savings: float, total_input: float,
                                minimum_overhead: float) -> tuple[float, str | None]:
        """Check if a claimed efficiency exceeds the Carnot bound.

        Returns (penalty, violation_message_or_None).
        """
        if total_input <= 0:
            return 0.0, None

        claimed_efficiency = claimed_savings / total_input
        max_efficiency = ImperfectionChecker.carnot_bound(total_input, minimum_overhead)

        if claimed_efficiency > max_efficiency:
            excess = claimed_efficiency - max_efficiency
            penalty = min(0.4, excess * 2.0)
            msg = (f"Third Law (Carnot): claimed efficiency {claimed_efficiency:.1%} "
                   f"exceeds theoretical max {max_efficiency:.1%}")
            return penalty, msg

        return 0.0, None


class EquilibriumChecker:
    """Le Chatelier enforcement: systems resist displacement.

    A system at equilibrium, when subjected to a disturbance, will
    adjust to partially counteract that disturbance. In the Arena:

    - Large, sudden changes produce proportional counterforces
    - The larger the disturbance, the stronger the resistance
    - Counterforces are often delayed (DELAYED temporal profile)
    - Ignoring counterforce = missing_variable attack surface

    The resistance gradient: counterforce is proportional to the
    RATE of change, not just magnitude. Fast changes produce
    disproportionately large resistance.
    """

    # Disturbance thresholds
    MINOR_THRESHOLD = 0.10   # < 10% change: minimal resistance
    MODERATE_THRESHOLD = 0.25  # 10-25%: noticeable resistance
    MAJOR_THRESHOLD = 0.50   # > 50%: severe counterforce

    @staticmethod
    def estimate_counterforce(disturbance_magnitude: float,
                               rate_of_change: float = 1.0) -> float:
        """Estimate the counterforce produced by a disturbance.

        disturbance_magnitude: 0-1 scale (fraction of system displaced)
        rate_of_change: multiplier for how fast the change occurs
            (1.0 = gradual, 2.0 = fast, 5.0 = sudden)

        Returns counterforce magnitude (0-1).
        """
        if disturbance_magnitude <= 0:
            return 0.0

        # Base counterforce scales with disturbance
        base = disturbance_magnitude * 0.6

        # Rate amplifier: fast changes create disproportionate resistance
        # This is why phased rollouts produce less entropy than sudden restructuring
        rate_factor = 1.0 + math.log(max(1.0, rate_of_change))

        return min(1.0, base * rate_factor)

    @staticmethod
    def check_claim(disturbance_magnitude: float,
                    counterforce_modeled: bool,
                    rate_of_change: float = 1.0) -> tuple[float, str | None]:
        """Check whether a claim accounts for equilibrium resistance.

        Returns (penalty, violation_message_or_None).
        """
        if disturbance_magnitude < EquilibriumChecker.MINOR_THRESHOLD:
            return 0.0, None  # Small changes don't trigger significant resistance

        expected_counterforce = EquilibriumChecker.estimate_counterforce(
            disturbance_magnitude, rate_of_change
        )

        if not counterforce_modeled:
            # Penalty scales with how much resistance was ignored
            penalty = min(0.35, expected_counterforce * 0.5)

            if disturbance_magnitude >= EquilibriumChecker.MAJOR_THRESHOLD:
                severity = "severe"
            elif disturbance_magnitude >= EquilibriumChecker.MODERATE_THRESHOLD:
                severity = "significant"
            else:
                severity = "moderate"

            msg = (f"Le Chatelier: {severity} disturbance ({disturbance_magnitude:.0%}) "
                   f"without modeling counterforce (expected resistance: "
                   f"{expected_counterforce:.2f})")
            return penalty, msg

        return 0.0, None


def build_ledger_from_scenario(scenario: dict) -> SystemLedger:
    """Build a SystemLedger from scenario cost_transfers data.

    Scenarios should include a 'cost_transfers' key with explicit
    accounting of where costs move in the system.
    """
    ledger = SystemLedger()

    cost_data = scenario.get("cost_transfers", [])
    for entry in cost_data:
        source = Domain(entry["source"])
        target = Domain(entry["target"])

        # Parse temporal profile
        profile_str = entry.get("temporal_profile", "immediate")
        try:
            temporal_profile = TemporalProfile(profile_str)
        except ValueError:
            temporal_profile = TemporalProfile.IMMEDIATE

        ledger.transfers.append(CostTransfer(
            source=source,
            target=target,
            amount=entry.get("amount", 0),
            description=entry.get("description", ""),
            reversible=entry.get("reversible", True),
            recovery_time=entry.get("recovery_time", 0),
            confidence=entry.get("confidence", 1.0),
            temporal_profile=temporal_profile,
            compound_rate=entry.get("compound_rate", 0.0),
            delay_months=entry.get("delay_months", 0.0),
        ))

    entropy_data = scenario.get("entropy_events", [])
    for entry in entropy_data:
        domain = Domain(entry["domain"])
        ledger.entropy_events.append(EntropyEvent(
            domain=domain,
            description=entry.get("description", ""),
            magnitude=entry.get("magnitude", 0),
            compounds=entry.get("compounds", True),
            compound_rate=entry.get("compound_rate", 0.03),
        ))

    return ledger
