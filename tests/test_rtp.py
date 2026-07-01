"""Tests for the v2 RTP arena modules:
  arena/admission.py, arena/reciprocity.py, arena/routing.py,
  arena/visibility.py, arena/coordinator.py, arena/audit.py
"""

import unittest

from arena.admission import (
    TRUST_DIMENSIONS,
    AgentProfile,
    DimensionRecord,
    TransparencyLevel,
)
from arena.reciprocity import access_report, can_access, reciprocity_matrix
from arena.routing import ARTIFACT_KINDS, POOL_PRIVATE, POOL_SHARED, destination, route_batch
from arena.visibility import VisibilityGate
from arena.coordinator import Coordinator
from arena.audit import session_audit


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _transparent(name="T"):
    return AgentProfile(name=name, transparency_level=TransparencyLevel.TRANSPARENT)


def _private(name="P"):
    return AgentProfile(name=name, transparency_level=TransparencyLevel.PRIVATE)


# ===========================================================================
# DimensionRecord
# ===========================================================================

class TestDimensionRecord(unittest.TestCase):

    def test_default_score_is_half(self):
        d = DimensionRecord(dimension="x")
        self.assertEqual(d.score, 0.5)

    def test_observe_updates_score(self):
        d = DimensionRecord(dimension="x")
        d.observe(1.0)
        self.assertEqual(d.score, 1.0)

    def test_rolling_mean_last_twenty(self):
        d = DimensionRecord(dimension="x")
        for _ in range(25):
            d.observe(0.0)
        d.observe(1.0)
        # 19 zeros + 1 one = 1/20 = 0.05
        self.assertAlmostEqual(d.score, 0.05)

    def test_observe_rejects_out_of_range(self):
        d = DimensionRecord(dimension="x")
        with self.assertRaises(ValueError):
            d.observe(1.1)
        with self.assertRaises(ValueError):
            d.observe(-0.1)

    def test_count_tracks_observations(self):
        d = DimensionRecord(dimension="x")
        d.observe(0.5)
        d.observe(0.7)
        self.assertEqual(d.count, 2)


# ===========================================================================
# AgentProfile
# ===========================================================================

class TestAgentProfile(unittest.TestCase):

    def test_all_trust_dimensions_initialised(self):
        p = AgentProfile(name="A")
        for dim in TRUST_DIMENSIONS:
            self.assertIn(dim, p.trust_record)

    def test_transparent_permissions_superset_of_private(self):
        t = _transparent()
        p = _private()
        self.assertTrue(p.current_permissions < t.current_permissions)

    def test_private_cannot_view_shared_reasoning(self):
        p = _private()
        self.assertNotIn("view_shared_reasoning", p.current_permissions)

    def test_transparent_can_view_shared_reasoning(self):
        t = _transparent()
        self.assertIn("view_shared_reasoning", t.current_permissions)

    def test_both_can_access_public_results(self):
        for profile in (_transparent(), _private()):
            self.assertIn("access_public_results", profile.current_permissions)

    def test_observe_records_value(self):
        p = AgentProfile(name="A")
        p.observe("transparency", 0.9, note="consistent")
        self.assertAlmostEqual(p.trust_record["transparency"].score, 0.9)

    def test_trust_summary_has_all_dimensions(self):
        p = AgentProfile(name="A")
        summary = p.trust_summary()
        for dim in TRUST_DIMENSIONS:
            self.assertIn(dim, summary)

    def test_trust_summary_no_aggregate(self):
        # summary must not contain a single "total" or "score" key
        p = AgentProfile(name="A")
        summary = p.trust_summary()
        self.assertNotIn("total", summary)
        self.assertNotIn("score", summary)

    def test_log_audit_appends(self):
        p = AgentProfile(name="A")
        p.log_audit("admit")
        p.log_audit("submit", "proposal")
        self.assertEqual(len(p.audit_history), 2)


# ===========================================================================
# reciprocity
# ===========================================================================

class TestCanAccess(unittest.TestCase):

    def test_both_transparent_granted(self):
        self.assertTrue(can_access(_transparent("A"), _transparent("B")))

    def test_observer_private_denied(self):
        self.assertFalse(can_access(_private("P"), _transparent("T")))

    def test_target_private_denied(self):
        self.assertFalse(can_access(_transparent("T"), _private("P")))

    def test_both_private_denied(self):
        self.assertFalse(can_access(_private("P1"), _private("P2")))


class TestAccessReport(unittest.TestCase):

    def test_granted_report(self):
        r = access_report(_transparent("A"), _transparent("B"))
        self.assertTrue(r["access_granted"])
        self.assertIn("mutual", r["reason"])

    def test_private_observer_report_mentions_reciprocity(self):
        r = access_report(_private("P"), _transparent("T"))
        self.assertFalse(r["access_granted"])
        self.assertIn("reciprocity", r["reason"])

    def test_private_target_report(self):
        r = access_report(_transparent("T"), _private("P"))
        self.assertFalse(r["access_granted"])
        self.assertIn("private", r["reason"])

    def test_report_fields(self):
        r = access_report(_transparent("A"), _private("B"))
        for field in ("observer", "target", "observer_level", "target_level",
                      "access_granted", "reason"):
            self.assertIn(field, r)


class TestReciprocityMatrix(unittest.TestCase):

    def test_three_agents_three_pairs(self):
        profiles = [_transparent("A"), _transparent("B"), _private("C")]
        matrix = reciprocity_matrix(profiles)
        self.assertEqual(len(matrix), 3)

    def test_all_transparent_all_granted(self):
        profiles = [_transparent("A"), _transparent("B"), _transparent("C")]
        matrix = reciprocity_matrix(profiles)
        self.assertTrue(all(r["access_granted"] for r in matrix))

    def test_single_agent_empty_matrix(self):
        self.assertEqual(reciprocity_matrix([_transparent("A")]), [])


# ===========================================================================
# routing
# ===========================================================================

class TestDestination(unittest.TestCase):

    def test_transparent_proposal_to_shared(self):
        d = destination(_transparent(), "proposal")
        self.assertEqual(d["pool"], POOL_SHARED)
        self.assertEqual(d["subfolder"], "proposals")

    def test_transparent_critique_to_shared(self):
        d = destination(_transparent(), "critique")
        self.assertEqual(d["pool"], POOL_SHARED)

    def test_transparent_revision_to_shared(self):
        d = destination(_transparent(), "revision")
        self.assertEqual(d["pool"], POOL_SHARED)

    def test_private_agent_to_private(self):
        d = destination(_private(), "proposal")
        self.assertEqual(d["pool"], POOL_PRIVATE)
        self.assertIsNone(d["subfolder"])

    def test_unknown_kind_returns_error(self):
        d = destination(_transparent(), "monologue")
        self.assertIn("error", d)

    def test_artifact_kinds_nonempty(self):
        self.assertTrue(len(ARTIFACT_KINDS) > 0)


class TestRouteBatch(unittest.TestCase):

    def test_batch_length_matches_input(self):
        agent = _transparent()
        arts = [{"kind": "proposal"}, {"kind": "critique"}]
        results = route_batch(agent, arts)
        self.assertEqual(len(results), 2)

    def test_batch_private_agent_all_private(self):
        agent = _private()
        arts = [{"kind": "proposal"}, {"kind": "revision"}]
        for r in route_batch(agent, arts):
            self.assertEqual(r["pool"], POOL_PRIVATE)


# ===========================================================================
# visibility
# ===========================================================================

class TestVisibilityGate(unittest.TestCase):

    def test_transparent_deposit_succeeds(self):
        gate = VisibilityGate()
        result = gate.deposit(_transparent(), {"kind": "proposal"})
        self.assertTrue(result["deposited"])
        self.assertEqual(result["pool"], "shared")

    def test_private_deposit_rejected(self):
        gate = VisibilityGate()
        result = gate.deposit(_private(), {"kind": "proposal"})
        self.assertFalse(result["deposited"])
        self.assertEqual(result["pool"], "private")

    def test_transparent_observer_reads_pool(self):
        gate = VisibilityGate()
        gate.deposit(_transparent("A"), {"kind": "proposal", "text": "hello"})
        entries = gate.retrieve(_transparent("B"))
        self.assertEqual(len(entries), 1)

    def test_private_observer_reads_nothing(self):
        gate = VisibilityGate()
        gate.deposit(_transparent("A"), {"kind": "proposal"})
        entries = gate.retrieve(_private("P"))
        self.assertEqual(entries, [])

    def test_retrieve_filters_by_agent(self):
        gate = VisibilityGate()
        gate.deposit(_transparent("A"), {"kind": "proposal", "x": 1})
        gate.deposit(_transparent("B"), {"kind": "proposal", "x": 2})
        entries = gate.retrieve(_transparent("C"), target_agent="A")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["agent"], "A")

    def test_pool_size_counts_transparent_only(self):
        gate = VisibilityGate()
        gate.deposit(_transparent(), {"kind": "proposal"})
        gate.deposit(_private(), {"kind": "proposal"})
        self.assertEqual(gate.pool_size(), 1)

    def test_publish_visible_to_all(self):
        gate = VisibilityGate()
        gate.publish({"conclusion": "water is wet"})
        self.assertEqual(len(gate.published()), 1)

    def test_published_returns_copy(self):
        gate = VisibilityGate()
        gate.publish({"c": 1})
        pub = gate.published()
        pub.append({"c": 2})
        self.assertEqual(len(gate.published()), 1)


# ===========================================================================
# coordinator
# ===========================================================================

class TestCoordinator(unittest.TestCase):

    def setUp(self):
        self.c = Coordinator()
        self.t = _transparent("Alice")
        self.p = _private("Bob")

    def test_admit_returns_orientation(self):
        result = self.c.admit(self.t)
        self.assertEqual(result["agent"], "Alice")
        self.assertIn("permissions", result)
        self.assertIn("transparency_level", result)

    def test_admit_logs_event(self):
        self.c.admit(self.t)
        log = self.c.session_log()
        self.assertEqual(log[0]["event"], "admit")

    def test_submit_unknown_agent_errors(self):
        result = self.c.submit("Ghost", "proposal", {})
        self.assertIn("error", result)

    def test_submit_unknown_kind_errors(self):
        self.c.admit(self.t)
        result = self.c.submit("Alice", "monologue", {})
        self.assertIn("error", result)

    def test_transparent_submit_reaches_shared_pool(self):
        self.c.admit(self.t)
        result = self.c.submit("Alice", "proposal", {"text": "hi"})
        self.assertTrue(result["deposited"])
        self.assertEqual(self.c.pool_size(), 1)

    def test_private_submit_does_not_reach_shared_pool(self):
        self.c.admit(self.p)
        result = self.c.submit("Bob", "proposal", {"text": "hi"})
        self.assertFalse(result["deposited"])
        self.assertEqual(self.c.pool_size(), 0)

    def test_transparent_reads_shared_pool(self):
        self.c.admit(self.t)
        self.c.admit(self.p)
        self.c.submit("Alice", "proposal", {"text": "reasoning"})
        entries = self.c.read("Alice")
        self.assertEqual(len(entries), 1)

    def test_private_reads_empty(self):
        self.c.admit(self.t)
        self.c.admit(self.p)
        self.c.submit("Alice", "proposal", {"text": "reasoning"})
        entries = self.c.read("Bob")
        self.assertEqual(entries, [])

    def test_read_unknown_observer_errors(self):
        result = self.c.read("Ghost")
        self.assertIn("error", result)

    def test_access_check_between_known_agents(self):
        self.c.admit(self.t)
        self.c.admit(self.p)
        report = self.c.access_check("Bob", "Alice")
        self.assertFalse(report["access_granted"])

    def test_access_check_unknown_agent_errors(self):
        self.c.admit(self.t)
        result = self.c.access_check("Alice", "Ghost")
        self.assertIn("error", result)

    def test_full_access_matrix_covers_all_pairs(self):
        t2 = _transparent("Carol")
        self.c.admit(self.t)
        self.c.admit(self.p)
        self.c.admit(t2)
        matrix = self.c.full_access_matrix()
        self.assertEqual(len(matrix), 3)  # 3 choose 2

    def test_record_convergence_requires_topic(self):
        with self.assertRaises(ValueError):
            self.c.record_convergence({"agree": [], "disagree": []})

    def test_record_convergence_preserves_disagreement(self):
        self.c.record_convergence({
            "topic": "lithium extraction",
            "agree": ["price-sensitive"],
            "disagree": ["timeline-sensitive", "consent-required"],
        })
        cm = self.c.convergence_map()
        self.assertEqual(len(cm), 1)
        self.assertEqual(len(cm[0]["disagree"]), 2)

    def test_publish_visible_in_published(self):
        self.c.admit(self.t)
        self.c.publish({"conclusion": "water is wet"})
        self.assertEqual(len(self.c.published()), 1)

    def test_session_log_grows_with_events(self):
        self.c.admit(self.t)
        self.c.submit("Alice", "proposal", {})
        self.c.record_convergence({"topic": "x", "agree": [], "disagree": []})
        self.c.publish({"c": "y"})
        log = self.c.session_log()
        events = [e["event"] for e in log]
        self.assertIn("admit", events)
        self.assertIn("submit", events)
        self.assertIn("convergence_map", events)
        self.assertIn("publish", events)

    def test_agent_profiles_returns_copy(self):
        self.c.admit(self.t)
        profiles = self.c.agent_profiles()
        profiles["injected"] = _transparent("Injected")
        self.assertNotIn("injected", self.c.agent_profiles())


# ===========================================================================
# audit
# ===========================================================================

class TestSessionAudit(unittest.TestCase):

    def test_empty_coordinator(self):
        c = Coordinator()
        result = session_audit(c)
        self.assertEqual(result["agent_count"], 0)
        self.assertEqual(result["shared_pool_size"], 0)

    def test_counts_agents_by_level(self):
        c = Coordinator()
        c.admit(_transparent("A"))
        c.admit(_transparent("B"))
        c.admit(_private("C"))
        result = session_audit(c)
        self.assertEqual(result["agent_count"], 3)
        self.assertEqual(len(result["by_transparency_level"]["transparent"]), 2)
        self.assertEqual(len(result["by_transparency_level"]["private"]), 1)

    def test_pool_size_in_summary(self):
        c = Coordinator()
        t = _transparent("A")
        c.admit(t)
        c.submit("A", "proposal", {})
        result = session_audit(c)
        self.assertEqual(result["shared_pool_size"], 1)

    def test_convergence_map_count(self):
        c = Coordinator()
        c.record_convergence({"topic": "x", "agree": [], "disagree": []})
        result = session_audit(c)
        self.assertEqual(result["convergence_map_entries"], 1)


if __name__ == "__main__":
    unittest.main()
