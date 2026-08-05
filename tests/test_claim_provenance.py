"""Tests for experimental/claim_provenance.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from claim_provenance import (
    Agent,
    Claim,
    ClaimNetwork,
    ClaimStatus,
    Evidence,
    Opinion,
    ProvenanceScientificFramework,
    build_demo_network,
    contested_scene,
    render_disagreement,
    render_provenance,
)


def _sums_to_one(op):
    return abs(op.b + op.d + op.u - 1.0) < 1e-6


class TestOpinion(unittest.TestCase):

    def test_normalizes_drift(self):
        op = Opinion(0.5, 0.5, 0.5, 0.5)
        self.assertTrue(_sums_to_one(op))

    def test_zero_mass_becomes_vacuous(self):
        op = Opinion(0.0, 0.0, 0.0, 0.5)
        self.assertTrue(op.is_vacuous)
        self.assertTrue(_sums_to_one(op))

    def test_negative_mass_clamped(self):
        op = Opinion(0.8, -0.3, 0.2, 0.5)
        self.assertEqual(op.d, 0.0)
        self.assertTrue(_sums_to_one(op))

    def test_expectation_uses_base_rate(self):
        op = Opinion(0.2, 0.2, 0.6, 0.5)
        self.assertAlmostEqual(op.expectation, 0.5)

    def test_discount_moves_distrust_to_uncertainty(self):
        claim_op = Opinion(0.9, 0.1, 0.0, 0.5)
        distrusted = claim_op.discount(Opinion(0.0, 0.9, 0.1, 0.5))
        self.assertTrue(distrusted.is_vacuous)

    def test_discount_reduces_belief(self):
        claim_op = Opinion(0.9, 0.1, 0.0, 0.5)
        discounted = claim_op.discount(Opinion(0.5, 0.2, 0.3, 0.5))
        self.assertLess(discounted.b, claim_op.b)
        self.assertGreater(discounted.u, claim_op.u)

    def test_dilute_endpoints(self):
        op = Opinion(0.6, 0.2, 0.2, 0.5)
        self.assertAlmostEqual(op.dilute(1.0).b, 0.6)
        self.assertTrue(op.dilute(0.0).is_vacuous)

    def test_negate_swaps_belief_and_disbelief(self):
        op = Opinion(0.7, 0.1, 0.2, 0.4).negate()
        self.assertAlmostEqual(op.b, 0.1)
        self.assertAlmostEqual(op.d, 0.7)
        self.assertAlmostEqual(op.a, 0.6)

    def test_fusion_with_vacuous_is_identity(self):
        op = Opinion(0.6, 0.2, 0.2, 0.5)
        fused = Opinion.cumulative_fuse(op, Opinion.vacuous())
        self.assertAlmostEqual(fused.b, op.b)
        self.assertAlmostEqual(fused.d, op.d)
        self.assertAlmostEqual(fused.u, op.u)

    def test_fusion_is_commutative(self):
        a = Opinion(0.6, 0.2, 0.2, 0.5)
        b = Opinion(0.3, 0.3, 0.4, 0.5)
        ab = Opinion.cumulative_fuse(a, b)
        ba = Opinion.cumulative_fuse(b, a)
        self.assertAlmostEqual(ab.b, ba.b)
        self.assertAlmostEqual(ab.u, ba.u)

    def test_fusion_reduces_uncertainty(self):
        a = Opinion(0.5, 0.1, 0.4, 0.5)
        fused = Opinion.cumulative_fuse(a, Opinion(0.5, 0.1, 0.4, 0.5))
        self.assertLess(fused.u, a.u)

    def test_fusion_of_two_dogmatic_opinions_averages(self):
        fused = Opinion.cumulative_fuse(Opinion(1, 0, 0, 0.5), Opinion(0, 1, 0, 0.5))
        self.assertAlmostEqual(fused.b, 0.5)
        self.assertTrue(_sums_to_one(fused))

    def test_fusion_preserves_normalization(self):
        pairs = [
            (Opinion(0.9, 0.05, 0.05, 0.5), Opinion(0.05, 0.9, 0.05, 0.5)),
            (Opinion(0.0, 0.0, 1.0, 0.5), Opinion(0.0, 0.0, 1.0, 0.5)),
            (Opinion(0.3, 0.3, 0.4, 0.2), Opinion(0.1, 0.8, 0.1, 0.9)),
        ]
        for a, b in pairs:
            self.assertTrue(_sums_to_one(Opinion.cumulative_fuse(a, b)))


class TestClaimProvenance(unittest.TestCase):

    def test_add_evidence_logs_history(self):
        claim = Claim(id=1, statement="x")
        claim.add_evidence(Evidence(2, "observed x"))
        self.assertEqual(len(claim.history), 1)
        self.assertIn("Agent2", claim.history[0])

    def test_echo_from_same_source_rejected(self):
        claim = Claim(id=1, statement="x")
        self.assertTrue(claim.add_evidence(Evidence(2, "observed x")))
        self.assertFalse(claim.add_evidence(Evidence(2, "observed x")))
        self.assertEqual(len(claim.evidence), 1)
        self.assertIn("Echo ignored", claim.history[-1])

    def test_same_content_from_different_source_kept(self):
        claim = Claim(id=1, statement="x")
        claim.add_evidence(Evidence(2, "observed x"))
        self.assertTrue(claim.add_evidence(Evidence(3, "observed x")))
        self.assertEqual(claim.sources, {2, 3})


class TestAgentEvaluation(unittest.TestCase):

    def setUp(self):
        self.net = ClaimNetwork()
        self.claim = Claim(id=1, statement="the door is red")
        self.claim.add_evidence(Evidence(2, "saw red", relevance=0.9))
        self.net.add_claim(self.claim)

    def test_untrusted_source_yields_vacuous(self):
        agent = Agent(1, {})
        self.net.add_agent(agent)
        self.assertTrue(agent.evaluate_claim(self.claim, self.net).is_vacuous)

    def test_trusted_source_yields_belief(self):
        agent = Agent(1, {2: Opinion(0.9, 0.05, 0.05, 0.5)})
        self.net.add_agent(agent)
        op = agent.evaluate_claim(self.claim, self.net)
        self.assertGreater(op.b, 0.6)

    def test_lower_trust_yields_more_uncertainty(self):
        high = Agent(1, {2: Opinion(0.9, 0.05, 0.05, 0.5)}).evaluate_claim(self.claim, self.net)
        low = Agent(3, {2: Opinion(0.3, 0.2, 0.5, 0.5)}).evaluate_claim(self.claim, self.net)
        self.assertGreater(low.u, high.u)
        self.assertLess(low.b, high.b)

    def test_source_trace_records_who_moved_the_opinion(self):
        agent = Agent(1, {2: Opinion(0.9, 0.05, 0.05, 0.5)})
        self.net.add_agent(agent)
        agent.evaluate_claim(self.claim, self.net)
        self.assertEqual(agent.source_trace[1], {2})

    def test_attack_edge_raises_disbelief(self):
        target = Claim(id=2, statement="the gem is behind it")
        target.add_evidence(Evidence(2, "map says so", relevance=0.8))
        self.net.add_claim(target)
        agent = Agent(1, {2: Opinion(0.9, 0.05, 0.05, 0.5)})
        self.net.add_agent(agent)

        undisputed = agent.evaluate_claim(target, self.net)
        agent.belief_graph[1] = Opinion(0.9, 0.05, 0.05, 0.5)  # believes the attacker
        self.net.add_argument(1, 2, "attack")
        attacked = agent.evaluate_claim(target, self.net)
        self.assertGreater(attacked.d, undisputed.d)

    def test_vacuous_antecedent_does_not_move_target(self):
        target = Claim(id=2, statement="the gem is behind it")
        target.add_evidence(Evidence(2, "map says so", relevance=0.8))
        self.net.add_claim(target)
        agent = Agent(1, {2: Opinion(0.9, 0.05, 0.05, 0.5)})
        self.net.add_agent(agent)
        before = agent.evaluate_claim(target, self.net)

        agent.belief_graph[1] = Opinion.vacuous()
        self.net.add_argument(1, 2, "attack")
        after = agent.evaluate_claim(target, self.net)
        self.assertAlmostEqual(before.b, after.b)
        self.assertAlmostEqual(before.d, after.d)

    def test_unknown_relation_rejected(self):
        self.net.add_claim(Claim(id=2, statement="y"))
        with self.assertRaises(ValueError):
            self.net.add_argument(1, 2, "undermine")


class TestBroadcastAndConsensus(unittest.TestCase):

    def _net(self, relevance_by_source, trust_by_agent, damping=1.0):
        net = ClaimNetwork(correlation_damping=damping)
        claim = Claim(id=1, statement="c")
        for src, rel in relevance_by_source.items():
            claim.add_evidence(Evidence(src, f"report from {src}", relevance=rel))
        net.add_claim(claim)
        for aid, trust in trust_by_agent.items():
            net.add_agent(Agent(aid, trust))
        return net

    def test_consensus_unknown_without_opinions(self):
        net = self._net({1: 0.9}, {})
        self.assertIs(net.consensus(1), ClaimStatus.UNKNOWN)

    def test_broadcast_skips_sender(self):
        net = self._net({1: 0.9}, {
            10: {1: Opinion(0.9, 0.05, 0.05, 0.5)},
            11: {1: Opinion(0.9, 0.05, 0.05, 0.5)},
        })
        net.broadcast(1, sender_id=11)
        self.assertIn(1, net.agents[10].belief_graph)
        self.assertNotIn(1, net.agents[11].belief_graph)

    def test_verified_on_trusted_supporting_evidence(self):
        net = self._net({1: 0.95, 2: 0.9}, {
            10: {1: Opinion(0.9, 0.05, 0.05, 0.5), 2: Opinion(0.9, 0.05, 0.05, 0.5)},
        })
        net.broadcast(1)
        self.assertIs(net.consensus(1), ClaimStatus.VERIFIED)

    def test_refuted_on_trusted_contrary_evidence(self):
        net = self._net({1: 0.05, 2: 0.05}, {
            10: {1: Opinion(0.9, 0.05, 0.05, 0.5), 2: Opinion(0.9, 0.05, 0.05, 0.5)},
        })
        net.broadcast(1)
        self.assertIs(net.consensus(1), ClaimStatus.REFUTED)

    def test_nei_when_uncertainty_dominates(self):
        net = self._net({1: 0.7}, {10: {1: Opinion(0.2, 0.1, 0.7, 0.5)}})
        net.broadcast(1)
        self.assertIs(net.consensus(1), ClaimStatus.NEI)

    def test_undecided_between_thresholds(self):
        net = self._net({1: 0.6}, {10: {1: Opinion(0.75, 0.15, 0.1, 0.5)}})
        net.broadcast(1)
        status = net.consensus(1)
        self.assertIs(status, ClaimStatus.UNDEC)
        self.assertLess(net.claims[1].opinion.u, 0.5)

    def test_split_pool_is_disputed_not_averaged(self):
        net, claim = contested_scene()
        net.broadcast(claim.id)
        self.assertIs(net.consensus(claim.id), ClaimStatus.DISPUTED)

    def test_correlation_damping_preserves_uncertainty(self):
        trust = {1: Opinion(0.8, 0.1, 0.1, 0.5)}
        agents = {10: dict(trust), 11: dict(trust), 12: dict(trust)}

        naive = self._net({1: 0.9}, agents, damping=0.0)
        naive.broadcast(1)
        naive.consensus(1)

        priced = self._net({1: 0.9}, agents, damping=1.0)
        priced.broadcast(1)
        priced.consensus(1)

        self.assertGreater(priced.claims[1].opinion.u, naive.claims[1].opinion.u)

    def test_priced_echo_equals_a_single_reading(self):
        trust = {1: Opinion(0.8, 0.1, 0.1, 0.5)}
        net = self._net({1: 0.9}, {10: dict(trust), 11: dict(trust), 12: dict(trust)})
        net.broadcast(1)
        net.consensus(1)
        solo = net.agents[10].belief_graph[1]
        self.assertAlmostEqual(net.claims[1].opinion.b, solo.b, places=6)
        self.assertAlmostEqual(net.claims[1].opinion.u, solo.u, places=6)

    def test_independent_sources_do_accumulate(self):
        net = self._net(
            {1: 0.9, 2: 0.9},
            {
                10: {1: Opinion(0.8, 0.1, 0.1, 0.5)},
                11: {2: Opinion(0.8, 0.1, 0.1, 0.5)},
            },
        )
        net.broadcast(1)
        net.consensus(1)
        solo = net.agents[10].belief_graph[1]
        self.assertLess(net.claims[1].opinion.u, solo.u)

    def test_consensus_stores_opinion_and_logs(self):
        net = self._net({1: 0.9}, {10: {1: Opinion(0.8, 0.1, 0.1, 0.5)}})
        net.broadcast(1)
        net.consensus(1)
        self.assertIsNotNone(net.claims[1].opinion)
        self.assertTrue(any("fused:" in h for h in net.claims[1].history))


class TestDisagreementMap(unittest.TestCase):

    def test_no_opinions(self):
        net = ClaimNetwork()
        net.add_claim(Claim(id=1, statement="c"))
        dmap = net.disagreement_map(1)
        self.assertEqual(dmap.categories, ["no_opinions"])
        self.assertFalse(dmap.is_polarized)

    def test_polarized_pool_named_and_kept(self):
        net, claim = contested_scene()
        net.broadcast(claim.id)
        dmap = net.disagreement_map(claim.id)
        self.assertIn("polarized", dmap.categories)
        self.assertTrue(dmap.is_polarized)
        self.assertIn(10, dmap.believers)
        self.assertIn(11, dmap.disbelievers)
        self.assertIn(13, dmap.abstainers)
        self.assertGreater(dmap.spread, 0.5)
        self.assertEqual(len(dmap.per_agent), 4)

    def test_uncertainty_split_detected(self):
        net, claim = contested_scene()
        net.broadcast(claim.id)
        self.assertIn("uncertainty_split", net.disagreement_map(claim.id).categories)

    def test_echo_pool_named(self):
        net = ClaimNetwork()
        claim = Claim(id=1, statement="c")
        claim.add_evidence(Evidence(1, "the one report", relevance=0.9))
        net.add_claim(claim)
        for aid in (10, 11, 12):
            net.add_agent(Agent(aid, {1: Opinion(0.8, 0.1, 0.1, 0.5)}))
        net.broadcast(1)
        dmap = net.disagreement_map(1)
        self.assertIn("echo", dmap.categories)
        self.assertAlmostEqual(dmap.mean_source_overlap, 1.0)

    def test_independent_pool_named(self):
        net = ClaimNetwork()
        claim = Claim(id=1, statement="c")
        claim.add_evidence(Evidence(1, "report one", relevance=0.9))
        claim.add_evidence(Evidence(2, "report two", relevance=0.9))
        net.add_claim(claim)
        net.add_agent(Agent(10, {1: Opinion(0.8, 0.1, 0.1, 0.5)}))
        net.add_agent(Agent(11, {2: Opinion(0.8, 0.1, 0.1, 0.5)}))
        net.broadcast(1)
        dmap = net.disagreement_map(1)
        self.assertIn("independent_pool", dmap.categories)
        self.assertAlmostEqual(dmap.mean_source_overlap, 0.0)

    def test_abstainers_do_not_dilute_overlap(self):
        net = ClaimNetwork()
        claim = Claim(id=1, statement="c")
        claim.add_evidence(Evidence(1, "the one report", relevance=0.9))
        net.add_claim(claim)
        for aid in (10, 11):
            net.add_agent(Agent(aid, {1: Opinion(0.8, 0.1, 0.1, 0.5)}))
        net.add_agent(Agent(12, {}))  # abstains
        net.broadcast(1)
        self.assertAlmostEqual(net.disagreement_map(1).mean_source_overlap, 1.0)

    def test_render_is_readable(self):
        net, claim = contested_scene()
        net.broadcast(claim.id)
        text = render_disagreement(net.disagreement_map(claim.id))
        self.assertIn("polarized", text)
        self.assertIn("Agent10", text)
        self.assertIn("abstains", text)


class TestFramework(unittest.TestCase):

    def setUp(self):
        self.net = build_demo_network()
        self.smf = ProvenanceScientificFramework(self.net, verbose=False, seed=7)

    def test_formulate_records_proposer(self):
        claim = self.smf.formulate_claim("c", proposer_agent_id=2)
        self.assertIs(claim.status, ClaimStatus.PROPOSED)
        self.assertIn("proposed by Agent2", claim.history[0])

    def test_test_claim_sets_status_and_opinion(self):
        claim = self.smf.formulate_claim(
            "c", 1, [Evidence(2, "saw it", relevance=0.9)]
        )
        status = self.smf.test_claim(claim.id)
        self.assertIsInstance(status, ClaimStatus)
        self.assertIs(claim.status, status)
        self.assertIsNotNone(claim.opinion)

    def test_modify_claim_links_and_retires_parent(self):
        parent = self.smf.formulate_claim("c", 1, [Evidence(2, "saw it", relevance=0.6)])
        child = self.smf.modify_claim(parent.id, [Evidence(3, "and also", relevance=0.7)])
        self.assertEqual(child.was_revision_of, parent.id)
        self.assertIs(parent.status, ClaimStatus.DORMANT)
        self.assertEqual(child.sources, {2, 3})
        self.assertEqual(child.derivation_method, "revision")

    def test_decided_claim_is_not_made_dormant(self):
        claim = self.smf.formulate_claim("c", 1)
        claim.status = ClaimStatus.VERIFIED
        self.assertIs(self.net.mark_dormant(claim.id), ClaimStatus.VERIFIED)

    def test_hidden_variable_search_attributes_the_finder(self):
        claim = self.smf.formulate_claim("c", 1)
        ev = self.smf.hidden_variable_search(claim.id)
        self.assertIsNotNone(ev)
        self.assertIn(ev.source_agent_id, self.net.agents)
        self.assertIn(ev, claim.evidence)

    def test_hidden_variable_search_on_empty_pool(self):
        net = ClaimNetwork()
        smf = ProvenanceScientificFramework(net, verbose=False)
        claim = smf.formulate_claim("c", 1)
        self.assertIsNone(smf.hidden_variable_search(claim.id))

    def test_provenance_chain_walks_revisions(self):
        c1 = self.smf.formulate_claim("c", 1, [Evidence(2, "e", relevance=0.6)])
        c2 = self.smf.modify_claim(c1.id)
        c3 = self.smf.modify_claim(c2.id)
        self.assertEqual(self.net.provenance_chain(c3.id), [c1.id, c2.id, c3.id])

    def test_provenance_chain_of_root_is_itself(self):
        c1 = self.smf.formulate_claim("c", 1)
        self.assertEqual(self.net.provenance_chain(c1.id), [c1.id])

    def test_render_provenance_includes_history(self):
        c1 = self.smf.formulate_claim("c", 1, [Evidence(2, "saw it", relevance=0.6)])
        c2 = self.smf.modify_claim(c1.id)
        text = render_provenance(self.net, c2.id)
        self.assertIn("saw it", text)
        self.assertIn("dormant", text)

    def test_iterate_is_deterministic_under_seed(self):
        def run():
            net = build_demo_network()
            smf = ProvenanceScientificFramework(net, verbose=False, seed=7)
            smf.iterate(max_iterations=5)
            return [(cid, c.status.value, c.statement) for cid, c in sorted(net.claims.items())]

        self.assertEqual(run(), run())

    def test_iterate_produces_claims_with_history(self):
        self.smf.iterate(max_iterations=4)
        self.assertGreater(len(self.net.claims), 1)
        for claim in self.net.claims.values():
            self.assertTrue(claim.history)

    def test_disputed_claim_is_not_iterated_into_agreement(self):
        net, claim = contested_scene()
        smf = ProvenanceScientificFramework(net, verbose=False, seed=1)
        smf.claim_counter = claim.id
        smf.current_claim = claim
        smf.iterate(max_iterations=1)
        self.assertIs(claim.status, ClaimStatus.DORMANT)
        self.assertIn("disputed split preserved", " ".join(claim.history))
        # no revision was spawned to paper over the split
        self.assertEqual(len(net.claims), 1)


if __name__ == "__main__":
    unittest.main()
