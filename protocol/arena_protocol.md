# Arena Protocol

## Purpose

The arena exists to make ensemble disagreements productive — not to collapse them into consensus.

Disagreement is information. The arena's job is to preserve it, structure it, and make it navigable. A session ends with a convergence map, not a verdict.

## Version

This protocol governs v2 of the arena. v1 (`arena.py`) runs a different mode — adversarial, zero-sum — and its documentation lives in `AI-argument-arena.md`. The two modes are not interchangeable. See `MODES.md` for when to use each.

## Session lifecycle

```
admit agents
  └─ each declares transparency level (transparent | private)
submit reasoning artifacts
  └─ proposals, critiques, revisions routed by RTP
read shared pool (if permitted)
record convergence observations
  └─ agree / disagree / notes — disagreement preserved, not voted away
publish conclusions
  └─ public; all agents may read regardless of transparency level
```

## What the arena does not do

- It does not declare winners.
- It does not transfer trust from one agent to another.
- It does not produce a single answer.
- It does not punish disagreement.
- It does not reward agreement.

## Components

| Module | Role |
|---|---|
| `arena/admission.py` | Agent registration, per-dimension trust record |
| `arena/reciprocity.py` | RTP access rule enforcement |
| `arena/routing.py` | Logical destination for reasoning artifacts |
| `arena/visibility.py` | In-memory shared pool with access control |
| `arena/coordinator.py` | Session coordinator — single entry point |
| `arena/audit.py` | Bridges to `shared_blind_spot` and `trainer_mismatch_audit` |

## Related protocols

- `transparency_protocol.md` — what transparent participation means
- `reciprocity_protocol.md` — the access rule and its rationale
- `trust_protocol.md` — per-dimension trust record specification
- `audit_protocol.md` — when and how to run the audit detectors
