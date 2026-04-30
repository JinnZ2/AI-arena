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


class VerbSpace:
    """The space defined by a list of axes. Compiles regexes once, then
    encodes input strings into VerbVectors against that fixed basis."""

    _NEGATION_WINDOW = 30  # chars before a match to scan for negation
    _NEGATIONS = (" not ", "n't ", " no ", " never ",
                  "do not", "does not", "did not", "cannot", "can't")

    def __init__(self, axes: Iterable[Axis]):
        self.axes: List[Axis] = list(axes)
        self._compile()

    def _compile(self) -> None:
        self._compiled: List = []
        for ax in self.axes:
            patterns = [re.compile(t, re.IGNORECASE) for t in ax.triggers]
            self._compiled.append((ax, patterns))
        self.basis = [ax.name for ax in self.axes]

    def add_axis(self, axis: Axis) -> None:
        self.axes.append(axis)
        self._compile()

    @staticmethod
    def _is_negated(text_lower: str, match_start: int) -> bool:
        window_start = max(0, match_start - VerbSpace._NEGATION_WINDOW)
        window = text_lower[window_start:match_start]
        return any(neg in window for neg in VerbSpace._NEGATIONS)

    def _check_degeneracy(self, text: str) -> List[str]:
        """Flag noun-first / copula-collapsed sentences. The flag is the
        signal: a downstream consumer needs to know the encoding is lossy.
        """
        flags: List[str] = []
        t = text.strip().lower()

        copula_only = re.match(
            r"^(the |a |an |this |that )?[\w\s]+?\b"
            r"(is|are|was|were|be|been|being)\b\s+[\w\s,]+?\.?$",
            t,
        )
        content_verb = re.search(
            r"\b(flow|carry|carries|carried|bind|bound|switch|recirculate|"
            r"amplif|decorrelate|couple|condition|derive|reframe|move|"
            r"send|receive|push|pull|emit|absorb|drive|trigger|cascade|"
            r"propagate|transmit|mediate|cause|produce|generate|disrupt|"
            r"loop|reach|cross|exceed|fall|rise|grow|shrink|fold|unfold|"
            r"shift|change|alter|modulate|gate|filter|select|exchange|"
            r"share|convert|translate|map|encode|decode|attract|repel)\b",
            t,
        )
        if copula_only and not content_verb:
            flags.append("COPULA_COLLAPSE")

        nominalizations = len(re.findall(
            r"\b\w+(?:tion|ment|ness|ity|ism|ance|ence)\b", t,
        ))
        verbs_found = len(re.findall(r"\b\w+(?:s|ed|ing)\b", t))
        if nominalizations >= 3 and nominalizations >= verbs_found:
            flags.append("NOUN_FIRST_DEGENERATE")

        if not content_verb and not copula_only:
            flags.append("NO_RELATION_DETECTED")

        return flags

    def encode(self, text: str, source_label: Optional[str] = None) -> VerbVector:
        """Encode a sentence or short claim into a verb-vector. Each axis
        sums weight_per_hit per non-negated trigger, capped at 5.0 to
        prevent a single repeated phrase from dominating.
        """
        text_lower = text.lower()
        components = {ax.name: Component(axis=ax.name, value=0.0)
                      for ax in self.axes}

        for ax, patterns in self._compiled:
            comp = components[ax.name]
            for pat in patterns:
                for m in pat.finditer(text_lower):
                    if ax.negation_guard and self._is_negated(text_lower, m.start()):
                        continue
                    comp.value = min(5.0, comp.value + ax.weight_per_hit)
                    snippet = text[max(0, m.start() - 20): m.end() + 20].strip()
                    comp.evidence.append(f"...{snippet}...")

        return VerbVector(
            components=components,
            flags=self._check_degeneracy(text),
            source=source_label or text,
            basis=list(self.basis),
        )

    def encode_paper(self, paper: dict) -> VerbVector:
        """Encode a structured paper-claim dict. Concatenates title,
        abstract, claims, notes and runs encode().
        """
        parts: List[str] = []
        for k in ("title", "abstract"):
            if paper.get(k):
                parts.append(paper[k])
        for k in ("claims", "notes"):
            if paper.get(k):
                parts.extend(paper[k])
        return self.encode("  ".join(parts),
                           source_label=paper.get("title", "untitled"))
