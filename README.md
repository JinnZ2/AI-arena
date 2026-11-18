> Read first: [READING_PROTOCOL.md](READING_PROTOCOL.md) (how to read this repo).
> Map, not prescription. Errors are data. Check it. Built for the need, revisable.

> Before reading or editing anything here, read READ_ME_THIS_WAY.md.
> Mismatches, dead ends and odd names in this repo are kept on purpose.

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

## Word-slot layer (experimental)

Note 2026-11-18, co-authored (JinnZ2 + Claude). CI (`.github/workflows/ci.yml`, Python 3.10 and 3.13) checks out both pinned siblings and fails on any skip. `experimental/word_slots.py` maps agent
claim text onto the wordslots checker in JinnZ2/formula-audit and says where two agents'
claims on the same word differ. It imports that checker; it holds no place table and no
copy of the checker's logic. Paths, commits and sha256 are pinned in
`REFERENCES/wordslots_place_table.json`; a missing checkout or a hash mismatch is
`NOT_RUN` with the reason.

| bin | what it marks |
|---|---|
| `SLOT_CONFLICT` | the same slot filled by both agents, with different fillings |
| `SLOT_GAP` | one agent fills a slot the other leaves empty (`VOID`, or `DEGRADED` when it was required) |
| `SENSE_SPLIT` | different senses of the word (safe: `PROTECTED` vs `NOT_PERILOUS`) |
| `SOURCE_SPLIT` | same filling, different source or evidential |

Two claims are paired when they use the same word (`pair_basis: WORD`) or rest on the
same source predicate of the pinned table (`pair_basis: PREDICATE`). A claimed word the
place table has no entry for ("aggressive") is looked up in formula-audit's pinned
`REFERENCES/lojban_place_structures.json`; if exactly one table entry is built on the
predicate it names (le'onmo → "hostile"), the claim is checked under that entry's slots,
and the claimed word, the entry used and the reference's mapping status (PROPOSED) are
kept beside the record.

The bins locate a difference. They do not rule on which claim holds, and no agent is
counted up, ranked or resolved. A slot every agent leaves empty produces no difference
at all, so it is passed to `experimental/shared_blind_spot.py` as correlated silence.

Fillings are taken only from a tag in the claim text, never from prose:
`[[safe x1="the bridge" x2="collapse" x3="pedestrians" sense=PROTECTED evidential=observed source_id="inspection"]]`.
The checker's `human_interest` / `ai_interest` slots are left null.

Optional transport: `to_bridge_record()` packs a report into one experiment_bridge v1.1
EB01 record (JinnZ2/geometric-to-binary-computational-bridge, pinned) and decodes it back.
Byte envelope only; the COBOL round trip is not run from here and the original copybook
generator is not used.

```sh
python experimental/word_slots.py          # demo; needs formula-audit cloned beside this repo
python -m unittest tests.test_word_slots   # table-dependent tests skip without the checkout
python tests/run_counts.py                 # whole suite; prints passed / skipped / NOT_RUN
```

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

---

## License and scope (current)

Owner-authored material in this repository is dedicated to the public domain
under **CC0 1.0 Universal**; the complete legal code is in
[LICENSE](LICENSE). This designation reaches only rights held by JinnZ2.

**Exceptions / care required.** The four `nodes/*_v1.json` records are
author-created, synthetic schema illustrations, but their named cultural
practices, carrier communities, and lineage-specific knowledge are not claimed
or relicensed; actual use requires the consent stated in each record.
`Contributors.md` links to external GitHub user-attachment images whose
licenses/ownership cannot be established from this repository; the linked
remote assets are not relicensed. No vendored source, submodule, or nested
third-party license file is tracked. [LICENSE_HISTORY.md](LICENSE_HISTORY.md)
records the prior MIT legal text, exact preserved prior scope statement, and
provenance details.

`READ_ME_THIS_WAY.md` is preserved byte-for-byte as a reading-layer record.
Its final local MIT/explicit-CC0 scope statement records the earlier licensing
layout; it does not alter the current root [LICENSE](LICENSE).
