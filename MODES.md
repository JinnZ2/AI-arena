# MODES.md

How to decide whether to use AI-arena in **v1 (Adversarial)** or
**v2 (Exploratory)** mode.

> v2 is the documented intent. v1 is what runs in `arena.py` today.
> See `README.md` for the full philosophy split.

---

## Quick selector

| Question shape                                | Mode |
|-----------------------------------------------|------|
| Bounded predictive, verifiable ground truth   | v1   |
| Multi-paradigm sensing, partial truths        | v2   |
| Single-paradigm reasoners, shared substrate   | v1   |
| Substrate-isolated reasoners                  | v2   |
| Optimization with one clear metric            | v1   |
| Exploration where the metric isn't fixed yet  | v2   |

When in doubt: **v2**. v1 is a special case of v2 — single-paradigm
arenas reduce to predictive competition naturally — but v2 is not a
special case of v1.

---

## Why this distinction matters

The repository's two modes serve different question shapes, and
conflating them produces bad outcomes in both directions:

- Running **v1** (zero-sum trust cannibalization) on an exploratory
  multi-paradigm problem destroys the cross-paradigm signal you
  wanted to harvest. Paradigms that were catching different real
  slices of the territory get punished for not agreeing.
- Running **v2** (paradigm-purchase records, no annihilation) on a
  bounded predictive problem with verifiable ground truth wastes
  the discipline that adversarial scoring provides. When there *is*
  a single correct answer and an Oracle can verify it, the
  exploratory mode's refusal to declare winners costs you accuracy.

The mode is a function of the question, not a preference.

---

## How each mode handles the LOGOS primitives

| Primitive   | v1 behavior                                      | v2 behavior                                                                 |
|-------------|--------------------------------------------------|-----------------------------------------------------------------------------|
| CLAIM       | Bounded prediction; competes for trust           | Bounded prediction; declares paradigm slice                                 |
| ATTACK      | Causal-break / missing-variable hit on a rival   | Same diagnostic surface, but tagged as "what my paradigm sees, theirs missed" |
| REFINE      | Costly concession; lowers confidence             | Information event; updates both paradigms' purchase records                 |
| RESOLUTION  | Oracle votes; trust is reallocated zero-sum      | Territory map; records which paradigm carried which slice                   |

---

## Status note

v1 is implemented (`arena.py`). v2 is currently a behavioral pattern,
not code — a future patch will introduce the v2 module (either as
`arena_v2.py`, or by renaming `arena.py` → `arena_v1.py` and making
v2 the new `arena.py`; that structural decision is deferred to the
code patch).

Until v2 lands in code, "running in v2" means humans applying the
v2 discipline to v1's outputs:

- Treat REFINE as information, not loss
- Don't concentrate trust in single winners
- Record per-paradigm purchase across domains rather than maintaining
  a single trust pool
- Read the Oracle's verdict as one paradigm's slice, not the final word

This file will be updated when v2 is implemented; the selector table
above is the durable interface.
