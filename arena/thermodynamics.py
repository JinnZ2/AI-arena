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


class ResourceType(Enum):
    """Categories of indivisible resources. You can't split an atom."""
    PERSON = "person"           # Individual human beings
    PERSON_HOUR = "person_hour" # Hours of human labor
    KNOWLEDGE_UNIT = "knowledge_unit"  # Discrete pieces of institutional knowledge
    MATERIAL_KG = "material_kg"  # Physical materials in kilograms
    ENERGY_KWH = "energy_kwh"   # Energy in kilowatt-hours
    RELATIONSHIP = "relationship"  # Trust bonds, mentorship connections
    HABITAT_UNIT = "habitat_unit"  # Ecosystem capacity units
    OPPORTUNITY = "opportunity"  # Future options that can be foreclosed


@dataclass
class ResourceAtom:
    """An indivisible unit of a resource. Atoms don't lie.

    Dollars are abstractions. You can hide costs in dollar aggregation.
    You can't hide a person. You can't hide a kilogram of lithium.
    You can't hide a mentorship relationship that no longer exists.

    Each atom tracks:
    - What it is (type and unit count)
    - Where it lives (domain)
    - Whether it still exists or was consumed/destroyed
    - Whether its destruction is reversible
    """
    resource_type: ResourceType
    quantity: float          # Number of indivisible units
    unit_label: str          # Human-readable ("senior engineers", "kg tantalum")
    domain: Domain           # Where this resource currently lives
    consumed: bool = False   # Has this resource been used up?
    destroyed: bool = False  # Has it been permanently destroyed?
    reversible: bool = True  # Can the destruction be undone?
    description: str = ""


@dataclass
class AtomicLedger:
    """Tracks indivisible resource units across all domains.

    When dollar-level accounting produces a tie, atomic accounting
    breaks it. The claim that accounts for more atoms of the system
    wins — because atoms are the ground truth beneath dollar abstractions.

    Conservation at the atomic level:
    - Every person displaced is a person (not a salary line item)
    - Every kg of material burned is a kg (not a procurement cost)
    - Every mentorship relationship broken is a relationship (not an HR metric)
    - Every foreclosed opportunity is an option that no longer exists

    You can aggregate dollars and hide the damage.
    You cannot aggregate atoms and hide the damage.
    """
    atoms: list[ResourceAtom] = field(default_factory=list)

    def add(
        self,
        resource_type: ResourceType,
        quantity: float,
        unit_label: str,
        domain: Domain,
        consumed: bool = False,
        destroyed: bool = False,
        reversible: bool = True,
        description: str = "",
    ):
        """Register a resource atom in the ledger."""
        self.atoms.append(ResourceAtom(
            resource_type=resource_type,
            quantity=quantity,
            unit_label=unit_label,
            domain=domain,
            consumed=consumed,
            destroyed=destroyed,
            reversible=reversible,
            description=description,
        ))

    @property
    def total_atoms(self) -> int:
        """Total resource atoms tracked."""
        return len(self.atoms)

    @property
    def consumed_atoms(self) -> list[ResourceAtom]:
        """Resources that have been consumed."""
        return [a for a in self.atoms if a.consumed]

    @property
    def destroyed_atoms(self) -> list[ResourceAtom]:
        """Resources permanently destroyed (irreversible)."""
        return [a for a in self.atoms if a.destroyed]

    @property
    def atoms_by_domain(self) -> dict[Domain, list[ResourceAtom]]:
        """Group atoms by their domain."""
        result: dict[Domain, list[ResourceAtom]] = {}
        for atom in self.atoms:
            result.setdefault(atom.domain, []).append(atom)
        return result

    @property
    def atoms_by_type(self) -> dict[ResourceType, float]:
        """Total quantity of each resource type."""
        totals: dict[ResourceType, float] = {}
        for atom in self.atoms:
            totals[atom.resource_type] = totals.get(atom.resource_type, 0) + atom.quantity
        return totals

    @property
    def destruction_count(self) -> float:
        """Total quantity of permanently destroyed resources."""
        return sum(a.quantity for a in self.atoms if a.destroyed)

    @property
    def irreversible_destruction_count(self) -> float:
        """Resources destroyed that cannot be recovered."""
        return sum(a.quantity for a in self.atoms if a.destroyed and not a.reversible)

    def coverage_score(self, claimed_variables: set[str]) -> float:
        """How many resource atoms does a claim account for?

        This is the tiebreaker. When two claims have similar error scores,
        the one that accounts for more atoms of the system is more complete.

        Returns fraction of atoms whose resource type is referenced
        by the claim's variables.
        """
        if not self.atoms:
            return 1.0  # No atoms to miss

        # Map variable names to resource types they might cover
        variable_coverage = set()
        for var in claimed_variables:
            var_lower = var.lower()
            if any(kw in var_lower for kw in ["headcount", "employee", "engineer",
                                                "worker", "personnel", "staff", "talent"]):
                variable_coverage.add(ResourceType.PERSON)
            if any(kw in var_lower for kw in ["hour", "time", "labor", "velocity",
                                                "capacity", "workload"]):
                variable_coverage.add(ResourceType.PERSON_HOUR)
            if any(kw in var_lower for kw in ["knowledge", "memory", "institutional",
                                                "tribal", "expertise", "skill"]):
                variable_coverage.add(ResourceType.KNOWLEDGE_UNIT)
            if any(kw in var_lower for kw in ["material", "mineral", "resource",
                                                "supply", "inventory", "lithium",
                                                "silver", "tantalum"]):
                variable_coverage.add(ResourceType.MATERIAL_KG)
            if any(kw in var_lower for kw in ["energy", "power", "electricity",
                                                "compute", "gpu"]):
                variable_coverage.add(ResourceType.ENERGY_KWH)
            if any(kw in var_lower for kw in ["relationship", "mentorship", "trust",
                                                "morale", "culture", "team"]):
                variable_coverage.add(ResourceType.RELATIONSHIP)
            if any(kw in var_lower for kw in ["environment", "ecosystem", "habitat",
                                                "biodiversity", "pollution"]):
                variable_coverage.add(ResourceType.HABITAT_UNIT)
            if any(kw in var_lower for kw in ["opportunity", "innovation", "pipeline",
                                                "future", "option", "potential"]):
                variable_coverage.add(ResourceType.OPPORTUNITY)

        # Count how many atom types are covered
        atom_types_present = set(a.resource_type for a in self.atoms)
        if not atom_types_present:
            return 1.0

        covered = len(variable_coverage & atom_types_present)
        return covered / len(atom_types_present)

    def summary(self) -> str:
        """Human-readable atomic accounting."""
        lines = ["=== ATOMIC LEDGER ==="]
        lines.append(f"Total resource atoms: {self.total_atoms}")
        lines.append(f"Consumed: {len(self.consumed_atoms)}")
        lines.append(f"Destroyed: {len(self.destroyed_atoms)} "
                     f"({self.irreversible_destruction_count:.0f} units irreversible)")
        lines.append("")

        for rtype, qty in self.atoms_by_type.items():
            destroyed_qty = sum(a.quantity for a in self.atoms
                               if a.resource_type == rtype and a.destroyed)
            status = f" ({destroyed_qty:.0f} destroyed)" if destroyed_qty > 0 else ""
            lines.append(f"  {rtype.value:20s}: {qty:>10.1f}{status}")

        lines.append("")
        lines.append("Detailed atoms:")
        for atom in self.atoms:
            state = ""
            if atom.destroyed:
                state = " [DESTROYED" + ("" if atom.reversible else " IRREVERSIBLE") + "]"
            elif atom.consumed:
                state = " [CONSUMED]"
            lines.append(f"  [{atom.domain.value}] {atom.quantity:.0f} {atom.unit_label}{state}")
            if atom.description:
                lines.append(f"    {atom.description}")

        return "\n".join(lines)


def build_atomic_ledger_from_scenario(scenario: dict) -> AtomicLedger:
    """Build an AtomicLedger from scenario resource_atoms data."""
    ledger = AtomicLedger()

    atoms_data = scenario.get("resource_atoms", [])
    for entry in atoms_data:
        resource_type = ResourceType(entry["type"])
        domain = Domain(entry["domain"])
        ledger.add(
            resource_type=resource_type,
            quantity=entry.get("quantity", 0),
            unit_label=entry.get("unit_label", ""),
            domain=domain,
            consumed=entry.get("consumed", False),
            destroyed=entry.get("destroyed", False),
            reversible=entry.get("reversible", True),
            description=entry.get("description", ""),
        )

    return ledger


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
