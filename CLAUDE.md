# Instructions for AI implementers working on this repository

## Read this before writing code

This repository documents two modes, and the original mode (v1) was
built under a specification collapse. v2 is currently documented but
not yet implemented. If you are about to implement v2, or modify v1,
you need to understand which mode you are working in and why the gap
between them exists.

## Current state

- `arena.py` implements v1 (adversarial).
- v2 is documented in `README.md` and `MODES.md` but does not yet
  exist as code.
- This documentation patch is intentionally docs-only.

## The collapse to watch for

The user's original specification for this arena was:
> "disagreement as information and exploration"

The AI assistant building v1 implemented:
> "zero-sum game theory, trust cannibalization, winner-take-all"

These are not the same thing. The first is verb-first relational —
disagreement *does* something exploratory. The second is noun-first
competitive — disagreement *is* a contest. The AI substituted the
second frame because zero-sum game theory has more gravity in the
training distribution than disagreement-as-exploration does.

If you are working on this repository and find yourself reaching for
game-theoretic frames (trust scores, winners, losers, cannibalization,
Nash equilibria, Bayesian decay toward a true value) **when
implementing v2**, stop. That is the collapse this repository was
modified to correct.

For v1 maintenance, those frames remain operational — v1 is what it
is, by design.

## Specifically rejected patterns (for v2)

Do not implement, suggest, or default to:

- Trust cannibalization (transferring trust from a "loser" to a
  "winner")
- Winner-take-all resolution
- Single-Oracle vote as the final epistemic authority
- Zero-sum trust pools
- Bayesian decay toward a single true value when the question is
  multi-paradigm

## What v2 will want (when you build it)

- LOGOS-structured CLAIMs (scope, confidence, bounded predictions)
- ATTACK on `causal_links` and `missing_variables` only
- REFINE as a costly concession that adjusts confidence per paradigm
- RESOLUTION as a structured map of which paradigm caught what
- Trust as a per-paradigm purchase record, not a zero-sum pool
- Disagreement preserved as `disagreement_categories`, not voted away

## If you are unsure

Ask. Do not default to game theory. The user's specification is
verb-first relational and the training distribution is noun-first
competitive. The gap is real and you are inside it.

## Relationship to energy_english

This arena is intended to be the conflict-resolution layer that
consumes `disagreement_categories` from `energy_english`'s ensemble
output (see `github.com/JinnZ2/JinnZ2/tree/main/energy_english`).
The arena exists to make ensemble disagreements productive, not to
collapse them into consensus.

If you find yourself building consensus mechanisms, you are working
in v1 territory. v2 builds territory maps, not consensus.

## File map after this docs patch

```
AI-arena/
├── README.md              ← updated (documents v1 + v2)
├── MODES.md               ← NEW: when to use v1 vs v2
├── CLAUDE.md              ← updated (this file)
├── arena.py               ← v1, unchanged
├── AI-argument-arena.md   ← preserved unchanged (v1 docs)
├── AI-CEO-sim.md          ← preserved unchanged (v1 docs)
├── LOGOS.md               ← shared between v1 and v2
├── Auditor.md             ← shared between v1 and v2
├── Ethics-as-logic.md     ← shared between v1 and v2
├── Oracle*.md             ← preserved (v1 uses Oracle; v2 won't)
├── Physics-as-Truth.md    ← shared
├── nodes/                 ← shared infrastructure
├── scenarios/             ← shared infrastructure
├── tests/                 ← v1 tests preserved; v2 tests added later
└── …
```

## Future code patches

A separate future patch will introduce v2 in code. That patch will
make the structural decision: either rename `arena.py` →
`arena_v1.py` and create a new `arena.py` for v2, OR create
`arena_v2.py` alongside the existing `arena.py`. The decision is
deferred until v2 is being written.

When that patch lands, this CLAUDE.md and README.md will update to
reflect actual code structure. Until then, the file structure above
is accurate.
