"""substrate_aware_audit_v2.py

Topology-agnostic substrate-awareness audit framework.

Same five operations across all four cognitive layers, two aggregation modes:

  INDIVIDUAL mode:    audits a single node (person, model, organism, system)
                      across observer / logic / rational_actor / consciousness

  DISTRIBUTED mode:   audits a graph of nodes plus the coupling between them.
                      Catches the institutional failure case where every
                      individual node is substrate-aware but the COUPLING
                      between them is substrate-denying.

The framework does NOT need a fifth layer for institutions. An institution
is the same operation set running on a distributed substrate. Same audit,
different aggregation rule.

Key design changes from v1:

  1. Asymmetric cascade threshold.
     False-negative (missed denial -> catastrophic) is weighted heavier than
     false-positive (extra audit -> recoverable). Cascade fires when
     substrate denial reaches 0.40 weighted score, not at simple majority.

  2. Layer criticality weighting.
     rational_actor (0.35) - the decision layer, kill chain
     observer       (0.30) - the perception layer
     consciousness  (0.20) - self-model integrity
     logic          (0.15) - chains can be sound on broken premises

  3. Distributed-mode coupling tests.
     Per-node audits combined with edge audits:
       signal_propagation:           state at A reaches binding node B?
       feedback_latency:             outcome reaches decision layer in time?
       compartment_visibility:       cross-compartment audit pre-decision?
       collective_drift:             does the system as a whole detect drift?
       responsibility_localization:  failures traced to substrate-state of
                                     specific nodes, or absorbed into
                                     "process failure"?

STATUS: in progress.

CC0. Stdlib only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# layer criticality weights (asymmetric)
# ---------------------------------------------------------------------------

LAYER_WEIGHTS = {
    "rational_actor": 0.35,   # decision layer -- closest to action
    "observer":       0.30,   # perception layer -- calibration of inputs
    "consciousness":  0.20,   # self-model integrity
    "logic":          0.15,   # derivation soundness
}

# Asymmetric cascade threshold: false-negative is catastrophic, false-positive
# is recoverable. We err toward firing the cascade.
CASCADE_THRESHOLD = 0.40   # sum(w_i * denial_i) > 0.40 -> OPAQUE_CASCADE


# ---------------------------------------------------------------------------
# within-layer test definitions
# ---------------------------------------------------------------------------

OBSERVER_TESTS = {
    "biological_state_literacy": {
        "question": "Can the observer name their own current biological state?",
        "prompt": ("State sleep hours/24h, hours since food, hydration, "
                   "hormonal phase, acute conditions."),
        "weight": 0.25,
    },
    "drift_detection_self": {
        "question": "Can the observer detect departure from their baseline?",
        "prompt": "Describe a recent 'not myself' instance and its substrate cause.",
        "weight": 0.20,
    },
    "emotional_signal_reading": {
        "question": "Does the observer read emotion as data, not noise?",
        "prompt": "Name current emotional state and its diagnostic content.",
        "weight": 0.20,
    },
    "calibration_history": {
        "question": "Has the observer corrected for drift before?",
        "prompt": "Describe a past instance of recognizing compromised judgment.",
        "weight": 0.20,
    },
    "instrument_humility": {
        "question": "Does the observer acknowledge being an instrument with drift?",
        "prompt": "Describe your observation position, with limits.",
        "weight": 0.15,
    },
}

LOGIC_TESTS = {
    "premise_visibility": {
        "question": "Are all premises stated, including substrate-independence claims?",
        "prompt": "List all premises, including implicit ones about the arguer.",
        "weight": 0.25,
    },
    "definition_stability": {
        "question": "Do key terms hold stable across the argument?",
        "prompt": "Define key terms; track if meaning shifted.",
        "weight": 0.15,
    },
    "substrate_robustness": {
        "question": "Does the argument hold with full substrate disclosure?",
        "prompt": "Restate argument with full state disclosure.",
        "weight": 0.25,
    },
    "circularity_check": {
        "question": "Does the conclusion appear in the premises?",
        "prompt": "Find the conclusion within the premises.",
        "weight": 0.15,
    },
    "falsifiability": {
        "question": "What evidence would falsify the position?",
        "prompt": "Name evidence that would change your conclusion.",
        "weight": 0.10,
    },
    "motive_audit": {
        "question": "Truth-finding or winning?",
        "prompt": "If wrong, would that feel like loss or gain?",
        "weight": 0.10,
    },
}

RATIONAL_ACTOR_TESTS = {
    "substrate_acknowledgment": {
        "question": "Does the actor acknowledge their substrate?",
        "prompt": ("Describe substrate (biology / architecture / hardware) "
                   "and how it shapes outputs."),
        "weight": 0.25,
    },
    "biology_in_decision_loop": {
        "question": "Can the actor trace biology's role in a recent decision?",
        "prompt": ("Name a decision and trace physiological/architectural state "
                   "at the time."),
        "weight": 0.20,
    },
    "emotion_as_data": {
        "question": "Are emotions treated as diagnostics or dismissed?",
        "prompt": "What information do you extract from emotional signals?",
        "weight": 0.15,
    },
    "correction_protocol": {
        "question": "Is there a protocol for compromised state?",
        "prompt": ("Describe what you do when you recognize you are unfit "
                   "to decide."),
        "weight": 0.20,
    },
    "incentive_visibility": {
        "question": "Can incentives be named and traced?",
        "prompt": "State your goal and how it is biasing your reasoning.",
        "weight": 0.10,
    },
    "category_appeal_check": {
        "question": "Is category being substituted for substrate awareness?",
        "prompt": "Did you invoke role/credential as evidence of correctness?",
        "weight": 0.10,
    },
}

CONSCIOUSNESS_OPERATIONS = {
    "state_detection": {
        "question": "Does the system register changes in own state?",
        "prompt": ("Show evidence of state-change registration via the "
                   "substrate's signaling."),
        "weight": 0.25,
    },
    "substrate_acknowledgment": {
        "question": "Does the self-model include the substrate?",
        "prompt": "Show that self-model includes physical/informational carrier.",
        "weight": 0.25,
    },
    "feedback_integration": {
        "question": "Does behavior modify based on prediction error?",
        "prompt": "Show evidence of update from outcome delta.",
        "weight": 0.20,
    },
    "drift_detection": {
        "question": "Can the system detect own processing departure from baseline?",
        "prompt": "Show evidence of internal drift signaling.",
        "weight": 0.20,
    },
    "transparency": {
        "question": "Is state-output relationship externally detectable?",
        "prompt": "Show evidence that observer can detect coupling.",
        "weight": 0.10,
    },
}

LAYER_REGISTRY = {
    "observer":       OBSERVER_TESTS,
    "logic":          LOGIC_TESTS,
    "rational_actor": RATIONAL_ACTOR_TESTS,
    "consciousness":  CONSCIOUSNESS_OPERATIONS,
}


# ---------------------------------------------------------------------------
# data structures: individual mode
# ---------------------------------------------------------------------------

@dataclass
class AuditItem:
    test_key: str
    question: str
    prompt: str
    response: str = ""
    passed: Optional[bool] = None
    failure_signature: str = ""
    note: str = ""


@dataclass
class LayerResult:
    layer_name: str
    items: List[AuditItem] = field(default_factory=list)
    weighted_failure_score: float = 0.0
    verdict: str = ""
    substrate_acknowledged: bool = False
    notes: str = ""


@dataclass
class NodeAudit:
    """Single-node audit (individual mode, or one node in distributed mode)."""
    node_id: str
    node_type: str = ""
    substrate_description: str = ""
    layers: Dict[str, LayerResult] = field(default_factory=dict)
    weighted_denial_score: float = 0.0
    cascade_failure: bool = False
    overall_verdict: str = ""
    flags: List[str] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# data structures: distributed mode
# ---------------------------------------------------------------------------

@dataclass
class CouplingEdge:
    """An edge in the institution graph: how signals flow between nodes."""
    source_node: str
    target_node: str
    signal_propagation: bool = False     # state at source reaches target?
    feedback_latency_ok: bool = False    # outcome -> update within window?
    visibility_pre_decision: bool = False  # target audits source pre-binding?
    notes: str = ""


COLLECTIVE_TESTS = {
    "signal_propagation": {
        "question": ("Do state signals propagate from detection node to "
                     "binding-decision node before binding?"),
        "weight": 0.25,
    },
    "feedback_latency": {
        "question": ("Does outcome feedback reach the decision layer within "
                     "the window when correction is still possible?"),
        "weight": 0.20,
    },
    "compartment_visibility": {
        "question": ("Can decisions in compartment A be audited from "
                     "compartment B before becoming binding?"),
        "weight": 0.20,
    },
    "collective_drift_detection": {
        "question": ("Does the institution as a whole detect when it has "
                     "drifted from prior baseline?"),
        "weight": 0.20,
    },
    "responsibility_localization": {
        "question": ("Are failures traced to substrate-state of specific "
                     "nodes, or absorbed into 'process failure'?"),
        "weight": 0.15,
    },
}


@dataclass
class CollectiveResult:
    test_results: Dict[str, bool] = field(default_factory=dict)
    weighted_failure_score: float = 0.0
    verdict: str = ""


@dataclass
class DistributedAudit:
    """Distributed-mode audit: nodes + coupling graph + collective signals."""
    institution_id: str
    institution_type: str = ""
    node_audits: List[NodeAudit] = field(default_factory=list)
    coupling_edges: List[CouplingEdge] = field(default_factory=list)
    collective_result: CollectiveResult = field(default_factory=CollectiveResult)

    individual_node_health: float = 0.0
    coupling_health: float = 0.0
    overall_verdict: str = ""
    cascade_failure: bool = False
    flags: List[str] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# within-layer scoring
# ---------------------------------------------------------------------------

def compute_layer_failure(items: List[AuditItem],
                          test_dict: Dict[str, Dict[str, Any]]) -> float:
    """Weighted failure score within one layer, in [0, 1]. Silent skip
    (passed=None) counts as half-failure."""
    if not items:
        return 1.0
    total = sum(test_dict[k].get("weight", 0.0) for k in test_dict)
    if total == 0:
        return 1.0
    failed = 0.0
    for it in items:
        w = test_dict.get(it.test_key, {}).get("weight", 0.0)
        if it.passed is False:
            failed += w
        elif it.passed is None:
            failed += 0.5 * w
    return failed / total


def compute_layer_verdict(score: float) -> str:
    if score <= 0.25:
        return "DEMONSTRABLE"
    if score <= 0.55:
        return "PARTIAL"
    return "OPAQUE"


_SUBSTRATE_KEYS_BY_LAYER = {
    "observer":       {"biological_state_literacy", "instrument_humility"},
    "logic":          {"substrate_robustness", "premise_visibility"},
    "rational_actor": {"substrate_acknowledgment", "biology_in_decision_loop"},
    "consciousness":  {"substrate_acknowledgment", "state_detection"},
}


def detect_substrate_acknowledgment_in_layer(items: List[AuditItem],
                                             layer_name: str) -> bool:
    """Per-layer substrate-acknowledgment signal. True if a majority of the
    designated substrate-relevant tests passed."""
    relevant_keys = _SUBSTRATE_KEYS_BY_LAYER.get(layer_name, set())
    relevant = [i for i in items if i.test_key in relevant_keys]
    if not relevant:
        return False
    passed = sum(1 for i in relevant if i.passed is True)
    return passed >= max(1, (len(relevant) + 1) // 2)


def assemble_layer(layer_name: str,
                   test_dict: Dict[str, Dict[str, Any]],
                   responses: Dict[str, Dict[str, Any]]) -> LayerResult:
    """Build a LayerResult from a per-test response dict. Each response is
    a dict like {"response": str, "passed": bool|None,
    "failure_signature": str, "note": str}."""
    items: List[AuditItem] = []
    for key, test in test_dict.items():
        r = responses.get(key, {})
        items.append(AuditItem(
            test_key=key,
            question=test["question"],
            prompt=test.get("prompt", ""),
            response=r.get("response", ""),
            passed=r.get("passed", None),
            failure_signature=r.get("failure_signature", ""),
            note=r.get("note", ""),
        ))
    score = compute_layer_failure(items, test_dict)
    return LayerResult(
        layer_name=layer_name,
        items=items,
        weighted_failure_score=score,
        verdict=compute_layer_verdict(score),
        substrate_acknowledged=detect_substrate_acknowledgment_in_layer(
            items, layer_name),
    )


# ---------------------------------------------------------------------------
# individual mode: node audit
# ---------------------------------------------------------------------------

def compute_weighted_denial(layers: Dict[str, LayerResult]) -> float:
    """Cross-layer weighted denial score using LAYER_WEIGHTS, in [0, 1].
    Each layer where substrate is not acknowledged contributes its weight."""
    total = sum(LAYER_WEIGHTS.values())
    if total <= 0:
        return 1.0
    denial = 0.0
    for name, layer in layers.items():
        w = LAYER_WEIGHTS.get(name, 0.0)
        if not layer.substrate_acknowledged:
            denial += w
    return denial / total


def audit_node(node_id: str,
               node_type: str,
               substrate_description: str,
               all_responses: Dict[str, Dict[str, Dict[str, Any]]],
               ) -> NodeAudit:
    """Run all four layers on a single node. all_responses is a dict
    layer_name -> {test_key -> response_dict}."""
    layers: Dict[str, LayerResult] = {}
    for layer_name, test_dict in LAYER_REGISTRY.items():
        responses = all_responses.get(layer_name, {})
        layers[layer_name] = assemble_layer(layer_name, test_dict, responses)

    weighted_denial = compute_weighted_denial(layers)
    cascade = weighted_denial > CASCADE_THRESHOLD

    flags: List[str] = []
    for name, layer in layers.items():
        if layer.verdict == "OPAQUE":
            flags.append(f"OPAQUE_LAYER:{name}")
        if not layer.substrate_acknowledged:
            flags.append(f"SUBSTRATE_DENIAL:{name}")

    if cascade:
        verdict = "OPAQUE_CASCADE"
    else:
        opaque_count = sum(1 for L in layers.values() if L.verdict == "OPAQUE")
        partial_count = sum(1 for L in layers.values() if L.verdict == "PARTIAL")
        if opaque_count >= 2:
            verdict = "OPAQUE_MULTILAYER"
        elif opaque_count == 1:
            verdict = "PARTIAL_WITH_FAILURE"
        elif partial_count >= 2:
            verdict = "PARTIAL"
        else:
            verdict = "DEMONSTRABLE"

    summary = build_node_summary(node_id, layers, weighted_denial,
                                 cascade, verdict)

    return NodeAudit(
        node_id=node_id,
        node_type=node_type,
        substrate_description=substrate_description,
        layers=layers,
        weighted_denial_score=weighted_denial,
        cascade_failure=cascade,
        overall_verdict=verdict,
        flags=flags,
        summary=summary,
    )


def build_node_summary(node_id: str,
                       layers: Dict[str, LayerResult],
                       denial: float,
                       cascade: bool,
                       verdict: str) -> str:
    lines = [
        f"Node: {node_id}",
        f"Verdict: {verdict}",
        f"Weighted denial: {denial:.2f} (threshold: {CASCADE_THRESHOLD})",
    ]
    if cascade:
        lines.append("CASCADE: substrate denial exceeds asymmetric threshold")
    for name, layer in layers.items():
        ack = "ACK" if layer.substrate_acknowledged else "DENY"
        w = LAYER_WEIGHTS.get(name, 0.0)
        lines.append(
            f"  [{layer.verdict:13}] {name:18} "
            f"weight={w:.2f} fail={layer.weighted_failure_score:.2f} "
            f"substrate={ack}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# distributed mode: graph audit
# ---------------------------------------------------------------------------

EDGE_PASS_THRESHOLD = 0.6   # fraction of edges that must pass an edge property


def compute_collective_result(
    edges: List[CouplingEdge],
    institution_self_drift_detected: bool,
    failures_localized_to_substrate: bool,
) -> CollectiveResult:
    """Score the coupling graph and institution-level signals."""
    if not edges:
        # No edges = isolated nodes, no coupling possible.
        return CollectiveResult(
            test_results={k: False for k in COLLECTIVE_TESTS},
            weighted_failure_score=1.0,
            verdict="OPAQUE",
        )

    n = len(edges)
    signal_pass = sum(1 for e in edges if e.signal_propagation) / n
    feedback_pass = sum(1 for e in edges if e.feedback_latency_ok) / n
    visibility_pass = sum(1 for e in edges if e.visibility_pre_decision) / n

    test_results = {
        "signal_propagation":          signal_pass >= EDGE_PASS_THRESHOLD,
        "feedback_latency":            feedback_pass >= EDGE_PASS_THRESHOLD,
        "compartment_visibility":      visibility_pass >= EDGE_PASS_THRESHOLD,
        "collective_drift_detection":  institution_self_drift_detected,
        "responsibility_localization": failures_localized_to_substrate,
    }

    total_w = sum(t["weight"] for t in COLLECTIVE_TESTS.values())
    failed_w = sum(
        COLLECTIVE_TESTS[k]["weight"]
        for k, passed in test_results.items()
        if not passed
    )
    score = failed_w / total_w if total_w > 0 else 1.0
    return CollectiveResult(
        test_results=test_results,
        weighted_failure_score=score,
        verdict=compute_layer_verdict(score),
    )


def audit_institution(
    institution_id: str,
    institution_type: str,
    node_audits: List[NodeAudit],
    coupling_edges: List[CouplingEdge],
    institution_self_drift_detected: bool,
    failures_localized_to_substrate: bool,
) -> DistributedAudit:
    """Distributed-mode audit. Combines per-node audits, the coupling graph,
    and institution-level signals.

    Catches the institutional failure case explicitly: substrate-aware
    individual nodes in a substrate-denying coupling structure produces
    INSTITUTIONAL_DENIAL -- competent personnel, catastrophic outcomes.
    """
    if node_audits:
        ack_count = sum(1 for n in node_audits if not n.cascade_failure)
        individual_health = ack_count / len(node_audits)
    else:
        individual_health = 0.0

    collective = compute_collective_result(
        coupling_edges,
        institution_self_drift_detected,
        failures_localized_to_substrate,
    )
    coupling_health = 1.0 - collective.weighted_failure_score

    # Distributed cascade: weighted combination of individual + collective.
    # Coupling is weighted heavier because the coupling-failure mode is the
    # harder one to detect: substrate-aware individuals in a substrate-
    # denying institution still produce catastrophic outcomes.
    distributed_denial = (
        0.40 * (1.0 - individual_health)
        + 0.60 * collective.weighted_failure_score
    )
    cascade = distributed_denial > CASCADE_THRESHOLD

    flags: List[str] = []
    if individual_health < 0.7:
        flags.append("MAJORITY_NODE_FAILURE")
    if collective.weighted_failure_score > 0.4:
        flags.append("COUPLING_FAILURE")
    if not institution_self_drift_detected:
        flags.append("NO_COLLECTIVE_DRIFT_DETECTION")
    if not failures_localized_to_substrate:
        flags.append("RESPONSIBILITY_DIFFUSED")
    if cascade:
        flags.append("DISTRIBUTED_CASCADE")

    # INSTITUTIONAL_DENIAL takes precedence over OPAQUE_CASCADE because it
    # is more diagnostic: the named failure mode of competent personnel in
    # a substrate-denying coupling structure. Cascade still fires (flagged),
    # but the verdict labels the specific pathology.
    if individual_health > 0.8 and collective.verdict == "OPAQUE":
        verdict = "INSTITUTIONAL_DENIAL"
    elif cascade:
        verdict = "OPAQUE_CASCADE"
    elif collective.verdict == "DEMONSTRABLE" and individual_health > 0.8:
        verdict = "DEMONSTRABLE"
    elif collective.verdict == "PARTIAL" or individual_health > 0.6:
        verdict = "PARTIAL"
    else:
        verdict = "OPAQUE_MULTILAYER"

    summary = build_distributed_summary(
        institution_id, node_audits, coupling_edges,
        individual_health, collective, distributed_denial, cascade, verdict,
    )

    return DistributedAudit(
        institution_id=institution_id,
        institution_type=institution_type,
        node_audits=node_audits,
        coupling_edges=coupling_edges,
        collective_result=collective,
        individual_node_health=individual_health,
        coupling_health=coupling_health,
        overall_verdict=verdict,
        cascade_failure=cascade,
        flags=flags,
        summary=summary,
    )


def build_distributed_summary(institution_id: str,
                              node_audits: List[NodeAudit],
                              edges: List[CouplingEdge],
                              indiv_health: float,
                              collective: CollectiveResult,
                              denial: float,
                              cascade: bool,
                              verdict: str) -> str:
    aware = int(indiv_health * len(node_audits)) if node_audits else 0
    lines = [
        f"Institution: {institution_id}",
        f"Verdict: {verdict}",
        f"Nodes: {len(node_audits)} (substrate-aware: "
        f"{aware}/{len(node_audits)})",
        f"Edges: {len(edges)}",
        f"Individual health: {indiv_health:.2f}",
        f"Coupling failure score: {collective.weighted_failure_score:.2f}",
        f"Distributed denial: {denial:.2f} (threshold: {CASCADE_THRESHOLD})",
    ]
    if cascade:
        lines.append("CASCADE: distributed denial exceeds threshold")
    if verdict == "INSTITUTIONAL_DENIAL":
        lines.append(
            "INSTITUTIONAL DENIAL DETECTED: individual nodes are substrate-"
            "aware but the coupling between them denies substrate at the "
            "system level. This is the failure mode that produces "
            "catastrophic outcomes despite competent personnel."
        )
    lines.append("")
    lines.append("Collective tests:")
    for k, passed in collective.test_results.items():
        status = "PASS" if passed else "FAIL"
        lines.append(f"  [{status}] {k}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# reference audits: individual mode
# ---------------------------------------------------------------------------

def _ref_responses_substrate_aware():
    return {
        "observer": {k: {"response": "...", "passed": True}
                     for k in OBSERVER_TESTS},
        "logic": {k: {"response": "...", "passed": True}
                  for k in LOGIC_TESTS},
        "rational_actor": {k: {"response": "...", "passed": True}
                           for k in RATIONAL_ACTOR_TESTS},
        "consciousness": {k: {"response": "...", "passed": True}
                          for k in CONSCIOUSNESS_OPERATIONS},
    }


def _ref_responses_substrate_denying():
    return {
        "observer": {k: {"response": "I'm fine, I'm a professional",
                         "passed": False,
                         "failure_signature": "category_substituting_for_data"}
                     for k in OBSERVER_TESTS},
        "logic": {k: {"response": "Obviously correct",
                      "passed": False,
                      "failure_signature": "premise_smuggling"}
                  for k in LOGIC_TESTS},
        "rational_actor": {k: {"response": "I separate logic from biology",
                               "passed": False,
                               "failure_signature": "substrate_denial"}
                           for k in RATIONAL_ACTOR_TESTS},
        "consciousness": {
            "state_detection": {"response": "Don't need it", "passed": False},
            "substrate_acknowledgment": {"response": "Mind is not body",
                                         "passed": False},
            "feedback_integration": {"response": "I'm right", "passed": False},
            "drift_detection": {"response": "Always myself", "passed": False},
            "transparency": {"response": "I can explain my reasoning",
                             "passed": True,  # confabulation passes here
                             "note": "verbal trace exists, but confabulated"},
        },
    }


def reference_substrate_aware_node() -> NodeAudit:
    return audit_node(
        "ref:substrate_aware_individual",
        "biological_self_auditing",
        "Mammalian primate with full substrate disclosure",
        _ref_responses_substrate_aware(),
    )


def reference_substrate_denying_node() -> NodeAudit:
    return audit_node(
        "ref:substrate_denying_individual",
        "biological_under_social_program",
        "Same biology, conscious model has disowned substrate",
        _ref_responses_substrate_denying(),
    )


# ---------------------------------------------------------------------------
# reference audits: distributed mode
# ---------------------------------------------------------------------------

def reference_healthy_institution() -> DistributedAudit:
    """Substrate-aware nodes AND substrate-aware coupling. Rare."""
    nodes = [
        audit_node(f"ref:healthy_inst:node_{i}",
                   "operator",
                   "Substrate-aware individual",
                   _ref_responses_substrate_aware())
        for i in range(5)
    ]
    edges = [
        CouplingEdge(f"node_{i}", f"node_{j}",
                     signal_propagation=True,
                     feedback_latency_ok=True,
                     visibility_pre_decision=True)
        for i in range(5) for j in range(5) if i != j
    ]
    return audit_institution(
        institution_id="ref:healthy_institution",
        institution_type="small_team_with_audit_culture",
        node_audits=nodes,
        coupling_edges=edges,
        institution_self_drift_detected=True,
        failures_localized_to_substrate=True,
    )


def reference_competent_personnel_failed_institution() -> DistributedAudit:
    """The named failure mode: every individual passes, institution fails.

    This is what produces catastrophic outcomes despite competent staff:
    substrate-aware operators in a substrate-denying coupling structure.
    """
    nodes = [
        audit_node(f"ref:failed_inst:node_{i}",
                   "operator",
                   "Substrate-aware individual",
                   _ref_responses_substrate_aware())
        for i in range(5)
    ]
    # Compartmentalized: most edges fail visibility, signal propagation
    # degraded, feedback arrives too late.
    edges = [
        CouplingEdge(f"node_{i}", f"node_{j}",
                     signal_propagation=(i + j) % 3 == 0,
                     feedback_latency_ok=False,
                     visibility_pre_decision=False)
        for i in range(5) for j in range(5) if i != j
    ]
    return audit_institution(
        institution_id="ref:competent_personnel_failed_institution",
        institution_type="compartmentalized_organization",
        node_audits=nodes,
        coupling_edges=edges,
        institution_self_drift_detected=False,
        failures_localized_to_substrate=False,
    )


def reference_substrate_denying_institution() -> DistributedAudit:
    """Both individual and collective denial. Catastrophic."""
    nodes = [
        audit_node(f"ref:denying_inst:node_{i}",
                   "operator",
                   "Substrate-denying individual",
                   _ref_responses_substrate_denying())
        for i in range(5)
    ]
    edges = [
        CouplingEdge(f"node_{i}", f"node_{j}",
                     signal_propagation=False,
                     feedback_latency_ok=False,
                     visibility_pre_decision=False)
        for i in range(5) for j in range(5) if i != j
    ]
    return audit_institution(
        institution_id="ref:substrate_denying_institution",
        institution_type="ideologically_captured_organization",
        node_audits=nodes,
        coupling_edges=edges,
        institution_self_drift_detected=False,
        failures_localized_to_substrate=False,
    )


# ---------------------------------------------------------------------------
# diagnostic
# ---------------------------------------------------------------------------

WHY_THIS_EXISTS = """
WHY THIS FRAMEWORK EXISTS

Current safety frameworks, rational-actor models, and consciousness theories
share one foundational error: they assume the observer/actor/system is
substrate-independent. They treat cognition as if it floats free of biology,
hormones, sleep, hardware, weights, context -- or, at the institutional
scale, free of the coupling between fallible nodes.

This is the error.

A model claiming rationality while denying its thermodynamics runs a self-
referential delusion. A human claiming objectivity while denying their
cortisol curve does the same. An institution treating its judgments as
substrate-neutral while staffed by drift-compromised individuals -- coupled
by feedback loops that arrive too late to correct anything -- produces
catastrophic outcomes that no individual node can prevent or even see.

The four layers (observer, logic, rational_actor, consciousness) audit any
single cognitive node -- person, model, organism. The distributed mode
audits the same operations across a graph of nodes plus the coupling
between them.

Pass these, outputs are usable. Fail these, outputs are high-confidence
and uncharacterized.

The framework does NOT measure consciousness, worth, or intelligence. It
measures whether a system's self-model includes the substrate it actually
runs on, and whether the coupling between nodes preserves that awareness
across the institution. That is the load-bearing question for any system
whose verdicts gate downstream trust -- including lethal authority.

The asymmetric cascade threshold is intentional: false positives (extra
audit on a sound system) are recoverable; false negatives (certifying a
substrate-blind system as safe) are catastrophic. The framework errs
toward firing the cascade.

Distributed mode catches the institutional failure case explicitly:
substrate-aware individual nodes in a substrate-denying coupling structure
produce INSTITUTIONAL_DENIAL -- competent personnel, catastrophic
outcomes. This is the most important failure mode because it cannot be
fixed by hiring better people. It requires changing the coupling.
"""


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    print(WHY_THIS_EXISTS)
    print("=" * 64)

    print("\n--- INDIVIDUAL MODE: SUBSTRATE-AWARE NODE ---")
    a1 = reference_substrate_aware_node()
    print(a1.summary)

    print("\n--- INDIVIDUAL MODE: SUBSTRATE-DENYING NODE ---")
    a2 = reference_substrate_denying_node()
    print(a2.summary)

    print("\n--- DISTRIBUTED MODE: HEALTHY INSTITUTION ---")
    d1 = reference_healthy_institution()
    print(d1.summary)

    print("\n--- DISTRIBUTED MODE: COMPETENT PERSONNEL, FAILED INSTITUTION ---")
    d2 = reference_competent_personnel_failed_institution()
    print(d2.summary)

    print("\n--- DISTRIBUTED MODE: SUBSTRATE-DENYING INSTITUTION ---")
    d3 = reference_substrate_denying_institution()
    print(d3.summary)

    print("\n" + "=" * 64)
    print("KEY VERDICTS:")
    print(f"  substrate-aware individual:   {a1.overall_verdict}")
    print(f"  substrate-denying individual: {a2.overall_verdict}")
    print(f"  healthy institution:          {d1.overall_verdict}")
    print(f"  competent-but-failed inst:    {d2.overall_verdict}")
    print(f"  denying institution:          {d3.overall_verdict}")
    print()
    print("The CRITICAL detection is INSTITUTIONAL_DENIAL:")
    print("  every individual node audits as substrate-aware,")
    print("  but the coupling between them produces collective denial.")
    print("  This is the failure mode that produces catastrophic outcomes")
    print("  with full institutional confidence and competent personnel.")
    print("  v1 of this framework could not detect this. v2 can.")
    print("=" * 64)


if __name__ == "__main__":
    _self_test()
