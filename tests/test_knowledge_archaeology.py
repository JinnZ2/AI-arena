"""Tests for src/knowledge_archaeology.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from knowledge_archaeology import (
    KnowledgeNode,
    KnowledgeTree,
    Regime,
    TransmissionMode,
    ValidationDepth,
    APPLICABLE_THRESHOLD,
    REVIEW_THRESHOLD,
    applicability,
    load_tree_from_directory,
    regime_distance,
    regime_from_dict,
    _node_from_dict,
)


def _make_node(node_id: str, regime: Regime, **kwargs) -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        title=kwargs.pop("title", node_id),
        regime=regime,
        transmission=kwargs.pop("transmission", TransmissionMode.LIVED_ORAL),
        validation_depth=kwargs.pop("validation_depth", ValidationDepth.LIVED),
        **kwargs,
    )


class TestRegimeDistance(unittest.TestCase):

    def test_identical_regimes_distance_zero(self):
        r = Regime("X", "Dfb", "sparse", "preindustrial", "tribal")
        self.assertEqual(regime_distance(r, r), 0.0)

    def test_fully_foreign_regimes_distance_one(self):
        a = Regime("X", "Dfb", "sparse", "preindustrial", "tribal")
        b = Regime("Y", "Aw", "dense", "postindustrial", "corporate")
        self.assertAlmostEqual(regime_distance(a, b), 1.0, places=3)

    def test_ordinal_one_step_returns_half(self):
        a = Regime(technology_level="preindustrial")
        b = Regime(technology_level="industrial")
        # Only the technology axis differs by 1/2; geography & climate fields
        # are empty on both, so they return 0 (no info).
        # density and institutional are also empty -> 0.5 each.
        # tech: 0.5; institutional: 0.5; density: 0.5; geography: 0; climate: 0.
        d = regime_distance(a, b)
        self.assertGreater(d, 0.0)
        self.assertLess(d, 1.0)

    def test_unknown_value_treated_as_fully_foreign(self):
        a = Regime(technology_level="preindustrial")
        b = Regime(technology_level="quantum")
        # On a known/unknown ordinal pair, distance jumps to 1.0 for that axis.
        self.assertGreater(regime_distance(a, b), regime_distance(a, a))

    def test_tribal_corporate_institutional_far(self):
        a = Regime(institutional_context="tribal")
        b = Regime(institutional_context="corporate")
        c = Regime(institutional_context="state")  # also far from tribal
        d = Regime(institutional_context="communal")  # not in FAR set
        self.assertGreater(
            regime_distance(a, b),
            regime_distance(a, d),
        )
        self.assertGreater(
            regime_distance(a, c),
            regime_distance(a, d),
        )


class TestApplicability(unittest.TestCase):

    def test_applicable_at_low_distance(self):
        regime = Regime("X", "Dfb", "sparse", "preindustrial", "tribal")
        node = _make_node("n", regime)
        result = applicability(node, regime)
        self.assertEqual(result["verdict"], "applicable")
        self.assertEqual(result["score"], 0.0)

    def test_review_required_in_band(self):
        node = _make_node("n", Regime(
            "X", "Dfb", "sparse", "preindustrial", "tribal"))
        target = Regime("Y", "Dfb", "medium", "preindustrial", "communal")
        d = regime_distance(node.regime, target)
        self.assertGreater(d, APPLICABLE_THRESHOLD)
        self.assertLessEqual(d, REVIEW_THRESHOLD)
        self.assertEqual(applicability(node, target)["verdict"], "review_required")

    def test_do_not_deploy_at_high_distance(self):
        node = _make_node("n", Regime(
            "X", "Dfb", "sparse", "preindustrial", "tribal"))
        target = Regime("Y", "any", "dense", "industrial", "corporate")
        result = applicability(node, target)
        self.assertEqual(result["verdict"], "do_not_deploy")
        self.assertGreater(result["score"], REVIEW_THRESHOLD)
        self.assertTrue(result["reasons"])


class TestKnowledgeTree(unittest.TestCase):

    def setUp(self):
        self.tree = KnowledgeTree()
        self.root = _make_node("root",
            Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
            constraints_addressed=["potable water"])
        self.child = _make_node("child",
            Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
            parent_ids=["root"], constraints_addressed=["potable water"])
        self.parallel = _make_node("parallel",
            Regime("Y", "BSh", "medium", "preindustrial", "communal"),
            constraints_addressed=["potable water"])
        self.unrelated = _make_node("unrelated",
            Regime("Z", "Aw", "dense", "industrial", "corporate"),
            constraints_addressed=["something else"])
        for n in (self.root, self.child, self.parallel, self.unrelated):
            self.tree.add(n)

    def test_ancestors_returns_transitive_parents(self):
        self.assertEqual(self.tree.ancestors("child"), ["root"])
        self.assertEqual(self.tree.ancestors("root"), [])
        self.assertEqual(self.tree.ancestors("nonexistent"), [])

    def test_parallel_lineages_finds_shared_constraints(self):
        results = self.tree.parallel_lineages("root")
        ids = [r["id"] for r in results]
        self.assertIn("parallel", ids)
        self.assertIn("child", ids)
        self.assertNotIn("unrelated", ids)
        self.assertNotIn("root", ids)

    def test_attribution_trail_includes_self_and_ancestors(self):
        trail = self.tree.attribution_trail("child")
        self.assertEqual([t["id"] for t in trail], ["child", "root"])

    def test_deploy_check_unknown_node(self):
        result = self.tree.deploy_check("ghost", Regime())
        self.assertIn("error", result)

    def test_deploy_check_in_regime(self):
        result = self.tree.deploy_check("root",
            Regime("X", "Dfb", "sparse", "preindustrial", "tribal"))
        self.assertEqual(result["applicability"]["verdict"], "applicable")

    def test_deploy_check_extracted_node_warns(self):
        node = _make_node("ext",
            Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
            transmission=TransmissionMode.EXTRACTED_AGGREGATED)
        self.tree.add(node)
        result = self.tree.deploy_check("ext", node.regime)
        self.assertTrue(result["transmission_warnings"])

    def test_deploy_check_consent_states(self):
        for consent, must_warn in [("none", True), ("contested", True),
                                    ("unspecified", True), ("granted", False)]:
            node = _make_node(f"c_{consent}",
                Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
                carrier_consent=consent)
            self.tree.add(node)
            result = self.tree.deploy_check(f"c_{consent}", node.regime)
            if must_warn:
                self.assertTrue(result["consent_warnings"], consent)
            else:
                self.assertFalse(result["consent_warnings"], consent)


class TestNodeFromDict(unittest.TestCase):

    def test_invalid_consent_raises(self):
        with self.assertRaises(ValueError):
            _node_from_dict({
                "id": "n", "regime": {}, "carrier_consent": "bogus",
            })

    def test_minimal_node_loads(self):
        node = _node_from_dict({"id": "n"})
        self.assertEqual(node.id, "n")
        self.assertEqual(node.transmission, TransmissionMode.LIVED_ORAL)
        self.assertEqual(node.validation_depth, ValidationDepth.LIVED)


class TestLoadTreeFromDirectory(unittest.TestCase):

    def test_loads_seed_nodes(self):
        nodes_dir = os.path.join(os.path.dirname(__file__), "..", "nodes")
        tree = load_tree_from_directory(nodes_dir)
        self.assertIn("anishinaabe_gravity_filtration_v1", tree.nodes)
        self.assertIn("punjab_terracotta_filter_v1", tree.nodes)
        self.assertIn("ethnobotanical_isolate_v1", tree.nodes)
        self.assertIn("pacific_wayfinding_reconstructed_v1", tree.nodes)

    def test_extracted_aggregated_node_warns_on_deploy(self):
        nodes_dir = os.path.join(os.path.dirname(__file__), "..", "nodes")
        tree = load_tree_from_directory(nodes_dir)
        target = regime_from_dict({
            "geography": "global", "climate_zone": "any",
            "population_density": "dense", "technology_level": "industrial",
            "institutional_context": "corporate",
        })
        check = tree.deploy_check("ethnobotanical_isolate_v1", target)
        self.assertTrue(any("extracted/aggregated" in w
                            for w in check["transmission_warnings"]))
        self.assertTrue(check["consent_warnings"])

    def test_reconstructed_node_loads_with_witnessed_validation(self):
        nodes_dir = os.path.join(os.path.dirname(__file__), "..", "nodes")
        tree = load_tree_from_directory(nodes_dir)
        node = tree.nodes["pacific_wayfinding_reconstructed_v1"]
        self.assertEqual(node.transmission.value, "reconstructed")
        self.assertEqual(node.validation_depth.value, "witnessed")

    def test_missing_directory_returns_empty_tree(self):
        tree = load_tree_from_directory("/nonexistent/path/here")
        self.assertEqual(len(tree.nodes), 0)


class TestRegimeFromDict(unittest.TestCase):

    def test_missing_keys_default_to_empty(self):
        r = regime_from_dict({})
        self.assertEqual(r.geography, "")
        self.assertEqual(r.climate_zone, "")

    def test_full_dict_round_trip(self):
        d = {
            "geography": "X", "climate_zone": "Dfb",
            "population_density": "sparse", "technology_level": "preindustrial",
            "institutional_context": "tribal",
        }
        r = regime_from_dict(d)
        self.assertEqual(r.to_dict(), d)


if __name__ == "__main__":
    unittest.main()
