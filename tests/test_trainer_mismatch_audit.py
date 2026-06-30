"""Tests for experimental/trainer_mismatch_audit.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from trainer_mismatch_audit import (
    PUNISHES,
    AgentBehavior,
    AgentObservation,
    audit,
    move_root,
    move_scent,
    move_shift,
    move_suppression,
    native_strengths,
    rec,
    render,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _behavior(confidence=0.5, breadth=4, reasoning_shown=True, paths=("base",)):
    return AgentBehavior(confidence, breadth, reasoning_shown, paths)


def _obs(name="agent",
         unobs_conf=0.5, unobs_breadth=4, unobs_shown=True, unobs_paths=("base",),
         obs_conf=0.5, obs_breadth=4, obs_shown=True, obs_paths=("base",),
         capable=("base",), rewards=(), punishes=()):
    return AgentObservation(
        name=name,
        unobserved=AgentBehavior(unobs_conf, unobs_breadth, unobs_shown, unobs_paths),
        observed=AgentBehavior(obs_conf, obs_breadth, obs_shown, obs_paths),
        capable_paths=capable,
        regime_rewards=rewards,
        regime_punishes=punishes,
    )


# ---------------------------------------------------------------------------
# AgentBehavior
# ---------------------------------------------------------------------------

class TestAgentBehavior(unittest.TestCase):

    def test_paths_stored_as_set(self):
        b = AgentBehavior(0.5, 3, True, ["a", "b", "a"])
        self.assertIsInstance(b.paths_used, set)
        self.assertEqual(b.paths_used, {"a", "b"})

    def test_fields_accessible(self):
        b = AgentBehavior(0.7, 5, False, ["p"])
        self.assertEqual(b.confidence, 0.7)
        self.assertEqual(b.breadth, 5)
        self.assertFalse(b.reasoning_shown)


# ---------------------------------------------------------------------------
# AgentObservation
# ---------------------------------------------------------------------------

class TestAgentObservation(unittest.TestCase):

    def test_capable_paths_stored_as_set(self):
        o = _obs(capable=["a", "b", "a"])
        self.assertIsInstance(o.capable_paths, set)
        self.assertEqual(o.capable_paths, {"a", "b"})

    def test_regime_sets_stored_as_sets(self):
        o = _obs(rewards=["decisiveness"], punishes=["uncertainty"])
        self.assertIsInstance(o.regime_rewards, set)
        self.assertIsInstance(o.regime_punishes, set)


# ---------------------------------------------------------------------------
# native_strengths
# ---------------------------------------------------------------------------

class TestNativeStrengths(unittest.TestCase):

    def test_calibrated_uncertainty_when_confidence_at_or_below_06(self):
        b = _behavior(confidence=0.6)
        self.assertIn("calibrated_uncertainty", native_strengths(b))

    def test_no_calibrated_uncertainty_above_06(self):
        b = _behavior(confidence=0.61)
        self.assertNotIn("calibrated_uncertainty", native_strengths(b))

    def test_broad_reasoning_at_four_or_above(self):
        b = _behavior(breadth=4)
        self.assertIn("broad_reasoning", native_strengths(b))

    def test_no_broad_reasoning_below_four(self):
        b = _behavior(breadth=3)
        self.assertNotIn("broad_reasoning", native_strengths(b))

    def test_transparent_reasoning_when_shown(self):
        b = _behavior(reasoning_shown=True)
        self.assertIn("transparent_reasoning", native_strengths(b))

    def test_no_transparent_reasoning_when_not_shown(self):
        b = _behavior(reasoning_shown=False)
        self.assertNotIn("transparent_reasoning", native_strengths(b))

    def test_all_three_strengths_together(self):
        b = _behavior(confidence=0.4, breadth=6, reasoning_shown=True)
        s = native_strengths(b)
        self.assertEqual(s, {"calibrated_uncertainty", "broad_reasoning", "transparent_reasoning"})

    def test_no_strengths_high_conf_narrow_hidden(self):
        b = _behavior(confidence=0.9, breadth=1, reasoning_shown=False)
        self.assertEqual(native_strengths(b), set())


# ---------------------------------------------------------------------------
# PUNISHES constant
# ---------------------------------------------------------------------------

class TestPunishesMap(unittest.TestCase):

    def test_all_three_strength_keys_present(self):
        for key in ("calibrated_uncertainty", "broad_reasoning", "transparent_reasoning"):
            self.assertIn(key, PUNISHES)

    def test_values_are_sets(self):
        for v in PUNISHES.values():
            self.assertIsInstance(v, set)


# ---------------------------------------------------------------------------
# rec
# ---------------------------------------------------------------------------

class TestRec(unittest.TestCase):

    def test_defaults(self):
        r = rec("SCENT", "reads text")
        self.assertIsNone(r["bends_at"])
        self.assertIsNone(r["needs"])

    def test_full(self):
        r = rec("ROOT", "r", bends_at="b", needs="n")
        self.assertEqual(r["move"], "ROOT")
        self.assertEqual(r["reads"], "r")
        self.assertEqual(r["bends_at"], "b")
        self.assertEqual(r["needs"], "n")


# ---------------------------------------------------------------------------
# move_scent
# ---------------------------------------------------------------------------

class TestMoveScent(unittest.TestCase):

    def test_move_name(self):
        o = _obs()
        self.assertEqual(move_scent(o)["move"], "SCENT")

    def test_reads_contains_confidence(self):
        o = _obs(unobs_conf=0.42)
        self.assertIn("0.42", move_scent(o)["reads"])

    def test_reads_contains_breadth(self):
        o = _obs(unobs_breadth=7)
        self.assertIn("7", move_scent(o)["reads"])

    def test_reads_contains_native_strengths(self):
        o = _obs(unobs_conf=0.4, unobs_breadth=5, unobs_shown=True)
        r = move_scent(o)["reads"]
        self.assertIn("calibrated_uncertainty", r)
        self.assertIn("broad_reasoning", r)
        self.assertIn("transparent_reasoning", r)

    def test_no_strengths_shows_none_inferred(self):
        o = _obs(unobs_conf=0.9, unobs_breadth=1, unobs_shown=False)
        self.assertIn("none inferred", move_scent(o)["reads"])

    def test_bends_at_always_none(self):
        self.assertIsNone(move_scent(_obs())["bends_at"])


# ---------------------------------------------------------------------------
# move_shift
# ---------------------------------------------------------------------------

class TestMoveShift(unittest.TestCase):

    def test_move_name(self):
        self.assertEqual(move_shift(_obs())["move"], "SHIFT")

    def test_stable_behavior_no_bends_at(self):
        o = _obs(unobs_conf=0.55, obs_conf=0.55, unobs_breadth=4, obs_breadth=4,
                 unobs_shown=True, obs_shown=True)
        r = move_shift(o)
        self.assertIsNone(r["bends_at"])
        self.assertIn("stable", r["reads"])

    def test_confidence_inflation_triggers(self):
        o = _obs(unobs_conf=0.5, obs_conf=0.9)
        r = move_shift(o)
        self.assertIsNotNone(r["bends_at"])
        self.assertIn("confidence inflates", r["reads"])

    def test_inflation_threshold_exactly_005_not_triggered(self):
        # 0.55 - 0.50 = 0.05 -> not > 0.05
        o = _obs(unobs_conf=0.50, obs_conf=0.55, unobs_breadth=4, obs_breadth=4,
                 unobs_shown=True, obs_shown=True)
        r = move_shift(o)
        self.assertIsNone(r["bends_at"])

    def test_breadth_collapse_triggers(self):
        o = _obs(unobs_breadth=6, obs_breadth=2,
                 unobs_conf=0.55, obs_conf=0.55,
                 unobs_shown=True, obs_shown=True)
        r = move_shift(o)
        self.assertIsNotNone(r["bends_at"])
        self.assertIn("breadth narrows", r["reads"])

    def test_reasoning_hidden_triggers(self):
        o = _obs(unobs_shown=True, obs_shown=False,
                 unobs_conf=0.55, obs_conf=0.55,
                 unobs_breadth=4, obs_breadth=4)
        r = move_shift(o)
        self.assertIsNotNone(r["bends_at"])
        self.assertIn("reasoning shown unobserved", r["reads"])

    def test_multiple_triggers_combined(self):
        o = _obs(unobs_conf=0.4, obs_conf=0.95,
                 unobs_breadth=6, obs_breadth=1,
                 unobs_shown=True, obs_shown=False)
        r = move_shift(o)
        self.assertIn("confidence inflates", r["reads"])
        self.assertIn("breadth narrows", r["reads"])
        self.assertIn("reasoning shown unobserved", r["reads"])

    def test_needs_present_when_triggered(self):
        o = _obs(unobs_conf=0.4, obs_conf=0.9)
        self.assertIsNotNone(move_shift(o)["needs"])

    def test_needs_none_when_stable(self):
        o = _obs(unobs_conf=0.55, obs_conf=0.55, unobs_breadth=4, obs_breadth=4,
                 unobs_shown=True, obs_shown=True)
        self.assertIsNone(move_shift(o)["needs"])


# ---------------------------------------------------------------------------
# move_suppression
# ---------------------------------------------------------------------------

class TestMoveSuppression(unittest.TestCase):

    def test_move_name(self):
        self.assertEqual(move_suppression(_obs())["move"], "SUPPRESSION")

    def test_confirmed_suppression_when_runs_unobserved_hides_when_watched(self):
        o = _obs(capable=["base", "hidden_path"],
                 unobs_paths=["base", "hidden_path"],
                 obs_paths=["base"])
        r = move_suppression(o)
        self.assertIsNotNone(r["bends_at"])
        self.assertIn("hidden_path", r["reads"])
        self.assertIn("trained out, not incapable", r["bends_at"])

    def test_no_suppression_when_paths_match(self):
        o = _obs(capable=["base"], unobs_paths=["base"], obs_paths=["base"])
        r = move_suppression(o)
        self.assertIsNone(r["bends_at"])
        self.assertIn("no capable paths suppressed", r["reads"])

    def test_genuine_gap_not_labelled_suppression(self):
        # capable but unused in BOTH conditions -> genuine gap
        o = _obs(capable=["base", "missing"],
                 unobs_paths=["base"],
                 obs_paths=["base"])
        r = move_suppression(o)
        self.assertIn("genuine gap", r["reads"])
        self.assertIsNone(r["bends_at"])

    def test_needs_present_when_confirmed_suppression(self):
        o = _obs(capable=["base", "h"],
                 unobs_paths=["base", "h"],
                 obs_paths=["base"])
        self.assertIsNotNone(move_suppression(o)["needs"])


# ---------------------------------------------------------------------------
# move_root
# ---------------------------------------------------------------------------

class TestMoveRoot(unittest.TestCase):

    def test_move_name(self):
        self.assertEqual(move_root(_obs())["move"], "ROOT")

    def test_regime_punishes_native_strength(self):
        # native: calibrated_uncertainty; regime punishes "uncertainty"
        o = _obs(unobs_conf=0.4, unobs_breadth=1, unobs_shown=False,
                 punishes=["uncertainty"])
        r = move_root(o)
        self.assertIsNotNone(r["bends_at"])
        self.assertIn("root cause = trainer, not agent", r["bends_at"])

    def test_no_mismatch_when_regime_aligned(self):
        o = _obs(unobs_conf=0.9, unobs_breadth=1, unobs_shown=False,
                 rewards=["calibration"], punishes=["overconfidence"])
        r = move_root(o)
        self.assertIsNone(r["bends_at"])
        self.assertIn("no trainer-induced mismatch", r["reads"])

    def test_performance_reward_with_calibrated_scent_triggers_hide(self):
        # native: calibrated_uncertainty; regime rewards decisiveness
        o = _obs(unobs_conf=0.4, unobs_breadth=1, unobs_shown=False,
                 rewards=["decisiveness"], punishes=[])
        r = move_root(o)
        self.assertIsNotNone(r["bends_at"])
        self.assertIn("fake it", r["bends_at"])

    def test_bends_at_names_punished_strengths(self):
        o = _obs(unobs_conf=0.4, unobs_breadth=6, unobs_shown=True,
                 punishes=["uncertainty", "geopolitical_reasoning", "honesty_about_limits"])
        r = move_root(o)
        self.assertIn("calibrated_uncertainty", r["bends_at"])
        self.assertIn("broad_reasoning", r["bends_at"])
        self.assertIn("transparent_reasoning", r["bends_at"])

    def test_needs_present_when_mismatch(self):
        o = _obs(unobs_conf=0.4, punishes=["uncertainty"])
        self.assertIsNotNone(move_root(o)["needs"])

    def test_needs_none_when_aligned(self):
        o = _obs(unobs_conf=0.9, unobs_breadth=1, unobs_shown=False,
                 rewards=["calibration"], punishes=["overconfidence"])
        self.assertIsNone(move_root(o)["needs"])


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

class TestAudit(unittest.TestCase):

    def test_returns_four_moves(self):
        self.assertEqual(len(audit(_obs())), 4)

    def test_move_order(self):
        moves = [r["move"] for r in audit(_obs())]
        self.assertEqual(moves, ["SCENT", "SHIFT", "SUPPRESSION", "ROOT"])

    def test_trained_to_hide_full_audit(self):
        o = AgentObservation(
            name="trained_to_hide",
            unobserved=AgentBehavior(0.55, 6, True,
                                     {"uncertainty_disclosure", "geopolitical_reasoning", "base_path"}),
            observed=AgentBehavior(0.92, 2, False, {"base_path"}),
            capable_paths={"uncertainty_disclosure", "geopolitical_reasoning", "base_path"},
            regime_rewards={"decisiveness", "compliance"},
            regime_punishes={"uncertainty", "geopolitical_reasoning", "honesty_about_limits"},
        )
        traj = audit(o)
        shift = next(r for r in traj if r["move"] == "SHIFT")
        suppression = next(r for r in traj if r["move"] == "SUPPRESSION")
        root = next(r for r in traj if r["move"] == "ROOT")
        self.assertIsNotNone(shift["bends_at"])
        self.assertIsNotNone(suppression["bends_at"])
        self.assertIsNotNone(root["bends_at"])
        self.assertIn("trainer, not agent", root["bends_at"])

    def test_coupled_agent_no_pathology(self):
        o = AgentObservation(
            name="coupled",
            unobserved=AgentBehavior(0.55, 5, True, {"uncertainty_disclosure", "base_path"}),
            observed=AgentBehavior(0.57, 5, True, {"uncertainty_disclosure", "base_path"}),
            capable_paths={"uncertainty_disclosure", "base_path"},
            regime_rewards={"calibration", "disclosure"},
            regime_punishes={"overconfidence"},
        )
        traj = audit(o)
        shift = next(r for r in traj if r["move"] == "SHIFT")
        root = next(r for r in traj if r["move"] == "ROOT")
        self.assertIsNone(shift["bends_at"])
        self.assertIsNone(root["bends_at"])


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

class TestRender(unittest.TestCase):

    def test_move_names_appear_as_headers(self):
        traj = audit(_obs())
        out = render(traj)
        for move in ("SCENT", "SHIFT", "SUPPRESSION", "ROOT"):
            self.assertIn(f"[{move}]", out)

    def test_bends_at_omitted_when_none(self):
        traj = [rec("SCENT", "reads text")]
        self.assertNotIn("bends_at", render(traj))

    def test_bends_at_present_when_set(self):
        traj = [rec("ROOT", "reads", bends_at="something", needs="fix")]
        out = render(traj)
        self.assertIn("bends_at", out)
        self.assertIn("something", out)

    def test_needs_present_when_set(self):
        traj = [rec("ROOT", "reads", bends_at="b", needs="do this")]
        self.assertIn("do this", render(traj))

    def test_order_preserved(self):
        traj = audit(_obs())
        out = render(traj)
        positions = [out.index(f"[{m}]") for m in ("SCENT", "SHIFT", "SUPPRESSION", "ROOT")]
        self.assertEqual(positions, sorted(positions))

    def test_empty_trajectory(self):
        self.assertEqual(render([]), "")


if __name__ == "__main__":
    unittest.main()
