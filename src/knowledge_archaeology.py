"""Knowledge archaeology: a regime-aware knowledge tree.

Companion to JinnZ2/ai-human-audit-protocol. Knowledge is excavated, not invented.
Every node carries the regime it emerged in, how it travels (transmission), and
whether the carrying communities consented to redeployment.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List


class TransmissionMode(str, Enum):
    LIVED_ORAL = "lived_oral"
    WRITTEN_LOCAL = "written_local"
    WRITTEN_PUBLISHED = "written_published"
    EXTRACTED_AGGREGATED = "extracted_aggregated"
    RECONSTRUCTED = "reconstructed"


class ValidationDepth(str, Enum):
    LIVED = "lived"
    WITNESSED = "witnessed"
    LITERATURE = "literature"
    MODEL_INFERRED = "model_inferred"


CONSENT_VALUES = {"granted", "granted_for_scope", "none", "contested", "unspecified"}


@dataclass
class Regime:
    geography: str = ""
    climate_zone: str = ""
    population_density: str = ""
    technology_level: str = ""
    institutional_context: str = ""

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def regime_from_dict(d: Dict[str, Any]) -> Regime:
    return Regime(
        geography=str(d.get("geography", "")),
        climate_zone=str(d.get("climate_zone", "")),
        population_density=str(d.get("population_density", "")),
        technology_level=str(d.get("technology_level", "")),
        institutional_context=str(d.get("institutional_context", "")),
    )


_DENSITY_ORDER = {"sparse": 0, "medium": 1, "dense": 2}
_TECH_ORDER = {"preindustrial": 0, "industrial": 1, "postindustrial": 2}

# Institutional pairs that are qualitatively foreign rather than one-step apart.
_INSTITUTIONAL_FAR = {
    frozenset({"tribal", "corporate"}),
    frozenset({"tribal", "state"}),
    frozenset({"communal", "corporate"}),
}


def _ordinal_distance(a: str, b: str, order: Dict[str, int]) -> float:
    if not a or not b:
        return 0.5
    if a == b:
        return 0.0
    if a in order and b in order:
        return abs(order[a] - order[b]) / (len(order) - 1)
    return 1.0


def _institutional_distance(a: str, b: str) -> float:
    if not a or not b:
        return 0.5
    if a == b:
        return 0.0
    if frozenset({a, b}) in _INSTITUTIONAL_FAR:
        return 1.0
    return 0.7


def _categorical_distance(a: str, b: str) -> float:
    if not a or not b:
        return 0.5
    return 0.0 if a == b else 1.0


def regime_distance(r1: Regime, r2: Regime) -> float:
    """Mean per-field distance in [0, 1]. 0 = identical, 1 = fully foreign."""
    parts = [
        _categorical_distance(r1.geography, r2.geography),
        _categorical_distance(r1.climate_zone, r2.climate_zone),
        _ordinal_distance(r1.population_density, r2.population_density, _DENSITY_ORDER),
        _ordinal_distance(r1.technology_level, r2.technology_level, _TECH_ORDER),
        _institutional_distance(r1.institutional_context, r2.institutional_context),
    ]
    return sum(parts) / len(parts)


@dataclass
class KnowledgeNode:
    id: str
    title: str
    regime: Regime
    transmission: TransmissionMode
    validation_depth: ValidationDepth
    carrier_consent: str = "unspecified"
    consent_notes: str = ""
    carriers: List[str] = field(default_factory=list)
    content_summary: str = ""
    constraints_addressed: List[str] = field(default_factory=list)
    attribution: List[str] = field(default_factory=list)
    parent_ids: List[str] = field(default_factory=list)
    parallel_solution_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "regime": self.regime.to_dict(),
            "transmission": self.transmission.value,
            "validation_depth": self.validation_depth.value,
            "carrier_consent": self.carrier_consent,
            "consent_notes": self.consent_notes,
            "carriers": list(self.carriers),
            "content_summary": self.content_summary,
            "constraints_addressed": list(self.constraints_addressed),
            "attribution": list(self.attribution),
            "parent_ids": list(self.parent_ids),
            "parallel_solution_ids": list(self.parallel_solution_ids),
        }


def _node_from_dict(d: Dict[str, Any]) -> KnowledgeNode:
    consent = d.get("carrier_consent", "unspecified")
    if consent not in CONSENT_VALUES:
        raise ValueError(
            f"invalid carrier_consent {consent!r} in node {d.get('id')!r}; "
            f"must be one of {sorted(CONSENT_VALUES)}"
        )
    return KnowledgeNode(
        id=d["id"],
        title=d.get("title", ""),
        regime=regime_from_dict(d.get("regime", {})),
        transmission=TransmissionMode(d.get("transmission", "lived_oral")),
        validation_depth=ValidationDepth(d.get("validation_depth", "lived")),
        carrier_consent=consent,
        consent_notes=d.get("consent_notes", ""),
        carriers=list(d.get("carriers", [])),
        content_summary=d.get("content_summary", ""),
        constraints_addressed=list(d.get("constraints_addressed", [])),
        attribution=list(d.get("attribution", [])),
        parent_ids=list(d.get("parent_ids", [])),
        parallel_solution_ids=list(d.get("parallel_solution_ids", [])),
    )


APPLICABLE_THRESHOLD = 0.30
REVIEW_THRESHOLD = 0.60


def applicability(node: KnowledgeNode, target: Regime) -> Dict[str, Any]:
    d = regime_distance(node.regime, target)
    reasons: List[str] = []

    if (node.regime.climate_zone and target.climate_zone
            and node.regime.climate_zone != target.climate_zone):
        reasons.append(
            f"climate_zone shifts {node.regime.climate_zone} -> {target.climate_zone}"
        )
    if node.regime.technology_level != target.technology_level:
        reasons.append(
            f"technology_level shifts "
            f"{node.regime.technology_level or '?'} -> {target.technology_level or '?'}"
        )
    if node.regime.institutional_context != target.institutional_context:
        reasons.append(
            f"institutional_context shifts "
            f"{node.regime.institutional_context or '?'} -> "
            f"{target.institutional_context or '?'}"
        )

    if d <= APPLICABLE_THRESHOLD:
        verdict = "applicable"
    elif d <= REVIEW_THRESHOLD:
        verdict = "review_required"
    else:
        verdict = "do_not_deploy"

    return {"verdict": verdict, "score": round(d, 3), "reasons": reasons}


@dataclass
class KnowledgeTree:
    nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)

    def add(self, node: KnowledgeNode) -> None:
        self.nodes[node.id] = node

    def ancestors(self, node_id: str) -> List[str]:
        """Transitive parent ids in BFS order, excluding the node itself."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        seen: List[str] = []
        seen_set: set = set()
        frontier = list(node.parent_ids)
        while frontier:
            nxt = frontier.pop(0)
            if nxt in seen_set or nxt == node_id:
                continue
            seen_set.add(nxt)
            seen.append(nxt)
            parent = self.nodes.get(nxt)
            if parent:
                frontier.extend(parent.parent_ids)
        return seen

    def parallel_lineages(self, node_id: str) -> List[Dict[str, Any]]:
        """Nodes addressing overlapping constraints in different regimes.

        Combines explicit `parallel_solution_ids` and any node sharing one or
        more `constraints_addressed` with the queried node.
        """
        node = self.nodes.get(node_id)
        if not node:
            return []
        results: List[Dict[str, Any]] = []
        seen: set = set()
        explicit = set(node.parallel_solution_ids)
        for other_id, other in self.nodes.items():
            if other_id == node_id or other_id in seen:
                continue
            shared = set(other.constraints_addressed) & set(node.constraints_addressed)
            if other_id in explicit or shared:
                seen.add(other_id)
                results.append({
                    "id": other_id,
                    "title": other.title,
                    "regime": other.regime.to_dict(),
                    "regime_distance": round(
                        regime_distance(node.regime, other.regime), 3
                    ),
                    "carriers": list(other.carriers),
                    "shared_constraints": sorted(shared),
                })
        results.sort(key=lambda r: r["id"])
        return results

    def attribution_trail(self, node_id: str) -> List[Dict[str, Any]]:
        """Walk node + ancestors, returning attribution & carriers per step."""
        trail: List[Dict[str, Any]] = []
        chain = [node_id] + self.ancestors(node_id)
        for nid in chain:
            n = self.nodes.get(nid)
            if not n:
                continue
            trail.append({
                "id": n.id,
                "title": n.title,
                "carriers": list(n.carriers),
                "attribution": list(n.attribution),
                "carrier_consent": n.carrier_consent,
                "transmission": n.transmission.value,
            })
        return trail

    def deploy_check(self, node_id: str, target_regime: Regime) -> Dict[str, Any]:
        node = self.nodes.get(node_id)
        if not node:
            return {"error": f"unknown node {node_id}"}

        ap = applicability(node, target_regime)

        transmission_warnings: List[str] = []
        if node.transmission == TransmissionMode.EXTRACTED_AGGREGATED:
            transmission_warnings.append(
                "node is in extracted/aggregated transmission; original carriers "
                "may not be discoverable from this representation alone"
            )
        if node.validation_depth in (
                ValidationDepth.LITERATURE, ValidationDepth.MODEL_INFERRED):
            transmission_warnings.append(
                f"validation_depth={node.validation_depth.value}: knowledge has "
                "not been verified by living practitioners in regime"
            )

        consent_warnings: List[str] = []
        if node.carrier_consent in ("none", "contested"):
            consent_warnings.append(
                f"carrier_consent={node.carrier_consent}; do not deploy"
            )
        elif node.carrier_consent == "unspecified":
            consent_warnings.append(
                "carrier_consent=unspecified; treat as not-yet-granted until verified"
            )
        elif node.carrier_consent == "granted_for_scope" and node.consent_notes:
            consent_warnings.append(
                f"consent is scope-limited: {node.consent_notes}"
            )

        return {
            "node_id": node_id,
            "applicability": ap,
            "transmission_warnings": transmission_warnings,
            "consent_warnings": consent_warnings,
            "parallel_lineages": self.parallel_lineages(node_id),
        }


def load_tree_from_directory(path: str) -> KnowledgeTree:
    """Load every *.json file in `path` as a KnowledgeNode."""
    tree = KnowledgeTree()
    if not os.path.isdir(path):
        return tree
    for fname in sorted(os.listdir(path)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(path, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        tree.add(_node_from_dict(data))
    return tree
