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
