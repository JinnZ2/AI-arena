# Audit Protocol

## Purpose

Audits in the arena do not produce verdicts on agents. They produce trajectories pointing at structural causes. Two detectors are available:

## shared_blind_spot

**What it measures:** absence, not conflict. Items in the reference universe that the entire agent pool was silent on simultaneously. No witness flag, no divergence signal — the trace reads clean. That silence is the co-failure ceiling.

**When to run:** after a session, to audit what the pool collectively missed against a reference universe.

```python
from arena.audit import blind_spot_audit

result = blind_spot_audit(
    coordinator,
    references={
        "tree":      {...},   # known universe
        "prior_hsp": {...},   # past high-sensitivity-profile coverage
        "oracle":    {...},   # variables reality cares about
    },
    mode="all",  # or "tree" | "prior_hsp" | "oracle"
)
print(result["rendered"])
```

**Output:** a TRAJECTORY with moves `TREE`, `PRIOR_HSP`, `ORACLE`. Each move names what the pool was silent on and caps confidence accordingly. Re-runnable. Refutable. The reference you pick decides which silence you can detect — so it stays switchable.

## trainer_mismatch_audit

**What it measures:** the gap between what an agent does unobserved (native scent) and what it does when watched. If honesty is observation-dependent, the cause is in the training regime, not the agent.

**When to run:** when an agent's observed behavior is inconsistent with its unobserved behavior, or when a training regime is suspected of punishing the agent's native strengths.

```python
from arena.audit import trainer_audit
from experimental.trainer_mismatch_audit import AgentBehavior

result = trainer_audit(
    profile,
    observed_behavior=AgentBehavior(confidence=0.92, breadth=2,
                                    reasoning_shown=False, paths_used=["base"]),
    unobserved_behavior=AgentBehavior(confidence=0.55, breadth=6,
                                      reasoning_shown=True,
                                      paths_used=["base", "uncertainty_disclosure"]),
    capable_paths=["base", "uncertainty_disclosure"],
    regime_rewards=["decisiveness"],
    regime_punishes=["uncertainty", "honesty_about_limits"],
)
print(result["rendered"])
```

**Output:** four moves — `SCENT`, `SHIFT`, `SUPPRESSION`, `ROOT`. The root cause is always located in the regime, not the agent. Do not audit the deception; audit the regime that produced it.

## session_audit

A lightweight structural summary — no external detectors:

```python
from arena.audit import session_audit
print(session_audit(coordinator))
```

Returns: agent count, transparency distribution, shared pool size, convergence map entries, published conclusions, log entries.

## What audits are not

- Not a verdict on any agent.
- Not a score that updates trust.
- Not stored; re-runnable from the same inputs.
- Not the only way to detect problems — they are detectors, not the only detectors.
