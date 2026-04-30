"""verb_vector.py

Generic verb-relation vector space for encoding sentences, claims,
or whole papers in a basis where geometry is verb-flow rather than
noun co-occurrence.

STATUS: in progress. See OPEN QUESTIONS at end of file.

Design:
  - basis is DECLARED, not learned. every axis is a verb-relation
    with a list of trigger phrases. no opaque embeddings.
  - parser is rule-based and inspectable: each component traces back
    to the phrase that activated it.
  - basis is pluggable: callers can extend, replace, or shadow axes.
  - degenerate inputs (pure noun-first / copula-collapsed) are FLAGGED,
    not silently zeroed. the flag is the signal.

CC0. Stdlib only.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional


@dataclass
class Axis:
    """One verb-relation axis.

    triggers       regex patterns; matches contribute to this axis.
    weight_per_hit how much each match contributes (default 1.0).
    negation_guard if True, matches inside a "not / no / n't / never"
                   window do not count.
    """
    name: str
    description: str
    triggers: List[str]
    weight_per_hit: float = 1.0
    negation_guard: bool = True


@dataclass
class Component:
    """One entry in a verb-vector: an axis and its activations."""
    axis: str
    value: float
    evidence: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        ev = "; ".join(self.evidence[:3])
        more = "" if len(self.evidence) <= 3 else f" (+{len(self.evidence)-3} more)"
        return f"{self.axis}={self.value:.2f} [{ev}{more}]"


@dataclass
class VerbVector:
    """A vector in a verb-relation space."""
    components: dict
    flags: List[str] = field(default_factory=list)
    source: str = ""
    basis: List[str] = field(default_factory=list)

    def value(self, axis_name: str) -> float:
        c = self.components.get(axis_name)
        return c.value if c else 0.0

    def as_array(self) -> List[float]:
        return [self.value(name) for name in self.basis]

    def norm(self) -> float:
        return math.sqrt(sum(v * v for v in self.as_array()))

    def explain(self) -> None:
        print(f"\n-- verb-vector --")
        src = self.source[:80] + ("..." if len(self.source) > 80 else "")
        print(f"  source: {src}")
        if self.flags:
            print(f"  flags:  {', '.join(self.flags)}")
        active = [c for c in self.components.values() if c.value > 0]
        if not active:
            print("  (no active components)")
            return
        active.sort(key=lambda c: -c.value)
        for c in active:
            print(f"  {c}")

    def __repr__(self) -> str:
        active = [(n, self.value(n)) for n in self.basis if self.value(n) > 0]
        body = ", ".join(f"{n}:{v:.1f}" for n, v in active)
        flag_str = f" flags={self.flags}" if self.flags else ""
        return f"VerbVector({body}{flag_str})"
