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


@dataclass
class EntropyEvent:
    """An irreversible change in the system. Entropy always increases."""
    domain: Domain
    description: str
    magnitude: float  # 0-1 scale of how much capacity was permanently lost
    reversible: bool = False


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
        ledger.transfer(
            source=source,
            target=target,
            amount=entry.get("amount", 0),
            description=entry.get("description", ""),
            reversible=entry.get("reversible", True),
            recovery_time=entry.get("recovery_time", 0),
            confidence=entry.get("confidence", 1.0),
        )

    entropy_data = scenario.get("entropy_events", [])
    for entry in entropy_data:
        domain = Domain(entry["domain"])
        ledger.add_entropy(
            domain=domain,
            description=entry.get("description", ""),
            magnitude=entry.get("magnitude", 0),
        )

    return ledger
