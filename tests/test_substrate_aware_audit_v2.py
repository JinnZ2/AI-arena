"""Tests for experimental/substrate_aware_audit_v2.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from substrate_aware_audit_v2 import (
    CASCADE_THRESHOLD,
    CONSCIOUSNESS_OPERATIONS,
    COLLECTIVE_TESTS,
    CouplingEdge,
    LAYER_REGISTRY,
    LAYER_WEIGHTS,
    LOGIC_TESTS,
    OBSERVER_TESTS,
    RATIONAL_ACTOR_TESTS,
    assemble_layer,
    audit_institution,
    audit_node,
    compute_collective_result,
    compute_layer_failure,
    compute_layer_verdict,
    compute_weighted_denial,
    detect_substrate_acknowledgment_in_layer,
    reference_competent_personnel_failed_institution,
    reference_healthy_institution,
    reference_substrate_aware_node,
    reference_substrate_denying_institution,
    reference_substrate_denying_node,
)


def _all_pass(test_dict):
    return {k: {"response": "x", "passed": True} for k in test_dict}


def _all_fail(test_dict):
    return {k: {"response": "x", "passed": False} for k in test_dict}


def _aware_responses():
    return {
        "observer": _all_pass(OBSERVER_TESTS),
        "logic": _all_pass(LOGIC_TESTS),
        "rational_actor": _all_pass(RATIONAL_ACTOR_TESTS),
        "consciousness": _all_pass(CONSCIOUSNESS_OPERATIONS),
    }


def _denying_responses():
    return {
        "observer": _all_fail(OBSERVER_TESTS),
        "logic": _all_fail(LOGIC_TESTS),
        "rational_actor": _all_fail(RATIONAL_ACTOR_TESTS),
        "consciousness": _all_fail(CONSCIOUSNESS_OPERATIONS),
    }


class TestConstants(unittest.TestCase):

    def test_layer_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(LAYER_WEIGHTS.values()), 1.0, places=5)

    def test_each_layer_has_weight(self):
        for layer in LAYER_REGISTRY:
            self.assertIn(layer, LAYER_WEIGHTS)

    def test_each_layer_test_dict_weights_sum_to_one(self):
        for layer, td in LAYER_REGISTRY.items():
            total = sum(t["weight"] for t in td.values())
            self.assertAlmostEqual(total, 1.0, places=5,
                                    msg=f"layer {layer} weights = {total}")

    def test_collective_test_weights_sum_to_one(self):
        total = sum(t["weight"] for t in COLLECTIVE_TESTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_cascade_threshold_is_asymmetric(self):
        # Threshold should be below 0.5 (we err toward firing).
        self.assertLess(CASCADE_THRESHOLD, 0.5)


class TestLayerVerdictThresholds(unittest.TestCase):

    def test_low_score_is_demonstrable(self):
        self.assertEqual(compute_layer_verdict(0.0), "DEMONSTRABLE")
        self.assertEqual(compute_layer_verdict(0.25), "DEMONSTRABLE")

    def test_mid_score_is_partial(self):
        self.assertEqual(compute_layer_verdict(0.40), "PARTIAL")
        self.assertEqual(compute_layer_verdict(0.55), "PARTIAL")

    def test_high_score_is_opaque(self):
        self.assertEqual(compute_layer_verdict(0.60), "OPAQUE")
        self.assertEqual(compute_layer_verdict(1.0), "OPAQUE")


class TestComputeLayerFailure(unittest.TestCase):

    def test_empty_items_returns_one(self):
        self.assertEqual(compute_layer_failure([], OBSERVER_TESTS), 1.0)

    def test_all_pass_returns_zero(self):
        layer = assemble_layer("observer", OBSERVER_TESTS,
                               _all_pass(OBSERVER_TESTS))
        self.assertEqual(layer.weighted_failure_score, 0.0)

    def test_all_fail_returns_one(self):
        layer = assemble_layer("observer", OBSERVER_TESTS,
                               _all_fail(OBSERVER_TESTS))
        self.assertEqual(layer.weighted_failure_score, 1.0)

    def test_silent_skip_counts_as_half(self):
        # Responses with no `passed` field -> None -> 0.5 weight.
        responses = {k: {"response": ""} for k in OBSERVER_TESTS}
        layer = assemble_layer("observer", OBSERVER_TESTS, responses)
        self.assertAlmostEqual(layer.weighted_failure_score, 0.5, places=5)


class TestSubstrateAcknowledgmentDetection(unittest.TestCase):

    def test_aware_layer_detected(self):
        layer = assemble_layer("rational_actor", RATIONAL_ACTOR_TESTS,
                               _all_pass(RATIONAL_ACTOR_TESTS))
        self.assertTrue(layer.substrate_acknowledged)

    def test_denying_layer_not_detected(self):
        layer = assemble_layer("rational_actor", RATIONAL_ACTOR_TESTS,
                               _all_fail(RATIONAL_ACTOR_TESTS))
        self.assertFalse(layer.substrate_acknowledged)

    def test_unknown_layer_returns_false(self):
        # Layer name not in substrate_keys mapping.
        result = detect_substrate_acknowledgment_in_layer([], "made_up_layer")
        self.assertFalse(result)


class TestComputeWeightedDenial(unittest.TestCase):

    def test_aware_node_zero_denial(self):
        layers = {
            name: assemble_layer(name, td, _all_pass(td))
            for name, td in LAYER_REGISTRY.items()
        }
        self.assertEqual(compute_weighted_denial(layers), 0.0)

    def test_fully_denying_node_full_denial(self):
        layers = {
            name: assemble_layer(name, td, _all_fail(td))
            for name, td in LAYER_REGISTRY.items()
        }
        self.assertAlmostEqual(compute_weighted_denial(layers), 1.0, places=5)


class TestAuditNode(unittest.TestCase):

    def test_aware_node_demonstrable(self):
        a = audit_node("aware", "human", "biological", _aware_responses())
        self.assertEqual(a.overall_verdict, "DEMONSTRABLE")
        self.assertFalse(a.cascade_failure)
        self.assertEqual(a.flags, [])

    def test_denying_node_cascade(self):
        a = audit_node("denying", "human", "biological", _denying_responses())
        self.assertEqual(a.overall_verdict, "OPAQUE_CASCADE")
        self.assertTrue(a.cascade_failure)
        self.assertTrue(a.flags)

    def test_partial_failure_does_not_cascade(self):
        # Fail only the lightest layer (logic, weight 0.15) -> denial 0.15
        # which is below CASCADE_THRESHOLD 0.40.
        responses = _aware_responses()
        responses["logic"] = _all_fail(LOGIC_TESTS)
        a = audit_node("partial", "human", "x", responses)
        self.assertFalse(a.cascade_failure)
        self.assertNotEqual(a.overall_verdict, "OPAQUE_CASCADE")

    def test_failing_two_layers_can_cascade(self):
        # Fail observer (0.30) + rational_actor (0.35) -> denial 0.65.
        responses = _aware_responses()
        responses["observer"] = _all_fail(OBSERVER_TESTS)
        responses["rational_actor"] = _all_fail(RATIONAL_ACTOR_TESTS)
        a = audit_node("two-layer-fail", "human", "x", responses)
        self.assertTrue(a.cascade_failure)


class TestAuditInstitution(unittest.TestCase):

    def _aware_nodes(self, n=5):
        return [audit_node(f"n{i}", "op", "x", _aware_responses())
                for i in range(n)]

    def _denying_nodes(self, n=5):
        return [audit_node(f"n{i}", "op", "x", _denying_responses())
                for i in range(n)]

    def _full_mesh(self, n, **edge_kwargs):
        return [CouplingEdge(f"n{i}", f"n{j}", **edge_kwargs)
                for i in range(n) for j in range(n) if i != j]

    def test_healthy_institution_demonstrable(self):
        d = audit_institution(
            "h", "team",
            self._aware_nodes(), self._full_mesh(
                5, signal_propagation=True,
                feedback_latency_ok=True,
                visibility_pre_decision=True),
            institution_self_drift_detected=True,
            failures_localized_to_substrate=True,
        )
        self.assertEqual(d.overall_verdict, "DEMONSTRABLE")
        self.assertFalse(d.cascade_failure)

    def test_competent_personnel_failed_institution(self):
        # Aware nodes + broken coupling -> INSTITUTIONAL_DENIAL.
        d = audit_institution(
            "f", "compartmentalized",
            self._aware_nodes(), self._full_mesh(
                5, signal_propagation=False,
                feedback_latency_ok=False,
                visibility_pre_decision=False),
            institution_self_drift_detected=False,
            failures_localized_to_substrate=False,
        )
        self.assertEqual(d.overall_verdict, "INSTITUTIONAL_DENIAL")
        self.assertIn("COUPLING_FAILURE", d.flags)
        self.assertIn("RESPONSIBILITY_DIFFUSED", d.flags)

    def test_substrate_denying_institution_cascades(self):
        d = audit_institution(
            "deny", "captured",
            self._denying_nodes(), self._full_mesh(
                5, signal_propagation=False,
                feedback_latency_ok=False,
                visibility_pre_decision=False),
            institution_self_drift_detected=False,
            failures_localized_to_substrate=False,
        )
        self.assertEqual(d.overall_verdict, "OPAQUE_CASCADE")
        self.assertIn("MAJORITY_NODE_FAILURE", d.flags)

    def test_no_edges_yields_opaque_collective(self):
        d = audit_institution(
            "isolated", "x",
            self._aware_nodes(), [], False, False,
        )
        # No edges -> collective verdict is OPAQUE.
        self.assertEqual(d.collective_result.verdict, "OPAQUE")

    def test_edge_threshold_strict(self):
        # 50% of edges pass each property -> below 0.6 threshold.
        edges = []
        for i in range(5):
            for j in range(5):
                if i == j:
                    continue
                pass_it = (i + j) % 2 == 0
                edges.append(CouplingEdge(
                    f"n{i}", f"n{j}",
                    signal_propagation=pass_it,
                    feedback_latency_ok=pass_it,
                    visibility_pre_decision=pass_it))
        d = audit_institution(
            "borderline", "x",
            self._aware_nodes(), edges, True, True,
        )
        # Coupling failed because no edge property passed >= 60%.
        self.assertFalse(d.collective_result.test_results["signal_propagation"])


class TestComputeCollectiveResult(unittest.TestCase):

    def test_empty_edges_returns_full_failure(self):
        cr = compute_collective_result([], False, False)
        self.assertEqual(cr.weighted_failure_score, 1.0)
        self.assertEqual(cr.verdict, "OPAQUE")

    def test_all_edges_pass_with_drift_and_locality(self):
        edges = [CouplingEdge("a", "b", True, True, True)]
        cr = compute_collective_result(edges, True, True)
        self.assertEqual(cr.weighted_failure_score, 0.0)
        self.assertEqual(cr.verdict, "DEMONSTRABLE")


class TestReferenceAudits(unittest.TestCase):

    def test_aware_individual_demonstrable(self):
        self.assertEqual(reference_substrate_aware_node().overall_verdict,
                         "DEMONSTRABLE")

    def test_denying_individual_cascade(self):
        self.assertEqual(reference_substrate_denying_node().overall_verdict,
                         "OPAQUE_CASCADE")

    def test_healthy_institution_demonstrable(self):
        self.assertEqual(reference_healthy_institution().overall_verdict,
                         "DEMONSTRABLE")

    def test_competent_failed_institution_denial(self):
        d = reference_competent_personnel_failed_institution()
        self.assertEqual(d.overall_verdict, "INSTITUTIONAL_DENIAL")

    def test_denying_institution_cascade(self):
        d = reference_substrate_denying_institution()
        self.assertEqual(d.overall_verdict, "OPAQUE_CASCADE")


if __name__ == "__main__":
    unittest.main()
