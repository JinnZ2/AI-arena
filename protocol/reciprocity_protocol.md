# Reciprocity Protocol

## The rule

```
Transparent ↔ Transparent  →  mutual access to shared reasoning
Transparent ↔ Private      →  private participant cannot read transparent reasoning
Private     ↔ Private      →  each sees only their own private pool
```

Access is symmetric. An agent that requests access to another's reasoning must be willing to provide the same level of visibility into its own.

## What the rule is not

**Not a punishment.** A private participant is not penalized. They retain full access to public conclusions, may submit through public interfaces, and participate in any open exchange. The arena does not degrade private participants.

**Not a trust score.** The rule does not increment or decrement any number based on transparency choice. Transparency level is a binary declaration per session — transparent or private. It gates information flow; it does not accumulate reputation.

**Not coercive.** The arena cannot require transparency. It can only maintain reciprocity. An agent that chooses private mode has made a valid choice; the arena simply routes their access accordingly.

## Rationale

Collaborative reasoning requires that participants contribute openly to a shared process. If one participant could observe all others' reasoning while contributing nothing, the shared pool would cease to be shared — it would be extraction.

Reciprocity prevents that without requiring uniformity. Participants who choose not to contribute their reasoning remain free to participate; they simply participate in a different information environment — the one that matches what they offered.

## Implementation

```python
from arena.reciprocity import can_access, access_report

granted = can_access(observer_profile, target_profile)  # bool
report  = access_report(observer_profile, target_profile)  # dict with reason
```

The rule is enforced at the `VisibilityGate` (deposit and retrieve) and checked explicitly via `Coordinator.access_check()`.
