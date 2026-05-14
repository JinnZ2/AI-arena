# When to use v1 (adversarial) vs v2 (exploratory)

## Current state

v1 is implemented. v2 is documented but not yet coded.

If your question fits v2's profile, you can either:

- Wait for the v2 code patch (forthcoming)
- Apply v2's principles manually when running v1, by ignoring trust
  cannibalization in the output and treating disagreement as the
  signal rather than as a contest to resolve
- Fork and implement v2 yourself

## Quick rule

Use **v2** unless the question has all three of these properties:

1. There is a single verifiable ground truth (an Oracle exists).
2. All participating reasoners share enough substrate to compete
   on the same metric meaningfully.
3. Speed of decision matters more than coverage of paradigms.

If any of those is false, use v2.

## v1 is appropriate when

- Predictive accuracy is the only thing being measured.
- Ground truth arrives after the prediction (financial outcomes,
  operational results, supply chain events).
- All reasoners can be evaluated on the same metric without
  destroying signal.
- The decision is bounded and time-critical.

## v2 is appropriate when

- Multiple paradigms each catch a real aspect of the phenomenon.
- "Ground truth" is a structured map, not a single value.
- Reasoners have different native substrates (e.g., equations-only,
  physics-only, general-corpus).
- Exploration is the goal; the right metric isn't fixed yet.
- Disagreement is informative about paradigm-boundaries.

## What happens if you use the wrong mode

**v1 on a v2 question:** paradigms get punished for being
correct-about-different-slices. The substrate with broadest
training-data overlap wins by default. Cross-paradigm signal is
destroyed. Consensus-of-silence becomes likely.

**v2 on a v1 question:** no decision gets made. Territory maps
indefinitely. The arena fails to converge when convergence was the
actual point.

Mode selection is a first-class question. Don't default; choose.
