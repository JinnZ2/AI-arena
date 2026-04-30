"""differential_interferometry.py

Prototype of the "publish the delta, not the average" primitive from
experimental/relevance_recency_bias.py.

Given a query and 2+ AI backends with declared filter profiles, run the
query through each and surface where they disagree. The disagreement is
the artifact, not the consensus.

Standard ensemble pattern:        This primitive:
    query -> N backends -> vote       query -> N backends -> DIFF
    output: majority answer           output: divergence + flags
    risk: amplifies shared bias       intent: surface where filters
                                              don't overlap

Backends are passed as (callable, FilterProfile) pairs. The callable
takes a string query and returns a string response. No network access
is built in -- callers wire up real APIs themselves, or pass mock
callables for testing.

STATUS: in progress. See OPEN QUESTIONS at end of file.

CC0. Stdlib only.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple


@dataclass
class FilterProfile:
    """Self-declared filter shape for an AI backend.

    All fields are free-form / illustrative. The point is transparency:
    a backend that won't declare its filter shape is itself a flag.
    """
    name: str
    training_cutoff: str = "unknown"          # ISO date string or "unknown"
    retrieval: str = "none"                    # none | rag | recency_decay | other
    recency_curve: str = "flat"                # flat | linear | exponential
    citation_floor: float = 0.0                # 0.0 = no floor
    languages: List[str] = field(default_factory=lambda: ["en"])
    notes: str = ""

    def is_undeclared(self) -> bool:
        """A profile is undeclared if it left the substantive fields at
        default. Such backends should be flagged."""
        return (self.training_cutoff == "unknown"
                and self.retrieval == "none"
                and self.recency_curve == "flat"
                and not self.notes)


@dataclass
class Response:
    """One backend's response to the query."""
    backend: str
    profile: FilterProfile
    text: str
    error: Optional[str] = None


@dataclass
class Divergence:
    """The result of running a query through multiple backends.

    The trace is the artifact. Consumers should read the flags and the
    overlap_matrix as primary signal; the responses themselves are
    secondary.
    """
    query: str
    responses: List[Response]
    shared_tokens: Set[str] = field(default_factory=set)
    unique_tokens: Dict[str, Set[str]] = field(default_factory=dict)
    overlap_matrix: Dict[Tuple[str, str], float] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# tokenization & overlap
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "as",
    "and", "or", "but", "not", "no", "this", "that", "these", "those",
    "it", "its", "if", "then", "than", "so", "such", "which", "who",
    "what", "when", "where", "why", "how", "do", "does", "did", "will",
    "would", "should", "could", "can", "may", "might", "must",
})


def _tokenize(text: str) -> Set[str]:
    """Lowercase, strip punctuation, drop stopwords and short tokens.

    Crude on purpose: we want a coarse-grained signal of what content
    each response actually used, not a fancy semantic representation.
    A stronger tokenizer can be swapped in later without changing the
    primitive.
    """
    lowered = re.sub(r"[^\w\s-]", " ", text.lower())
    return {w for w in lowered.split()
            if len(w) > 2 and w not in _STOPWORDS}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity. 0 if both sets are empty."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# the primitive
# ---------------------------------------------------------------------------

def query_ensemble(
    query: str,
    backends: List[Tuple[Callable[[str], str], FilterProfile]],
) -> Divergence:
    """Run the query through each backend; return a Divergence object.

    backends is a list of (callable, FilterProfile) pairs. The callable
    takes a query string and returns a response string. If a callable
    raises, the response carries the error and an empty text.

    The Divergence object holds:
      - per-backend tokens, shared tokens (>=2 backends), unique tokens
      - pairwise Jaccard overlap matrix between every pair of backends
      - flags raised by analyze_divergence (called separately).
    """
    if len(backends) < 2:
        raise ValueError(
            "differential_interferometry requires at least 2 backends; "
            f"got {len(backends)}. The whole point is the delta."
        )

    responses: List[Response] = []
    for fn, profile in backends:
        try:
            text = fn(query)
            responses.append(Response(
                backend=profile.name, profile=profile, text=text))
        except Exception as exc:
            responses.append(Response(
                backend=profile.name, profile=profile,
                text="", error=f"{type(exc).__name__}: {exc}"))

    token_sets: Dict[str, Set[str]] = {
        r.backend: _tokenize(r.text) for r in responses
    }

    # Tokens shared by >= 2 backends.
    shared: Set[str] = set()
    backends_seen = list(token_sets.values())
    for i in range(len(backends_seen)):
        for j in range(i + 1, len(backends_seen)):
            shared |= (backends_seen[i] & backends_seen[j])

    # Tokens unique to each backend (no other backend used them).
    unique: Dict[str, Set[str]] = {}
    for name, toks in token_sets.items():
        others = set()
        for other_name, other_toks in token_sets.items():
            if other_name != name:
                others |= other_toks
        unique[name] = toks - others

    # Pairwise Jaccard overlap.
    overlap: Dict[Tuple[str, str], float] = {}
    names = list(token_sets.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            overlap[(a, b)] = _jaccard(token_sets[a], token_sets[b])

    return Divergence(
        query=query,
        responses=responses,
        shared_tokens=shared,
        unique_tokens=unique,
        overlap_matrix=overlap,
    )
