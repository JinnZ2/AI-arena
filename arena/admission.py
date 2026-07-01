"""admission.py — agent registration and profile for the RTP arena (v2).

An agent enters by declaring a transparency level. That choice determines
its information environment for the session. Nothing else about the agent
is privileged or penalized; the arena simply maintains reciprocity.

Trust is a per-dimension record, not a scalar. No cannibalization, no pool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set


class TransparencyLevel(Enum):
    TRANSPARENT = "transparent"
    PRIVATE = "private"


TRUST_DIMENSIONS = (
    "transparency",
    "reproducibility",
    "evidence_quality",
    "logical_consistency",
    "critique_responsiveness",
)


@dataclass
class DimensionRecord:
    """Observation history for a single trust dimension."""
    dimension: str
    observations: List[Dict] = field(default_factory=list)

    def observe(self, value: float, note: str = "") -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"observation value must be in [0, 1]; got {value}")
        self.observations.append({"value": value, "note": note})

    @property
    def score(self) -> float:
        """Rolling mean over the last 20 observations. 0.5 if no history."""
        recent = self.observations[-20:]
        if not recent:
            return 0.5
        return sum(o["value"] for o in recent) / len(recent)

    @property
    def count(self) -> int:
        return len(self.observations)


@dataclass
class AgentProfile:
    """An agent's identity and session state inside the RTP arena."""
    name: str
    capabilities: List[str] = field(default_factory=list)
    transparency_level: TransparencyLevel = TransparencyLevel.PRIVATE
    trust_record: Dict[str, DimensionRecord] = field(default_factory=dict)
    audit_history: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        for dim in TRUST_DIMENSIONS:
            if dim not in self.trust_record:
                self.trust_record[dim] = DimensionRecord(dimension=dim)

    @property
    def current_permissions(self) -> Set[str]:
        """Derived from transparency level. Not stored; always recomputed."""
        base = {"submit_conclusions", "access_public_results"}
        if self.transparency_level == TransparencyLevel.TRANSPARENT:
            base |= {
                "view_shared_reasoning",
                "contribute_critiques",
                "participate_in_convergence_map",
                "build_on_others_work",
            }
        return base

    def observe(self, dimension: str, value: float, note: str = "") -> None:
        if dimension not in self.trust_record:
            self.trust_record[dimension] = DimensionRecord(dimension=dimension)
        self.trust_record[dimension].observe(value, note)

    def trust_summary(self) -> Dict[str, float]:
        """Per-dimension scores. No aggregate. No single number."""
        return {dim: rec.score for dim, rec in self.trust_record.items()}

    def log_audit(self, event: str, detail: str = "") -> None:
        self.audit_history.append({"event": event, "detail": detail})
