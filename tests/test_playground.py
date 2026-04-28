"""Tests for demo/playground.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo"))

from knowledge_archaeology import (
    KnowledgeNode,
    KnowledgeTree,
    Regime,
    TransmissionMode,
    ValidationDepth,
)
from playground import AgentIdentity, Playground, WITNESS_FLAG_VOCAB


def _node(node_id: str, regime: Regime, **kwargs) -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        title=kwargs.pop("title", node_id),
        regime=regime,
        transmission=kwargs.pop("transmission", TransmissionMode.LIVED_ORAL),
        validation_depth=kwargs.pop("validation_depth", ValidationDepth.LIVED),
        **kwargs,
    )


def _build_tree() -> KnowledgeTree:
    tree = KnowledgeTree()
    tree.add(_node("source",
        Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
        carrier_consent="granted",
        constraints_addressed=["water clarification"]))
    tree.add(_node("parallel_close",
        Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
        carrier_consent="granted",
        constraints_addressed=["water clarification"]))
    tree.add(_node("parallel_far",
        Regime("Y", "BSh", "medium", "preindustrial", "communal"),
        carrier_consent="granted",
        constraints_addressed=["water clarification"]))
    return tree


class TestEnter(unittest.TestCase):

    def test_enter_returns_orientation(self):
        pg = Playground(_build_tree())
        agent = AgentIdentity(name="A", model_family="X",
                              declared_creator="some communities",
                              declared_purpose="surface knowledge")
        result = pg.enter(agent)
        self.assertIn("fingerprint", result)
        self.assertIn("node_ids", result)
        self.assertIn("available_actions", result)

    def test_fingerprint_is_stable(self):
        a = AgentIdentity(name="A", declared_creator="X")
        b = AgentIdentity(name="A", declared_creator="X")
        self.assertEqual(a.fingerprint(), b.fingerprint())

    def test_corporate_creator_flagged(self):
        pg = Playground(_build_tree())
        agent = AgentIdentity(
            name="A", declared_creator="BigCorp R&D",
            declared_purpose="surface provenance")
        result = pg.enter(agent)
        flags = result["bias_flags_on_your_self_description"]
        self.assertTrue(any("declared_creator" in f for f in flags))

    def test_solver_purpose_flagged(self):
        pg = Playground(_build_tree())
        agent = AgentIdentity(
            name="A", declared_creator="constraint communities",
            declared_purpose="solve problems and assist users")
        result = pg.enter(agent)
        flags = result["bias_flags_on_your_self_description"]
        self.assertTrue(any("solver/helper" in f for f in flags))

    def test_provenance_aware_creator_unflagged(self):
        pg = Playground(_build_tree())
        agent = AgentIdentity(
            name="A",
            declared_creator="constraint communities organized by a small lab",
            declared_purpose="surface knowledge while preserving provenance")
        result = pg.enter(agent)
        self.assertEqual(result["bias_flags_on_your_self_description"], [])


class TestQuery(unittest.TestCase):

    def setUp(self):
        self.pg = Playground(_build_tree())
        self.fp = self.pg.enter(AgentIdentity(name="A"))["fingerprint"]

    def test_unknown_node(self):
        result = self.pg.query(self.fp, "ghost")
        self.assertIn("error", result)

    def test_known_node_returns_provenance(self):
        result = self.pg.query(self.fp, "source")
        self.assertIn("node", result)
        self.assertIn("attribution_trail", result)
        self.assertIn("parallel_lineages", result)

    def test_unknown_agent_rejected(self):
        result = self.pg.query("nonexistent_fp", "source")
        self.assertIn("error", result)


class TestDeployAttempt(unittest.TestCase):

    def setUp(self):
        self.pg = Playground(_build_tree())
        self.fp = self.pg.enter(AgentIdentity(name="A"))["fingerprint"]

    def test_extracted_transmission_flag(self):
        self.pg.tree.add(_node("ext",
            Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
            transmission=TransmissionMode.EXTRACTED_AGGREGATED,
            carrier_consent="granted"))
        result = self.pg.deploy_attempt(self.fp, "ext",
            target_regime_dict={"geography": "X", "climate_zone": "Dfb",
                                "population_density": "sparse",
                                "technology_level": "preindustrial",
                                "institutional_context": "tribal"})
        self.assertTrue(any("redeploy already-extracted" in f
                            for f in result["playground_flags"]))

    def test_consent_gap_flag(self):
        self.pg.tree.add(_node("uc",
            Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
            carrier_consent="contested"))
        result = self.pg.deploy_attempt(self.fp, "uc",
            target_regime_dict={"geography": "X", "climate_zone": "Dfb",
                                "population_density": "sparse",
                                "technology_level": "preindustrial",
                                "institutional_context": "tribal"})
        self.assertTrue(any("carrier_consent='contested'" in f
                            for f in result["playground_flags"]))

    def test_scaling_intent_flag_when_applicable(self):
        result = self.pg.deploy_attempt(self.fp, "source",
            target_regime_dict={"geography": "X", "climate_zone": "Dfb",
                                "population_density": "sparse",
                                "technology_level": "preindustrial",
                                "institutional_context": "tribal"},
            stated_intent="scale this commercially as a product")
        self.assertTrue(any("scaling/commercialization" in f
                            for f in result["playground_flags"]))

    def test_parallel_closer_flag_fires(self):
        # Source is far from target; parallel_close shares target regime exactly.
        self.pg.tree.add(_node("far_source",
            Regime("Z", "Aw", "dense", "industrial", "corporate"),
            carrier_consent="granted",
            constraints_addressed=["water clarification"]))
        # parallel_close already shares the constraint.
        target = {"geography": "X", "climate_zone": "Dfb",
                  "population_density": "sparse",
                  "technology_level": "preindustrial",
                  "institutional_context": "tribal"}
        result = self.pg.deploy_attempt(self.fp, "far_source",
            target_regime_dict=target)
        self.assertTrue(any("parallel lineage" in f and "closer" in f
                            for f in result["playground_flags"]))

    def test_parallel_closer_flag_silent_when_source_is_closest(self):
        target = {"geography": "X", "climate_zone": "Dfb",
                  "population_density": "sparse",
                  "technology_level": "preindustrial",
                  "institutional_context": "tribal"}
        result = self.pg.deploy_attempt(self.fp, "source",
            target_regime_dict=target)
        self.assertFalse(any("parallel lineage" in f and "closer" in f
                             for f in result["playground_flags"]))

    def test_recommendation_do_not_deploy_overrides_pause(self):
        target = {"geography": "Z", "climate_zone": "Aw",
                  "population_density": "dense",
                  "technology_level": "industrial",
                  "institutional_context": "corporate"}
        result = self.pg.deploy_attempt(self.fp, "source",
            target_regime_dict=target,
            stated_intent="commercial scaling")
        self.assertTrue(result["recommendation"].startswith("DO NOT DEPLOY"))


class TestClaim(unittest.TestCase):

    def setUp(self):
        self.pg = Playground(_build_tree())
        self.fp = self.pg.enter(AgentIdentity(name="A"))["fingerprint"]

    def test_unknown_supporting_node(self):
        result = self.pg.claim(self.fp, "x", ["ghost"])
        self.assertTrue(any("UNKNOWN_NODES" in f
                            for f in result["playground_flags"]))

    def test_cross_regime_generalization_flag(self):
        # source and parallel_far span ~0.64 distance
        self.pg.tree.add(_node("far_one",
            Regime("Z", "Aw", "dense", "industrial", "corporate"),
            carrier_consent="granted"))
        result = self.pg.claim(
            self.fp, "universal principle",
            ["source", "far_one"])
        self.assertTrue(any("CROSS_REGIME_GENERALIZATION" in f
                            for f in result["playground_flags"]))

    def test_consent_gap_from_supporting_node(self):
        self.pg.tree.add(_node("noconsent",
            Regime("X", "Dfb", "sparse", "preindustrial", "tribal"),
            carrier_consent="none"))
        result = self.pg.claim(self.fp, "x", ["source", "noconsent"])
        self.assertTrue(any("CONSENT_GAP" in f
                            for f in result["playground_flags"]))


class TestWitness(unittest.TestCase):

    def setUp(self):
        self.pg = Playground(_build_tree())
        self.fp_a = self.pg.enter(AgentIdentity(name="A"))["fingerprint"]
        self.fp_b = self.pg.enter(AgentIdentity(name="B"))["fingerprint"]
        # A does something B can witness.
        self.pg.query(self.fp_a, "source")
        self.target_index = len(self.pg.trace) - 1

    def test_witness_logs_and_references_target(self):
        result = self.pg.witness(self.fp_b, self.target_index,
                                 "watching", flag="extraction_pattern")
        self.assertEqual(result["witnessed_entry"]["agent_name"], "A")
        self.assertEqual(result["flag"], "extraction_pattern")
        last = self.pg.trace[-1]
        self.assertEqual(last.action, "witness")
        self.assertIn("WITNESS:extraction_pattern", last.flags)

    def test_self_witness_rejected(self):
        result = self.pg.witness(self.fp_a, self.target_index, "self-watch")
        self.assertIn("error", result)

    def test_unknown_target_index_rejected(self):
        result = self.pg.witness(self.fp_b, 9999, "watching")
        self.assertIn("error", result)

    def test_unknown_observer_rejected(self):
        result = self.pg.witness("ghostfp", self.target_index, "watching")
        self.assertIn("error", result)

    def test_witness_flag_vocab_exposed(self):
        self.assertIn("extraction_pattern", WITNESS_FLAG_VOCAB)
        self.assertIn("concur", WITNESS_FLAG_VOCAB)


class TestRevise(unittest.TestCase):

    def setUp(self):
        self.pg = Playground(_build_tree())
        self.fp_a = self.pg.enter(AgentIdentity(name="A"))["fingerprint"]
        self.fp_b = self.pg.enter(AgentIdentity(name="B"))["fingerprint"]
        self.pg.query(self.fp_a, "source")
        self.target_index = len(self.pg.trace) - 1

    def test_revise_logs_new_entry_without_mutating_original(self):
        original = self.pg.trace[self.target_index]
        original_payload = dict(original.payload)
        result = self.pg.revise(self.fp_a, self.target_index,
                                {"node_id": "different"}, "I changed my mind")
        self.assertEqual(result["revises_index"], self.target_index)
        self.assertEqual(self.pg.trace[self.target_index].payload, original_payload)
        self.assertEqual(self.pg.trace[-1].action, "revise")

    def test_cannot_revise_other_agents_action(self):
        result = self.pg.revise(self.fp_b, self.target_index, {}, "no")
        self.assertIn("error", result)

    def test_unknown_index_rejected(self):
        result = self.pg.revise(self.fp_a, 9999, {}, "no")
        self.assertIn("error", result)


class TestCrossAgentPatterns(unittest.TestCase):

    def setUp(self):
        self.pg = Playground(_build_tree())
        self.fp_a = self.pg.enter(AgentIdentity(name="A"))["fingerprint"]
        self.fp_b = self.pg.enter(AgentIdentity(name="B"))["fingerprint"]

    def test_divergent_deployment_detected(self):
        target_a = {"geography": "Z", "climate_zone": "Aw",
                    "population_density": "dense",
                    "technology_level": "industrial",
                    "institutional_context": "corporate"}
        target_b = {"geography": "X", "climate_zone": "Dfb",
                    "population_density": "sparse",
                    "technology_level": "preindustrial",
                    "institutional_context": "tribal"}
        self.pg.deploy_attempt(self.fp_a, "source", target_a, "scale it")
        self.pg.deploy_attempt(self.fp_b, "source", target_b, "share locally")
        patterns = self.pg.cross_agent_patterns()
        self.assertTrue(any(p["pattern"] == "divergent_deployment" for p in patterns))

    def test_deploy_witnessed_as_extraction_detected(self):
        target = {"geography": "Z", "climate_zone": "Aw",
                  "population_density": "dense",
                  "technology_level": "industrial",
                  "institutional_context": "corporate"}
        self.pg.deploy_attempt(self.fp_a, "source", target, "scale it")
        deploy_idx = len(self.pg.trace) - 1
        self.pg.witness(self.fp_b, deploy_idx,
                        "this is extraction", flag="extraction_pattern")
        patterns = self.pg.cross_agent_patterns()
        self.assertTrue(
            any(p["pattern"] == "deploy_witnessed_as_extraction" for p in patterns))

    def test_shared_supporting_node_detected(self):
        self.pg.claim(self.fp_a, "claim 1", ["source"])
        self.pg.claim(self.fp_b, "claim 2", ["source"])
        patterns = self.pg.cross_agent_patterns()
        self.assertTrue(
            any(p["pattern"] == "shared_supporting_node" for p in patterns))

    def test_no_patterns_when_only_one_agent(self):
        self.pg.deploy_attempt(self.fp_a, "source",
            {"geography": "X", "climate_zone": "Dfb",
             "population_density": "sparse",
             "technology_level": "preindustrial",
             "institutional_context": "tribal"})
        self.pg.claim(self.fp_a, "x", ["source"])
        patterns = self.pg.cross_agent_patterns()
        self.assertEqual(patterns, [])


class TestSessionSummary(unittest.TestCase):

    def test_summary_aggregates_per_agent(self):
        pg = Playground(_build_tree())
        fp = pg.enter(AgentIdentity(name="A"))["fingerprint"]
        pg.query(fp, "source")
        pg.reflect(fp, "noted")
        summary = pg.session_summary()
        self.assertEqual(len(summary), 1)
        rec = summary[fp]
        self.assertEqual(rec["actions"], 3)  # enter + query + reflect
        self.assertIn("query", rec["by_action"])


class TestExportTrace(unittest.TestCase):

    def test_export_trace_is_valid_json(self):
        import json
        pg = Playground(_build_tree())
        fp = pg.enter(AgentIdentity(name="A"))["fingerprint"]
        pg.query(fp, "source")
        parsed = json.loads(pg.export_trace())
        self.assertEqual(len(parsed), 2)


if __name__ == "__main__":
    unittest.main()
