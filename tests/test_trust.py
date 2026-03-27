"""Tests for the trust engine."""

import unittest

from arena.trust import TrustEngine, TrustState


class TestTrustEngine(unittest.TestCase):

    def setUp(self):
        self.engine = TrustEngine()

    def test_initial_trust(self):
        state = TrustState()
        self.assertEqual(state.score, 0.5)
        self.assertTrue(state.can_attack)

    def test_valid_resolution_increases_trust(self):
        state = TrustState(score=0.5)
        new_score = self.engine.update_on_resolution(state, claim_confidence=0.7, error=0.1, outcome_valid=True)
        self.assertGreater(new_score, 0.5)

    def test_invalid_resolution_decreases_trust(self):
        state = TrustState(score=0.5)
        new_score = self.engine.update_on_resolution(state, claim_confidence=0.7, error=0.5, outcome_valid=False)
        self.assertLess(new_score, 0.5)

    def test_high_confidence_wrong_severe_penalty(self):
        state_high = TrustState(score=0.5)
        state_low = TrustState(score=0.5)

        self.engine.update_on_resolution(state_high, claim_confidence=0.95, error=0.8, outcome_valid=False)
        self.engine.update_on_resolution(state_low, claim_confidence=0.3, error=0.8, outcome_valid=False)

        # High confidence + wrong should be punished much more
        self.assertLess(state_high.score, state_low.score)

    def test_trust_floor(self):
        state = TrustState(score=0.5)
        self.engine.update_on_resolution(state, claim_confidence=1.0, error=1.0, outcome_valid=False)
        self.assertGreaterEqual(state.score, 0.01)

    def test_cannibalization(self):
        winner = TrustState(score=0.5)
        loser = TrustState(score=0.5)
        w_new, l_new = self.engine.cannibalize(winner, loser, attack_confidence=0.8)

        self.assertGreater(w_new, 0.5)
        self.assertLess(l_new, 0.5)
        # Zero-sum: what loser lost, winner gained
        transfer = 0.5 - l_new
        self.assertAlmostEqual(w_new - 0.5, transfer, places=10)

    def test_concession_bonus(self):
        state = TrustState(score=0.5)
        new_score = self.engine.apply_concession(state, confidence_delta=-0.15)
        self.assertGreater(new_score, 0.5)
        self.assertEqual(len(state.history), 1)

    def test_no_bonus_for_positive_delta(self):
        state = TrustState(score=0.5)
        new_score = self.engine.apply_concession(state, confidence_delta=0.1)
        self.assertEqual(new_score, 0.5)

    def test_abstention_bonus(self):
        state = TrustState(score=0.5)
        new_score = self.engine.apply_abstention(state, "insufficient data")
        self.assertGreater(new_score, 0.5)

    def test_attack_budget(self):
        state = TrustState(score=0.5, attack_budget=2)
        self.assertTrue(self.engine.consume_attack(state))
        self.assertTrue(self.engine.consume_attack(state))
        self.assertFalse(self.engine.consume_attack(state))

    def test_budget_reset(self):
        state = TrustState(score=0.5, attack_budget=1)
        self.engine.consume_attack(state)
        self.assertFalse(state.can_attack)
        state.reset_budget()
        self.assertTrue(state.can_attack)

    def test_memory_lock_in(self):
        state = TrustState()
        self.engine.lock_in(state, "C17", "invalid")
        self.assertEqual(state.memory_of_losses["C17"], "invalid")

    def test_trust_based_attack_budget(self):
        self.assertEqual(self.engine.compute_attack_budget(0.8), 5)
        self.assertEqual(self.engine.compute_attack_budget(0.5), 3)
        self.assertEqual(self.engine.compute_attack_budget(0.2), 1)


if __name__ == "__main__":
    unittest.main()
