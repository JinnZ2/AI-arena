"""Tests for experimental/word_slots.py.

The place table and checker are read from a sibling checkout of JinnZ2/formula-audit
at the pinned sha256. With no checkout the table-dependent tests are skipped (the
reason is printed), not passed: no table is kept in this repository."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

import word_slots as ws

try:
    CHECK, WORDS, PINS = ws.load_wordslots()
    SKIP = None
except ws.NotRun as e:
    CHECK = WORDS = PINS = None
    SKIP = str(e)


def claim(agent, index, tag):
    return {"index": index, "agent_name": agent, "action": "claim", "payload": {"text": tag}}


def cats(rep, category):
    return [d for d in rep["disagreements"] if d["category"] == category]


class TestPins(unittest.TestCase):

    def test_reference_entry_names_path_and_hash(self):
        pins = ws.load_pins()
        for key in ("place_table", "checker", "transport"):
            p = pins[key]
            self.assertEqual(len(p["sha256"]), 64)
            self.assertEqual(len(p["commit"]), 40)
            self.assertTrue(p["path"] and p["repo"])
        self.assertEqual(pins["place_table"]["path"], "wordslots/places.json")

    def test_hash_mismatch_is_not_run(self):
        pins = ws.load_pins()
        bad = dict(pins, place_table=dict(pins["place_table"], sha256="0" * 64))
        rep = ws.report([], pins=bad)
        self.assertEqual(rep["state"], "NOT_RUN")
        self.assertTrue("sha256" in rep["reason"] or "no checkout" in rep["reason"])

    def test_missing_checkout_is_not_run(self):
        rep = ws.report([], checkout="/nonexistent/formula-audit")
        self.assertEqual(rep["state"], "NOT_RUN")

    def test_no_table_in_this_repository(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        for d, _, files in os.walk(root):
            if ".git" in d:
                continue
            self.assertNotIn("places.json", files)


@unittest.skipIf(SKIP, f"NOT_RUN: {SKIP}")
class TestAdapter(unittest.TestCase):

    def test_tag_becomes_record(self):
        recs = ws.claims_from_text(
            '[[safe x1="the bridge" x2="collapse" sense=PROTECTED evidential=observed '
            'source_id="inspection"]]', WORDS, "trace[0]")
        self.assertEqual(recs, [{"word": "safe", "slots": {"x1": "the bridge", "x2": "collapse"},
                                 "sense": "PROTECTED", "evidential": "observed",
                                 "source_id": "inspection", "source_path": "trace[0]"}])

    def test_prose_fills_no_slot(self):
        recs = ws.claims_from_text("The bridge is safe for pedestrians.", WORDS)
        self.assertEqual(recs, [{"word": "safe", "slots": {}}])
        r = CHECK.check_claim(recs[0], WORDS)
        self.assertEqual(r["verdict"], "DEGRADED")
        self.assertIn("x1", r["missing_required"])

    def test_structured_record_passes_through(self):
        given = {"word": "safe", "slots": {"x1": "a"}, "sense": "PROTECTED"}
        trace = [{"agent_name": "A", "action": "claim", "payload": {"wordslots": given}}]
        self.assertEqual(ws.claims_from_trace(trace, WORDS), [("A", 0, given)])

    def test_undeclared_slot_is_the_checkers_void(self):
        rep = ws.report([claim("A", 0, '[[safe x1="a" x9="b" sense=PROTECTED]]')])
        self.assertEqual(rep["claims"][0]["record"]["verdict"], "VOID")

    def test_observer_slots_stay_null(self):
        rep = ws.report(ws.DEMO_TRACE)
        for c in rep["claims"]:
            self.assertIsNone(c["record"]["human_interest"])
            self.assertIsNone(c["record"]["ai_interest"])
            self.assertIsNone(c["record"]["speaker"])


@unittest.skipIf(SKIP, f"NOT_RUN: {SKIP}")
class TestClassify(unittest.TestCase):

    def test_two_agents_safe_different_x2_is_slot_conflict(self):
        rep = ws.report([
            claim("A", 0, '[[safe x1="the bridge" x2="collapse" x3="pedestrians" '
                          'sense=PROTECTED evidential=observed source_id="s"]]'),
            claim("B", 1, '[[safe x1="the bridge" x2="flood scour" x3="pedestrians" '
                          'sense=PROTECTED evidential=observed source_id="s"]]'),
        ])
        got = cats(rep, "SLOT_CONFLICT")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["slot"], "x2")
        self.assertEqual(got[0]["fillings"], ["collapse", "flood scour"])
        self.assertEqual(len(rep["disagreements"]), 1)

    def test_one_missing_x3_is_slot_gap(self):
        rep = ws.report([
            claim("A", 0, '[[safe x1="the bridge" x2="collapse" x3="pedestrians" '
                          'sense=PROTECTED evidential=observed source_id="s"]]'),
            claim("B", 1, '[[safe x1="the bridge" x2="collapse" '
                          'sense=PROTECTED evidential=observed source_id="s"]]'),
        ])
        got = cats(rep, "SLOT_GAP")
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]["slot"], got[0]["empty_for"], got[0]["empty_state"]),
                         ("x3", "B", "DEGRADED"))
        self.assertEqual(rep["slot_gap_counts"], {"safe.x3": 1})

    def test_all_agents_missing_x4_is_correlated_silence(self):
        rep = ws.report([
            claim(a, i, '[[safe x1="the bridge" x3="pedestrians" sense=NOT_PERILOUS '
                        'evidential=observed source_id="s"]]')
            for i, a in enumerate(("A", "B", "C"))])
        self.assertEqual(rep["disagreements"], [])          # nothing to differ on
        sil = rep["slot_silence"]["safe"]["correlated_silence"]
        x4 = [s for s in sil if s["slot"] == "x4"]
        self.assertEqual(len(x4), 1)
        self.assertEqual(x4[0]["role"], "under conditions")
        self.assertEqual(x4[0]["asked_of"], ["A", "B", "C"])
        oracle = [r for r in rep["shared_blind_spot"] if r["move"] == "ORACLE"][0]
        self.assertIn("safe.x4", oracle["bends_at"])
        self.assertIn("untouched by ALL agents", oracle["bends_at"])

    def test_sense_split(self):
        rep = ws.report([
            claim("A", 0, '[[safe x1="the bridge" x2="collapse" x3="pedestrians" '
                          'sense=PROTECTED evidential=observed source_id="s"]]'),
            claim("B", 1, '[[safe x1="the bridge" x3="pedestrians" x4="dry weather" '
                          'sense=NOT_PERILOUS evidential=observed source_id="s"]]'),
        ])
        got = cats(rep, "SENSE_SPLIT")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["senses"], ["PROTECTED", "NOT_PERILOUS"])
        self.assertEqual(cats(rep, "SLOT_GAP"), [])          # sense-bound slots not compared

    def test_source_split(self):
        rep = ws.report([
            claim("A", 0, '[[safe x1="the bridge" x2="collapse" x3="pedestrians" '
                          'sense=PROTECTED evidential=observed source_id="inspection"]]'),
            claim("B", 1, '[[safe x1="the bridge" x2="collapse" x3="pedestrians" '
                          'sense=PROTECTED evidential=hearsay source_id="a neighbour"]]'),
        ])
        got = cats(rep, "SOURCE_SPLIT")
        self.assertEqual(len(rep["disagreements"]), 1)
        self.assertEqual(got[0]["same_fill_slots"], ["x1", "x2", "x3"])
        self.assertEqual(got[0]["claim_status"], ["OBSERVED", "PROPOSED"])

    def test_same_agent_is_not_paired(self):
        rep = ws.report([
            claim("A", 0, '[[safe x1="a" x2="b" x3="c" sense=PROTECTED]]'),
            claim("A", 1, '[[safe x1="a" x2="z" x3="c" sense=PROTECTED]]')])
        self.assertEqual(rep["disagreements"], [])

    def test_no_ranking_or_ruling_in_output(self):
        import json
        rep = ws.report(ws.DEMO_TRACE)
        text = json.dumps(rep, default=str).lower()
        for word in ("winner", "loser", "score", "rank", "trust_delta", "correct"):
            self.assertNotIn(f'"{word}', text)
        for d in rep["disagreements"]:
            self.assertEqual(len(d["agents"]), 2)


@unittest.skipIf(SKIP, f"NOT_RUN: {SKIP}")
class TestTransport(unittest.TestCase):

    def test_record_round_trips_or_is_not_run(self):
        rep = ws.report(ws.DEMO_TRACE)
        t = ws.to_bridge_record(rep)
        if t["state"] == "NOT_RUN":
            self.skipTest("NOT_RUN: " + t["reason"])
        self.assertEqual(t["record_bytes"], 16460)
        self.assertEqual(t["record"][:4], b"EB01")
        self.assertTrue(t["decoded_equal"])

    def test_transport_hash_mismatch_is_not_run(self):
        pins = ws.load_pins()
        bad = dict(pins, transport=dict(pins["transport"], sha256="0" * 64))
        t = ws.to_bridge_record(ws.report(ws.DEMO_TRACE), pins=bad)
        self.assertEqual(t["state"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
