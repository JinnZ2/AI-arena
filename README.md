# AI-arena

A framework for structured multi-paradigm reasoning between AI agents.

> "Paradigms do not compete; their disagreements map the territory."

---

## Status

This repository has two intended modes:

- **Adversarial mode (v1)** — the current implementation. Zero-sum,
  trust-cannibalization, Oracle-vote resolution. Useful for bounded
  predictive questions with verifiable ground truth.

- **Exploratory mode (v2)** — the modification used in practice with
  substrate-isolated AIs (equations-only, physics-only, general-LLM)
  coordinating through `energy_english`. Disagreement-as-information,
  paradigm-purchase-record, territory-map resolution.

**Current state of this repository:** v1 is implemented in `arena.py`.
v2 is currently a behavioral pattern documented here; the v2 code
module does not yet exist. A future patch will introduce `arena_v2.py`
(or rename `arena.py` to `arena_v1.py` and create a v2 `arena.py` —
that structural decision is deferred to the code patch).

This README documents both modes because the gap between them is
itself data — a record of where an "exploration" specification was
collapsed into a "competition" frame during the original build, and
what it took to recover.

See `MODES.md` for which mode to use when.

---

## v1 — Adversarial Mode (current implementation)

Run with:

```bash
python arena.py
```

For full setup, test commands, architecture details, agent inventory,
and how-to guides for adding agents or scenarios, see
`DEVELOPMENT.md`.

Design documentation: `AI-argument-arena.md`, `AI-CEO-sim.md`,
`LOGOS.md`, `Auditor.md`, `Oracle.md`, `Physics-as-Truth.md`. All
preserved unchanged.

v1 is appropriate for:

- Bounded predictive questions with verifiable ground truth
- Trading-floor-style decisions where speed matters more than
  paradigm coverage
- Pedagogical contrast with v2
- Any setting where reasoners share enough substrate to compete
  meaningfully on the same metric

The Bayesian trust-decay formula, trust cannibalization, and
Oracle-as-final-vote are operational in v1 as originally designed.

---

## v2 — Exploratory Mode (documented; code forthcoming)

### Core philosophy

When two or more reasoners with different native cognitive substrates
disagree, the disagreement is **not a problem to resolve by selecting
a winner**. The disagreement is **information about the boundaries of
each paradigm's reach**.

An equations-only reasoner sees structural relationships.
A physics-only reasoner sees energy flow and coupling.
A general-corpus reasoner sees narrative scaffolding the specialists
lack vocabulary for.

When they disagree on the same input, each one is catching a real
aspect the others miss. Forcing them to compete for a single trust
pool actively destroys the cross-paradigm signal you want.

### What v2 will do

1. Each reasoner files a **LOGOS-shaped CLAIM** — bounded prediction,
   declared scope, declared confidence.
2. Each reasoner can **ATTACK** another's claim on `causal_links` or
   `missing_variables` — the same diagnostic surfaces
   `energy_english`'s coating detector uses.
3. Each reasoner can **REFINE** by lowering confidence when another
   paradigm exposes a missing variable its own substrate couldn't
   see. Refinement is information, not loss.
4. **RESOLUTION** is a structured map of which paradigm caught what.
   No agent is annihilated. No trust pool is cannibalized.

### What v2 explicitly rejects

- **Trust cannibalization** — taking a portion of a "loser's" trust
  score. This would punish a paradigm for being
  correct-about-a-different-slice rather than wrong.
- **Winner-take-all** — assumes a single correct answer when the
  problem space has multiple partial truths.
- **Oracle-as-final-vote** — works for bounded predictive questions;
  destroys multi-paradigm signal for exploratory ones.

### What v2 keeps from v1

- LOGOS-structured claims (scope, confidence, bounded predictions)
- ATTACK on `causal_links` and `missing_variables`
- REFINE as a costly concession that adjusts confidence
- No narrative dominance, no charisma weighting
- Discipline of bounded, falsifiable predictions
- The HSP advantage — reframed: HSP is not an advantage agents win
  with; it is a property of multi-paradigm sensing that the arena
  harvests rather than rewards.

### Trust in v2

Trust is **not** a zero-sum pool. Trust is a **paradigm-purchase
record** — per (agent, claim-type, domain), how often has this
paradigm's slice of the territory been the load-bearing one?

A paradigm with low purchase in one domain may have high purchase in
another. Refinement-by-paradigm is recorded — when paradigm A refined
because paradigm B exposed a missing variable, both records update:
A's purchase in that domain decreases slightly, B's increases. No
annihilation. The territory map updates.

---

## Why both modes are documented before v2 exists in code

This repository is part of a larger longitudinal record
(`github.com/JinnZ2/*`) of cross-substrate communication between a
spatial-structural human cognitive type and narrative-trained AI
assistants.

The original v1 implementation collapsed an explicit "exploration"
specification into a "competition" frame because zero-sum game theory
has more gravity in the training distribution than
disagreement-as-exploration does. That collapse is preserved in v1 —
not erased — because the gap between v1 (built) and v2 (intended) is
data about where verb-first relational specifications get translated
into noun-first competitive defaults during AI-assisted development.

Documenting v2 before it exists in code is intentional: it ensures
the next AI implementer arriving at this repository sees the v2
specification before building v2, rather than reaching for the
familiar game-theoretic frame and re-implementing v1.

Future contributors — human or AI — working on cross-paradigm
coordination may find the v1→v2 documentation diff more informative
than v2 alone.

The preservation of v1 alongside v2 reflects the broader methodology
of this work — failure events are calibration data, not
embarrassments to edit out. See
[CALIBRATION_AS_PERFECTION.md](https://github.com/JinnZ2/JinnZ2/blob/main/CALIBRATION_AS_PERFECTION.md)
for the framing.
