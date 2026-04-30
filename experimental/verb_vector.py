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


# ---------------------------------------------------------------------------
# distance / similarity
# ---------------------------------------------------------------------------

def cosine(a: VerbVector, b: VerbVector) -> float:
    """Cosine similarity in the shared basis. 0 if either vector is null."""
    if a.basis != b.basis:
        common = sorted(set(a.basis) | set(b.basis))
        av = [a.value(n) for n in common]
        bv = [b.value(n) for n in common]
    else:
        av = a.as_array()
        bv = b.as_array()
    dot = sum(x * y for x, y in zip(av, bv))
    na = math.sqrt(sum(x * x for x in av))
    nb = math.sqrt(sum(y * y for y in bv))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def distance_matrix(vectors: List[VerbVector]) -> List[List[float]]:
    """Pairwise cosine similarity matrix. Diagonal is 1.0."""
    n = len(vectors)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            m[i][j] = cosine(vectors[i], vectors[j])
    return m


def print_matrix(vectors: List[VerbVector]) -> None:
    labels = [v.source[:24] for v in vectors]
    width = max(len(label) for label in labels)
    print()
    print(" " * width + "  " + "  ".join(f"{i:>5d}" for i in range(len(vectors))))
    m = distance_matrix(vectors)
    for i, row in enumerate(m):
        print(f"{labels[i]:<{width}}  " + "  ".join(f"{v:>5.2f}" for v in row))
    print()
    for i, label in enumerate(labels):
        print(f"  {i}: {label}")


# ---------------------------------------------------------------------------
# default basis: 12 verb-relation axes
# ---------------------------------------------------------------------------

DEFAULT_AXES = [
    Axis(
        name="flows_into",
        description="substrate or signal moves into a region/state",
        triggers=[
            r"\bflow(s|ed|ing)?\s+(into|through|toward|across|down|up)\b",
            r"\bcarr(y|ies|ied)\b",
            r"\bmove(s|d|ment)?\s+(into|through|toward)\b",
            r"\btransport(s|ed|ing)?\b",
            r"\bpropagat(e|es|ed|ing|ion)\b",
            r"\bdiffus(e|es|ed|ion)\b",
            r"\bconduct(s|ed|ing|ion)?\b",
            r"\bdrain(s|ed|ing)?\s+(into|to)\b",
            r"\bdischarg(e|es|ed)\s+(into|to)\b",
        ],
    ),
    Axis(
        name="binds_to",
        description="entity attaches to / occupies a site",
        triggers=[
            r"\bbind(s|ing|ed)?\s+(to|with|at)\b",
            r"\battach(es|ed|ing)?\s+(to)\b",
            r"\boccup(y|ies|ied)\b",
            r"\bdock(s|ed|ing)?\b",
            r"\bcoordinat(e|es|ed)\s+(to|with)\b",
            r"\bligand\b",
            r"\breceptor\b",
            r"\bbinding site\b",
        ],
    ),
    Axis(
        name="mode_switches",
        description="discrete state change triggered by a condition",
        triggers=[
            r"\bmode[-\s]?switch\b",
            r"\bstate change\b",
            r"\bphase[-\s]?(transition|shift)\b",
            r"\bswitch(es|ed|ing)?\s+(between|to|from)\b",
            r"\btoggl(e|es|ed)\b",
            r"\ballosteric\b",
            r"\bgat(e|es|ed|ing)\b",
            r"\bbistabl(e|ity)\b",
        ],
    ),
    Axis(
        name="recirculates",
        description="signal loops back through the same graph or cluster",
        triggers=[
            r"\brecirculat(e|es|ed|ion)\b",
            r"\bloop(s|ed|ing)?\s+(back|through)\b",
            r"\bfeedback\b",
            r"\becho chamber\b",
            r"\bhomophil(y|ous)\b",
            r"\bcluster(ed|ing)\b",
            r"\bself[-\s]reinforc(e|ing|ement)\b",
            r"\breverberat(e|ion)\b",
        ],
    ),
    Axis(
        name="amplifies",
        description="small input produces large output",
        triggers=[
            r"\bamplif(y|ies|ied|ication)\b",
            r"\bcascad(e|es|ed|ing)\b",
            r"\bnonlinear\b",
            r"\bmagnif(y|ies|ied)\b",
            r"\bwhisper.{0,30}hurricane\b",
            r"\blow[-\s]dose.{0,30}(effect|active|response)\b",
            r"\bnon[-\s]monotonic\b",
            r"\bgain\b",
        ],
    ),
    Axis(
        name="decorrelates",
        description="breaks correlation in downstream signal or population",
        triggers=[
            r"\bdecorrelat(e|es|ed|ion|ing)\b",
            r"\bdiversif(y|ies|ied|ication)\b",
            r"\bbreak(s|ing)?\s+correlation\b",
            r"\bindependent\s+(signal|sample|observation)\b",
            r"\borthogonal\b",
            r"\bseparat(e|es|ed)\s+(spatially|radially|by)\b",
            r"\bdistinguish(es|ed|ing)?\b",
            r"\bspin[-\s](separation|hall)\b",
        ],
    ),
    Axis(
        name="phase_shifts_at",
        description="behavior changes when a parameter crosses a threshold",
        triggers=[
            r"\bthreshold\b",
            r"\bcritical\s+(point|value|temperature|concentration)\b",
            r"\bcross(es|ed|ing)\s+\w+",
            r"\bonset\s+of\b",
            r"\babove\s+\d",
            r"\bbelow\s+\d",
            r"\btransition(s|ed)?\s+(at|near|when)\b",
            r"\bIC\d{0,2}\b",
            r"\btipping\s+point\b",
        ],
    ),
    Axis(
        name="couples_to",
        description="cross-domain energy / information exchange",
        triggers=[
            r"\bcoupl(e|es|ed|ing)\b",
            r"\binteract(s|ed|ing|ion)\s+(with|between)\b",
            r"\bcross[-\s](domain|layer|scale|species)\b",
            r"\bsynerg(y|istic|ize)\b",
            r"\bcombined\s+effect\b",
            r"\bfeed(s|ing)?\s+into\b",
            r"\bentangl(e|ed|ement)\b",
            r"\bcorrelat(e|es|ed)\s+with\b",
        ],
    ),
    Axis(
        name="conditions_on",
        description="claim is bounded by an explicit scope or regime",
        triggers=[
            r"\bin\s+the\s+(regime|case|condition|context)\s+(where|of)\b",
            r"\bonly\s+(when|if|under)\b",
            r"\bunder\s+\w+\s+conditions?\b",
            r"\bso long as\b",
            r"\bas long as\b",
            r"\bprovided\s+that\b",
            r"\bwithin\s+the\s+(range|window|regime)\b",
            r"\bduring\s+(the|a)?\s*\w+\s+(window|period|phase)\b",
            r"\bcritical\s+window\b",
        ],
    ),
    Axis(
        name="derives_from",
        description="claim is about a rate, derivative, or trajectory",
        triggers=[
            r"\brate\s+of\b",
            r"\baccelerat(e|es|ed|ing|ion)\b",
            r"\bdeceler(ate|ating|ation)\b",
            r"\bvelocity\b",
            r"\btrajectory\b",
            r"\bderivative\b",
            r"\bchanging\s+faster\b",
            r"\bgrowth\s+rate\b",
            r"\btime[-\s]derivative\b",
            r"\bdrift(s|ing|ed)?\b",
        ],
    ),
    Axis(
        name="carries_for",
        description="transmission across time, generation, or distance",
        triggers=[
            r"\btransgenerational\b",
            r"\bmulti[-\s]generational\b",
            r"\binherit(s|ed|ance)\b",
            r"\bepigenetic\b",
            r"\bpersist(s|ed|ent|ence)\b",
            r"\blegacy\b",
            r"\btransmit(s|ted|ting|ssion)?\b",
            r"\bpropagate.{0,15}(through|across)\s+(generation|time)\b",
        ],
    ),
    Axis(
        name="reframes_as",
        description="basis change: same entity viewed from different frame",
        triggers=[
            r"\breframe(s|d|ing)?\s+as\b",
            r"\bnot\s+(just|only)\s+\w+.{0,20}but\s+(also)?\b",
            r"\b(also|equivalently)\s+(viewed|seen|understood)\s+as\b",
            r"\binstead\s+of\s+\w+.{0,20}\b",
            r"\b(rather|more accurately)\s+(than|as)\b",
            r"\bdual\s+role\b",
            r"\bligand.{0,30}(not|rather than).{0,30}substrate\b",
            r"\bsubstrate.{0,30}(not|rather than).{0,30}(only|just)\b",
        ],
    ),
]


def default_space() -> VerbSpace:
    return VerbSpace(DEFAULT_AXES)
