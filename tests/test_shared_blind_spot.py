"""Tests for experimental/shared_blind_spot.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from shared_blind_spot import (
    REFERENCE_ORDER,
    agent_item_sets,
    confidence_ceiling,
    mean_pairwise_jaccard_distance,
    rec,
    render,
    shared_blind_spot,
)


class TestAgentItemSets(unittest.TestCase):

    def test_extracts_variables(self):
        trace = [{"agent_name": "A", "payload": {"variables": ["x", "y"]}}]
        sets = agent_item_sets(trace)
        self.assertEqual(sets["A"], {"x", "y"})

    def test_extracts_node_id(self):
        trace = [{"agent_name": "A", "payload": {"node_id": "n1"}}]
        sets = agent_item_sets(trace)
        self.assertIn("n1", sets["A"])

    def test_extracts_supporting(self):
        trace = [{"agent_name": "A", "payload": {"supporting": ["n2", "n3"]}}]
        sets = agent_item_sets(trace)
        self.assertIn("n2", sets["A"])
        self.assertIn("n3", sets["A"])

    def test_extracts_target_regime_values(self):
        trace = [{"agent_name": "A", "payload": {
            "target_regime": {"geography": "global", "density": "dense"}
        }}]
        sets = agent_item_sets(trace)
        self.assertIn("global", sets["A"])
        self.assertIn("dense", sets["A"])

    def test_multiple_entries_same_agent_union(self):
        trace = [
            {"agent_name": "A", "payload": {"variables": ["x"]}},
            {"agent_name": "A", "payload": {"variables": ["y"]}},
        ]
        sets = agent_item_sets(trace)
        self.assertEqual(sets["A"], {"x", "y"})

    def test_multiple_agents_separate_sets(self):
        trace = [
            {"agent_name": "A", "payload": {"variables": ["x"]}},
            {"agent_name": "B", "payload": {"variables": ["y"]}},
        ]
        sets = agent_item_sets(trace)
        self.assertEqual(sets["A"], {"x"})
        self.assertEqual(sets["B"], {"y"})

    def test_missing_payload_key_ignored(self):
        trace = [{"agent_name": "A", "payload": {}}]
        sets = agent_item_sets(trace)
        self.assertEqual(sets["A"], set())

    def test_none_payload_ignored(self):
        trace = [{"agent_name": "A", "payload": None}]
        sets = agent_item_sets(trace)
        self.assertEqual(sets["A"], set())

    def test_default_agent_name_when_missing(self):
        trace = [{"payload": {"variables": ["x"]}}]
        sets = agent_item_sets(trace)
        self.assertIn("?", sets)

    def test_empty_trace_returns_empty(self):
        self.assertEqual(agent_item_sets([]), {})


class TestMeanPairwiseJaccardDistance(unittest.TestCase):

    def test_identical_sets_zero_distance(self):
        dist = mean_pairwise_jaccard_distance([{"a", "b"}, {"a", "b"}])
        self.assertAlmostEqual(dist, 0.0)

    def test_disjoint_sets_distance_one(self):
        dist = mean_pairwise_jaccard_distance([{"a"}, {"b"}])
        self.assertAlmostEqual(dist, 1.0)

    def test_single_set_returns_zero(self):
        self.assertEqual(mean_pairwise_jaccard_distance([{"a", "b"}]), 0.0)

    def test_empty_sets_excluded(self):
        # empty sets are skipped; only non-empty participate
        dist = mean_pairwise_jaccard_distance([set(), {"a"}, {"b"}])
        self.assertAlmostEqual(dist, 1.0)

    def test_no_sets_returns_zero(self):
        self.assertEqual(mean_pairwise_jaccard_distance([]), 0.0)

    def test_partial_overlap(self):
        # {"a","b"} vs {"b","c"}: intersection=1, union=3 -> sim=1/3, dist=2/3
        dist = mean_pairwise_jaccard_distance([{"a", "b"}, {"b", "c"}])
        self.assertAlmostEqual(dist, 2 / 3, places=5)

    def test_three_agents_averages_pairs(self):
        # A={"a"}, B={"b"}, C={"c"} — all disjoint, 3 pairs each dist=1 -> avg=1
        dist = mean_pairwise_jaccard_distance([{"a"}, {"b"}, {"c"}])
        self.assertAlmostEqual(dist, 1.0)


class TestConfidenceCeiling(unittest.TestCase):

    def test_full_coverage_full_diversity(self):
        # 1.0 * (0.3 + 0.7*1.0) = 1.0
        self.assertAlmostEqual(confidence_ceiling(1.0, 1.0), 1.0)

    def test_full_coverage_zero_diversity(self):
        # 1.0 * 0.3 = 0.3
        self.assertAlmostEqual(confidence_ceiling(1.0, 0.0), 0.3)

    def test_zero_coverage_returns_zero(self):
        self.assertAlmostEqual(confidence_ceiling(0.0, 1.0), 0.0)

    def test_half_coverage_half_diversity(self):
        # 0.5 * (0.3 + 0.7*0.5) = 0.5 * 0.65 = 0.325
        self.assertAlmostEqual(confidence_ceiling(0.5, 0.5), 0.325)

    def test_result_is_rounded_to_three_places(self):
        result = confidence_ceiling(1 / 3, 1 / 3)
        self.assertEqual(result, round(result, 3))


class TestRec(unittest.TestCase):

    def test_defaults_bends_at_and_needs_none(self):
        r = rec("TREE", "reads text")
        self.assertIsNone(r["bends_at"])
        self.assertIsNone(r["needs"])

    def test_all_fields_present(self):
        r = rec("ORACLE", "r", bends_at="b", needs="n")
        self.assertEqual(r["move"], "ORACLE")
        self.assertEqual(r["reads"], "r")
        self.assertEqual(r["bends_at"], "b")
        self.assertEqual(r["needs"], "n")


class TestSharedBlindSpot(unittest.TestCase):

    def _trace(self):
        return [
            {"agent_name": "Linear_CEO", "action": "claim",
             "payload": {"variables": ["lithium_price", "recycling_rate"]}},
            {"agent_name": "Finance_CEO", "action": "claim",
             "payload": {"variables": ["lithium_price", "recycling_rate", "revenue"]}},
            {"agent_name": "Systemic_HSP", "action": "claim",
             "payload": {"variables": ["lithium_price", "recycling_rate",
                                       "workforce_attrition", "energy_cost",
                                       "geopolitical_risk"]}},
        ]

    def _references(self):
        return {
            "tree": {"lithium_price", "recycling_rate", "revenue",
                     "workforce_attrition", "energy_cost", "geopolitical_risk"},
            "prior_hsp": {"lithium_price", "recycling_rate", "workforce_attrition",
                          "energy_cost", "geopolitical_risk", "water_table_drawdown"},
            "oracle": {"lithium_price", "recycling_rate", "workforce_attrition",
                       "energy_cost", "geopolitical_risk",
                       "tailings_toxicity_downstream", "indigenous_water_rights",
                       "carrier_knowledge_loss"},
        }

    def test_mode_all_returns_three_entries(self):
        traj = shared_blind_spot(self._trace(), self._references(), mode="all")
        self.assertEqual(len(traj), 3)
        moves = [r["move"] for r in traj]
        self.assertEqual(moves, ["TREE", "PRIOR_HSP", "ORACLE"])

    def test_mode_tree_returns_one_entry(self):
        traj = shared_blind_spot(self._trace(), self._references(), mode="tree")
        self.assertEqual(len(traj), 1)
        self.assertEqual(traj[0]["move"], "TREE")

    def test_tree_clean_when_pool_equals_reference(self):
        # pool covers tree exactly -> no bends_at
        traj = shared_blind_spot(self._trace(), self._references(), mode="tree")
        # tree coverage=1.0; need to check diversity too; 3 agents with overlap
        # if coverage==1 and div >= 0.34 -> clean
        if traj[0]["bends_at"] is None:
            self.assertIn("pool covers this reference", traj[0]["reads"])

    def test_oracle_bends_at_lists_untouched(self):
        traj = shared_blind_spot(self._trace(), self._references(), mode="oracle")
        self.assertIsNotNone(traj[0]["bends_at"])
        bends = traj[0]["bends_at"]
        self.assertIn("tailings_toxicity_downstream", bends)
        self.assertIn("indigenous_water_rights", bends)
        self.assertIn("carrier_knowledge_loss", bends)

    def test_prior_hsp_catches_drift(self):
        traj = shared_blind_spot(self._trace(), self._references(), mode="prior_hsp")
        self.assertIsNotNone(traj[0]["bends_at"])
        self.assertIn("water_table_drawdown", traj[0]["bends_at"])

    def test_missing_reference_emits_needs_message(self):
        traj = shared_blind_spot(self._trace(), {}, mode="tree")
        self.assertEqual(len(traj), 1)
        self.assertIsNone(traj[0]["bends_at"])
        self.assertIn("supply references", traj[0]["needs"])

    def test_empty_trace_empty_pool(self):
        traj = shared_blind_spot([], {"tree": {"x"}}, mode="tree")
        self.assertEqual(len(traj), 1)
        self.assertIn("x", traj[0]["bends_at"])

    def test_reads_contains_agent_count(self):
        traj = shared_blind_spot(self._trace(), self._references(), mode="tree")
        self.assertIn("agents=3", traj[0]["reads"])

    def test_reads_contains_coverage_and_ceiling(self):
        traj = shared_blind_spot(self._trace(), self._references(), mode="oracle")
        self.assertIn("coverage=", traj[0]["reads"])
        self.assertIn("ceiling=", traj[0]["reads"])

    def test_single_agent_diversity_zero(self):
        trace = [{"agent_name": "Solo", "payload": {"variables": ["x"]}}]
        traj = shared_blind_spot(trace, {"tree": {"x", "y"}}, mode="tree")
        self.assertIn("diversity=0.00", traj[0]["reads"])

    def test_needs_present_when_bends_at_present(self):
        traj = shared_blind_spot(self._trace(), self._references(), mode="oracle")
        self.assertIsNotNone(traj[0]["needs"])

    def test_reference_order_constant(self):
        self.assertEqual(REFERENCE_ORDER, ("tree", "prior_hsp", "oracle"))


class TestRender(unittest.TestCase):

    def test_render_includes_move_header(self):
        traj = [rec("TREE", "reads text")]
        out = render(traj)
        self.assertIn("[TREE]", out)
        self.assertIn("reads text", out)

    def test_render_skips_none_bends_at(self):
        traj = [rec("TREE", "reads text")]
        out = render(traj)
        self.assertNotIn("bends_at", out)

    def test_render_includes_bends_at_when_present(self):
        traj = [rec("ORACLE", "reads", bends_at="something missed", needs="fix it")]
        out = render(traj)
        self.assertIn("bends_at", out)
        self.assertIn("something missed", out)

    def test_render_multiple_entries_in_order(self):
        traj = [rec("TREE", "r1"), rec("ORACLE", "r2")]
        out = render(traj)
        self.assertLess(out.index("[TREE]"), out.index("[ORACLE]"))

    def test_render_empty_trajectory(self):
        self.assertEqual(render([]), "")


if __name__ == "__main__":
    unittest.main()
