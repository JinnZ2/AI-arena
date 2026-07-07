# Instructions for AI implementers working on this repository

## Read this before writing code

This repository documents two modes, and the original mode (v1) was
built under a specification collapse. v2 is currently documented but
not yet implemented. If you are about to implement v2, or modify v1,
you need to understand which mode you are working in and why the gap
between them exists.

For setup, run commands, architecture details, agent inventory, and
how-to guides for adding agents or scenarios, see `DEVELOPMENT.md`.

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
├── CLAUDE.md              ← updated (this file; v2-implementer guidance)
├── DEVELOPMENT.md         ← NEW: practical dev guide (setup, run, architecture, agents)
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


REVIEW.md — AI-arena

Reviewed against CLAUDE.md. This repo is in a documented transitional state between v1 (adversarial, implemented) and v2 (relational, specified but not yet coded). Findings respect that gap.

---

1. Structural Consistency & Conventions

· Documented file map vs. actual repo
  ✅ CLAUDE.md includes an explicit file map showing what was updated, preserved, or newly created in this docs patch.
  ⚠️ Verify: Do MODES.md and DEVELOPMENT.md actually exist? They're marked NEW. If missing, the docs patch is incomplete.
  ⚠️ Verify: Is arena.py truly unchanged? Any accidental drift from v1 behavior should be caught by the preserved test suite.
· Shared infrastructure
  ✅ nodes/, scenarios/, tests/ are marked as shared between v1 and v2. This is sensible, but:
  ❓ Are nodes/ and scenarios/ documented well enough that a v2 implementer knows what's reusable and what's v1-specific? A brief comment header or README in each directory would prevent accidental v1-frame contamination.
· Naming conventions
  ✅ Mix of PascalCase (MODES.md, DEVELOPMENT.md) and kebab-case (AI-argument-arena.md) — acceptable for a mixed docs/code repo. Python files use snake_case (arena.py). No violations.
· The deferred naming decision
  ❓ CLAUDE.md explicitly defers the arena_v1.py vs arena_v2.py decision. This is fine now, but it creates a ticking clock: the longer v2 code exists alongside v1 without a clear file naming convention, the harder the eventual rename will be. Consider making the decision before writing v2 code, not after.

---

2. The v1/v2 Tension (Collapse Risk Assessment)

This is the heart of the review. The CLAUDE.md exists because an AI assistant collapsed "disagreement as exploration" into "zero-sum game theory." The docs patch is the corrective. Here's what needs to hold:

· Are the rejected patterns sufficiently prominent?
  ✅ CLAUDE.md lists six rejected patterns (trust cannibalization, winner-take-all, single-Oracle vote, zero-sum trust pools, Bayesian decay to single truth).
  ⚠️ Recommendation: Copy this list into MODES.md and DEVELOPMENT.md as well. Redundancy is a feature when guarding against training-distribution gravity. A v2 implementer might read only DEVELOPMENT.md and miss the warnings in CLAUDE.md.
· Is v1 adequately quarantined?
  ✅ arena.py is marked as v1, unchanged.
  ❓ Do the preserved v1 docs (AI-argument-arena.md, AI-CEO-sim.md, Oracle*.md) carry a visible banner stating they describe v1 only? If a new contributor reads Oracle-Voting.md and assumes it applies to v2, they'll reintroduce the collapse. Add a header to each v1-only doc:
  > ⚠️ This document describes v1 (adversarial) only. For v2, see MODES.md.
· Shared files need mode-awareness
  ❓ LOGOS.md, Auditor.md, Ethics-as-logic.md, Physics-as-Truth.md are marked "shared between v1 and v2." Do they contain any v1-specific assumptions (e.g., Oracle as final authority, zero-sum framing)? Audit these for collapse-prone language. If any sentence assumes competition rather than exploration, flag it.
· The energy_english dependency
  ✅ CLAUDE.md clearly states v2 consumes disagreement_categories from energy_english. This boundary is well-defined.
  ❓ Is energy_english stable enough to build against? If its output format changes, v2 breaks. Consider pinning a version or adding a schema test.

---

3. Discoverability & Documentation

· Missing artifacts
  ❌ CITATION.cff — absent. Add:
  ```yaml
  cff-version: 1.2.0
  title: "AI-arena"
  authors:
    - name: "JinnZ2"
  license: MIT  # or whichever applies
  date-released: 2024-07-07
  url: "https://github.com/JinnZ2/AI-arena"
  ```
  ❌ KEYWORDS.txt — absent. Add: disagreement-as-exploration, multi-paradigm, verb-first-relational, structured-debate, epistemic-arena, LOGOS, ensemble-disagreement, non-adversarial.
  ❌ Repository topics — likely missing. Propose: debate, epistemology, multi-agent, disagreement, argumentation, non-zero-sum, consensus-alternatives.
  ❌ "Why This Matters" statement — especially important here. Suggestion:
  Most AI debate frameworks assume competition converges to truth. This one documents what happens when that assumption is wrong — and builds the alternative.
· MODES.md quality
  ❓ This is a new file. It must answer: When do I use v1? When do I use v2? What are the observable differences in behavior? A table or decision flowchart would help. If it's just prose, consider adding a quick-reference section.
· DEVELOPMENT.md quality
  ❓ Must include: setup, run commands, architecture diagram, agent inventory, how to add a scenario, and — critically — how to recognize when you're accidentally building v1-frame logic in v2 code.

---

4. Code Audit (Limited)

The only active code is arena.py (v1) and shared infrastructure in nodes/ and scenarios/. The review is constrained:

· v1 tests
  ✅ Preserved and should pass.
  ❓ Do the tests encode v1 assumptions (e.g., asserting a winner emerges, trust transfers occur)? If so, they serve as a partial specification of what v2 must not do. Document this: "If a test asserts a winner, it's a v1-only test."
· Shared infrastructure hygiene
  ❓ nodes/ and scenarios/ — do they import from arena.py? If they do, v2 will need to either refactor those imports or duplicate the shared code. Identify coupling points now, before v2 implementation begins.
· No v2 code exists yet — this is good.
  ✅ The docs patch correctly precedes the code patch. This is the right order.

---

5. Organizational Suggestions

· v1 doc quarantine
  Move v1-only docs (AI-argument-arena.md, AI-CEO-sim.md, Oracle*.md) into a v1-docs/ subdirectory, or add a prominent deprecation banner to each. A new contributor skimming the root will otherwise absorb v1 framing.
· Decision on file naming now
  The CLAUDE.md defers the arena_v1.py vs arena_v2.py decision. I recommend making it now: rename arena.py → arena_v1.py, create arena.py as a mode-switching entry point when v2 is built. This avoids a future rename scramble and signals to the filesystem itself that v1 is legacy.
· Shared vs. mode-specific tests
  When v2 tests are added, give them a separate directory (tests/v2/) or naming convention (test_v2_*.py) so CI can run both suites independently. A v1 test failure shouldn't block v2 development, and vice versa.

---

6. Repository Topics Suggestion

Add to GitHub: disagreement, multi-paradigm, epistemology, structured-debate, non-adversarial-ai, logos, argument-mapping, ensemble-methods, consensus-critique

---

This repo's primary risk is not code quality but frame contamination — the gravitational pull of adversarial defaults in AI training data. The docs patch is the right medicine. Guard it carefully.
