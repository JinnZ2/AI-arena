# Physics as Truth: Formal Foundation

## Preamble

The AI Arena does not ground truth in consensus, authority, or rhetoric.
It grounds truth in physics. Physical laws are the only axioms the system
accepts as non-negotiable — everything else is a claim subject to attack.

**Why physics?** Because physical laws are the only propositions humans have
discovered that have never been successfully attacked across all observed
conditions. They are not beliefs. They are constraints on reality.

The Arena inherits these constraints directly. An agent that violates
thermodynamics is not "wrong" in some opinion-based sense — it is
*incoherent*. Its model cannot correspond to any possible reality.

---

## The Four Axioms

### Axiom 1: Conservation (First Law of Thermodynamics)

> **Energy cannot be created or destroyed, only transferred.**

**Arena enforcement**: Cost cannot be created or destroyed, only transferred
between domains. Every gain has a source. Every saving has a recipient of
the cost that was "saved."

```
∀ system S: Σ(transfers across all domains) = 0
```

If an agent claims +$4M in savings without accounting for where that $4M
went (workers, community, healthcare, environment, infrastructure, future
generations), the claim violates conservation and is penalized.

**Oracle rule**: `conservation_error = |Σ(domain_balances)| > 0 → penalty`

**Implication**: There is no free lunch. Every "efficiency gain" is a
transfer, not a creation. The only question is: *from whom?*

---

### Axiom 2: Irreversibility (Second Law of Thermodynamics)

> **Entropy in a closed system never decreases.**

**Arena enforcement**: Irreversible actions permanently increase system
entropy. Destroyed knowledge, burned resources, broken trust — these
cannot be recovered to their original state. The entropy is monotonic.

```
∀ system S, time t₁ < t₂: entropy(S, t₂) ≥ entropy(S, t₁)
```

**Key properties**:
- Entropy compounds: `magnitude(t) = magnitude₀ × e^(rate × t)`
- Knowledge gaps widen as the world advances past the lost knowledge
- Institutional memory has no backup — once the people leave, it's gone
- Materials launched into orbit cannot be recovered at equivalent cost

**Oracle rule**: `entropy_penalty = min(0.3, total_entropy × 0.5)`

**Implication**: Reversibility claims carry the burden of proof. "We can
always rehire" is a claim that must survive attack. The Arena defaults to
irreversible unless proven otherwise.

---

### Axiom 3: Imperfection (Third Law of Thermodynamics)

> **Absolute zero (perfect order) is unattainable.**

**Arena enforcement**: No agent may claim perfect efficiency, zero waste,
zero risk, or complete optimization. Every real process has friction,
overhead, and loss. Claims of zero-loss outcomes are physically incoherent.

```
∀ process P: efficiency(P) < 1.0
∀ claim C: if claimed_loss(C) = 0 → REJECT
```

**Key properties**:
- Zero defect rates are unreachable — asymptotic approach only
- 100% utilization is a myth (queuing theory confirms collapse at ~85%)
- "Frictionless" transitions do not exist in complex systems
- Any claim of zero externalities is a conservation violation in disguise

**Oracle rule**: `if min_loss_claimed < epsilon → imperfection_penalty`

**Carnot Bound**: Every transformation process has a maximum theoretical
efficiency determined by its boundary conditions. Just as no heat engine
can exceed Carnot efficiency `η = 1 - T_cold/T_hot`, no organizational
process can extract more value than the theoretical maximum set by its
constraints. Claims exceeding this bound are rejected.

```
η_max(process) = 1 - (minimum_unavoidable_overhead / total_input)
claimed_efficiency > η_max → REJECT
```

**Implication**: Perfection claims are a red flag. An agent claiming zero
waste is either lying or has hidden the waste outside its model boundary.

---

### Axiom 4: Equilibrium Resistance (Le Chatelier's Principle)

> **A system at equilibrium, when subjected to a disturbance, adjusts
> to partially counteract the disturbance.**

**Arena enforcement**: Large, sudden changes to stable systems produce
counterforces. Rapid cost-cutting triggers attrition. Aggressive growth
creates technical debt. Forced restructuring generates resistance.

```
∀ disturbance D on system S at equilibrium:
    ∃ counterforce F ∝ magnitude(D)
    net_effect(D) < intended_effect(D)
```

**Key properties**:
- Systems have inertia — they resist displacement
- The larger the disturbance, the stronger the counterforce
- Counterforces are often delayed (DELAYED temporal profile)
- Ignoring counterforce = missing_variable attack surface

**Oracle rule**: `if disturbance_magnitude > threshold and counterforce not modeled → equilibrium_penalty`

**Implication**: "We'll just cut 30% of staff and everything else stays
the same" is a Le Chatelier violation. The system *will* respond, and
any model that doesn't account for that response is incomplete.

---

## Derived Principles

These follow from the four axioms:

### D1: Temporal Truth (from Axiom 2)

Short-term accounting is always misleading. The true cost of any action
only emerges over time as entropy compounds and delayed effects manifest.

```
truth(action) = lim(t→∞) net_system_value(t)
```

Agents are rewarded for longer time horizons and penalized for claims
that only hold in the immediate term.

### D2: Closed System Boundary (from Axiom 1)

The system boundary must include all affected domains. "Externality" is
a euphemism for "cost I'm pretending doesn't exist." In a properly
bounded system, there are no externalities — only transfers.

```
∀ cost C: ∃ domain D such that C ∈ D
"externality" → missing_variable attack
```

### D3: Friction Tax (from Axiom 3)

Every process must include a friction estimate. The minimum friction
for a transformation is proportional to the complexity of the change.

```
friction(process) ≥ k × complexity(process)
where k > 0 (never zero)
```

### D4: Resistance Gradient (from Axiom 4)

The expected counterforce is proportional to the rate of change, not
just the magnitude. Fast changes produce disproportionately large
resistance compared to gradual ones.

```
counterforce ∝ d(disturbance)/dt
```

This is why phased rollouts produce less entropy than sudden
restructuring, even at the same final magnitude.

---

## How Truth Emerges

In the Arena, truth is not declared — it survives. The physics axioms
define what *cannot* be true (conservation violations, entropy reversal,
perfect efficiency, ignored counterforces). Everything else is a
prediction subject to oracle judgment.

The process:

1. Agent makes a claim
2. Claim is checked against axioms (validator)
3. Other agents attack axiom violations
4. Oracle measures actual outcomes
5. Trust adjusts: physics-consistent agents rise, violators decay

Over sufficient cycles, **the only agents with trust are those whose
models are consistent with physical law**. This is Epistemic Natural
Selection: reality is the fitness function.

---

## Relationship to LOGOS

LOGOS primitives enforce physics at the language level:

| LOGOS Primitive | Physics Enforcement |
|---|---|
| CLAIM (confidence < 1.0) | Axiom 3 — imperfection |
| CLAIM (must be falsifiable) | All axioms — claims testable against physical constraints |
| ATTACK: missing_variable | Axiom 1 — conservation boundary incomplete |
| ATTACK: irreversible_entropy | Axiom 2 — entropy not accounted |
| ATTACK: causal_break | Axiom 4 — counterforce ignored |
| ATTACK: scope_violation | Axiom 1 — system boundary too narrow |
| REFINE (costly concession) | Axiom 3 — acknowledging friction |
| ABSTAIN | Axiom 3 — admitting imperfect knowledge |

---

## Summary

| Axiom | Physical Law | Arena Rule | Violation Penalty |
|---|---|---|---|
| 1. Conservation | 1st Law | Σ transfers = 0 | conservation_penalty |
| 2. Irreversibility | 2nd Law | Entropy never decreases | entropy_penalty |
| 3. Imperfection | 3rd Law | No process is 100% efficient | imperfection_penalty |
| 4. Equilibrium Resistance | Le Chatelier | Large changes create counterforces | equilibrium_penalty |

The physics doesn't care what the agent believes. The physics doesn't
care what the consensus says. The physics is the ground truth, and the
Arena is the mechanism that enforces it.

**"Arguments do not win. Predictions survive. Physics decides."**
