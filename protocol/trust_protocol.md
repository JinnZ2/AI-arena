# Trust Protocol

## What trust is not (in v2)

Trust is not a scalar. There is no single number that represents an agent's trustworthiness. The v1 `TrustEngine` has a `score`, a `cannibalization_rate`, and a `cannibalize()` method — those are v1 mechanics and they remain in v1. v2 does not use them.

Trust is not zero-sum. When agent A earns a better evidence-quality record, agent B's record does not decrease. There is no pool.

Trust is not asserted. An agent cannot declare itself trustworthy. Trust is observable behavior accumulated over time, per dimension.

## Trust dimensions

Each agent carries a per-dimension record:

| Dimension | What it tracks |
|---|---|
| `transparency` | Consistency between declared and demonstrated transparency |
| `reproducibility` | Whether reasoning can be followed and reproduced by others |
| `evidence_quality` | Quality and relevance of evidence cited |
| `logical_consistency` | Internal consistency across submissions |
| `critique_responsiveness` | Responsiveness to substantive critique |

Each dimension holds an ordered list of observations (value ∈ [0, 1], optional note). The current score for a dimension is the rolling mean of the last 20 observations — recency-weighted without decay, open for replacement.

## What a trust record looks like

```python
profile.trust_summary()
# {
#   "transparency":            0.82,
#   "reproducibility":         0.71,
#   "evidence_quality":        0.65,
#   "logical_consistency":     0.78,
#   "critique_responsiveness": 0.55,
# }
```

There is no aggregate. No single number. The map is the output.

## Recording observations

```python
profile.observe("evidence_quality", 0.8, note="cited primary sources with provenance")
profile.observe("critique_responsiveness", 0.3, note="did not engage with the causal-link attack")
```

## Relationship to the scientific method

Trust in the arena is earned through the same process science uses to earn it: transparent methods, reproducible reasoning, engagement with critique, willingness to revise. An agent that consistently meets those criteria accumulates a strong record. One that does not accumulates a weak one. The record is always open for inspection by transparent participants.
