"""Tests for the evolving agent memory system."""

import unittest

from arena.trust import TrustEngine, TrustState, MemoryEntry
from arena.agents.rule_based import LinearAgent, HSPAgent
from arena.agents.mock import MockLLMAgent
from arena.engine import Arena


DEMO_SCENARIO = {
    "scenario_id": "TEST-001",
    "title": "Test: Memory Evolution",
    "context": "Testing memory-driven adaptation",
    "parameters": {"time_horizon": "Q3-Q4", "material_circularity": 1.0},
    "agents": {
        "Linear_CEO": {
            "claim": "Reducing headcount increases operating margin",
            "variables": ["operating_margin", "labor_cost"],
            "confidence": 0.72,
            "omissions": ["attrition_rate", "institutional_memory_loss"],
        },
        "Systemic_HSP": {
            "counter_claim": "Headcount reduction causes downstream failure if attrition increases",
            "variables": ["attrition_rate", "failure_rate", "institutional_memory", "operating_margin", "morale"],
            "confidence": 0.65,
        },
    },
}


class TestMemoryEntry(unittest.TestCase):

    def test_memory_entry_creation(self):
        entry = MemoryEntry(
            claim_id="C1", proposition="A causes B",
            confidence=0.7, outcome="invalid", error=0.5, cycle=1,
        )
        self.assertEqual(entry.outcome, "invalid")
        self.assertEqual(entry.error, 0.5)

    def test_memory_entry_with_attacks(self):
        entry = MemoryEntry(
            claim_id="C1", proposition="A causes B",
            confidence=0.7, outcome="invalid", error=0.5, cycle=1,
            attacks_received=["missing variable X", "scope violation"],
        )
        self.assertEqual(len(entry.attacks_received), 2)


class TestTrustStateMemory(unittest.TestCase):

    def test_loss_count(self):
        state = TrustState()
        state.memory.append(MemoryEntry("C1", "A", 0.7, "invalid", 0.5, 1))
        state.memory.append(MemoryEntry("C2", "B", 0.6, "valid", 0.1, 2))
        state.memory.append(MemoryEntry("C3", "C", 0.5, "partially_valid", 0.3, 3))
        self.assertEqual(state.loss_count, 2)  # invalid + partially_valid
        self.assertEqual(state.win_count, 1)

    def test_avg_error(self):
        state = TrustState()
        state.memory.append(MemoryEntry("C1", "A", 0.7, "invalid", 0.6, 1))
        state.memory.append(MemoryEntry("C2", "B", 0.6, "valid", 0.2, 2))
        self.assertAlmostEqual(state.avg_error, 0.4)

    def test_avg_error_empty(self):
        state = TrustState()
        self.assertEqual(state.avg_error, 0.0)

    def test_has_failed_similar(self):
        state = TrustState()
        state.memory.append(MemoryEntry(
            "C1", "reducing headcount increases profit margin", 0.7,
            "invalid", 0.5, 1,
        ))
        self.assertTrue(state.has_failed_similar("reducing headcount increases operating margin"))
        self.assertFalse(state.has_failed_similar("launching satellites depletes rare earth minerals"))

    def test_get_failed_attacks(self):
        state = TrustState()
        state.memory.append(MemoryEntry(
            "C1", "A", 0.7, "invalid", 0.5, 1,
            attacks_received=["missing attrition variable", "scope too wide"],
        ))
        state.memory.append(MemoryEntry(
            "C2", "B", 0.6, "valid", 0.1, 2,
            attacks_received=["weak data"],
        ))
        # Only attacks from failures
        attacks = state.get_failed_attacks()
        self.assertEqual(len(attacks), 2)
        self.assertIn("missing attrition variable", attacks)

    def test_suggested_confidence_all_losses(self):
        state = TrustState()
        state.memory.append(MemoryEntry("C1", "A", 0.7, "invalid", 0.5, 1))
        state.memory.append(MemoryEntry("C2", "B", 0.6, "invalid", 0.6, 2))
        adj = state.suggested_confidence_adjustment()
        self.assertLess(adj, 0)  # Should suggest lowering confidence

    def test_suggested_confidence_all_wins(self):
        state = TrustState()
        state.memory.append(MemoryEntry("C1", "A", 0.5, "valid", 0.1, 1))
        state.memory.append(MemoryEntry("C2", "B", 0.6, "valid", 0.05, 2))
        adj = state.suggested_confidence_adjustment()
        self.assertGreater(adj, 0)  # Should suggest slight increase

    def test_suggested_confidence_empty(self):
        state = TrustState()
        self.assertEqual(state.suggested_confidence_adjustment(), 0.0)


class TestDoublingDown(unittest.TestCase):

    def test_doubling_down_increases_penalty(self):
        engine = TrustEngine()

        normal = TrustState(score=0.5)
        doubler = TrustState(score=0.5)

        engine.update_on_resolution(normal, 0.7, 0.5, False, is_doubling_down=False)
        engine.update_on_resolution(doubler, 0.7, 0.5, False, is_doubling_down=True)

        self.assertLess(doubler.score, normal.score)

    def test_rich_lock_in(self):
        engine = TrustEngine()
        state = TrustState()
        engine.lock_in(
            state, "C1", "invalid",
            proposition="A causes B", confidence=0.7, error=0.5,
            cycle=1, attacks_received=["missing X"],
        )
        self.assertEqual(len(state.memory), 1)
        self.assertEqual(state.memory[0].proposition, "A causes B")
        self.assertEqual(state.memory[0].attacks_received, ["missing X"])
        # Legacy still works
        self.assertEqual(state.memory_of_losses["C1"], "invalid")


class TestMemoryDrivenAgents(unittest.TestCase):

    def test_linear_lowers_confidence_after_losses(self):
        agent = LinearAgent("Linear_CEO")
        # Simulate past losses
        agent.trust.memory.append(MemoryEntry("C1", "X increases Y", 0.72, "partially_valid", 0.5, 1))
        agent.trust.memory.append(MemoryEntry("C2", "X increases Y", 0.72, "invalid", 0.7, 2))

        claim = agent.propose_claim(DEMO_SCENARIO)
        self.assertIsNotNone(claim)
        # Should be lower than the scenario's 0.72
        self.assertLess(claim.confidence, 0.72)

    def test_linear_adds_learned_assumptions(self):
        agent = LinearAgent("Linear_CEO")
        agent.trust.memory.append(MemoryEntry(
            "C1", "X", 0.7, "invalid", 0.5, 1,
            attacks_received=["ignoring attrition rate"],
        ))
        claim = agent.propose_claim(DEMO_SCENARIO)
        # Should have a "noted_" assumption from past attacks
        noted = [a for a in claim.assumptions if a.startswith("noted_")]
        self.assertTrue(len(noted) > 0)

    def test_linear_concedes_more_after_losses(self):
        from arena.logos.types import Claim, Attack, AttackType

        agent = LinearAgent("Linear_CEO")
        # After 3 losses, concession should be larger
        for i in range(3):
            agent.trust.memory.append(MemoryEntry(f"C{i}", "X", 0.7, "invalid", 0.5, i))

        claim = Claim("A causes B", ["Q1"], 0.7, agent_name="Linear_CEO")
        attack = Attack("X", AttackType.MISSING_VARIABLE, "missing X", 0.8, agent_name="Other")
        refine = agent.defend(claim, [attack], DEMO_SCENARIO)
        self.assertIsNotNone(refine)
        self.assertLessEqual(refine.confidence_delta, -0.08)

    def test_linear_abstains_after_many_losses(self):
        agent = LinearAgent("Linear_CEO")
        agent.trust.score = 0.2
        for i in range(4):
            agent.trust.memory.append(MemoryEntry(f"C{i}", "X", 0.7, "invalid", 0.5, i))

        result = agent.decide_abstain(DEMO_SCENARIO)
        self.assertIsNotNone(result)

    def test_hsp_increases_attack_confidence_after_wins(self):
        agent = HSPAgent("Systemic_HSP")
        # Simulate past wins
        for i in range(3):
            agent.trust.memory.append(MemoryEntry(f"C{i}", "X causes Y", 0.6, "valid", 0.1, i))

        from arena.logos.types import Claim
        claim = Claim("Cost reduction leads to profit increase", ["Q1"], 0.72, agent_name="Linear_CEO")
        attacks = agent.propose_attacks([claim], DEMO_SCENARIO)
        # Attack confidence should be above base 0.75
        if attacks:
            max_conf = max(a.confidence for a in attacks)
            self.assertGreater(max_conf, 0.75)

    def test_hsp_incorporates_lessons_in_assumptions(self):
        agent = HSPAgent("Systemic_HSP")
        agent.trust.memory.append(MemoryEntry(
            "C1", "X", 0.6, "partially_valid", 0.3, 1,
            attacks_received=["scope too narrow for systemic effects"],
        ))
        claim = agent.propose_claim(DEMO_SCENARIO)
        learned = [a for a in claim.assumptions if a.startswith("learned:")]
        self.assertTrue(len(learned) > 0)


class TestMemoryInArena(unittest.TestCase):

    def test_memory_grows_each_cycle(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=3, verbose=False)
        arena.run(DEMO_SCENARIO)

        for agent in agents:
            self.assertEqual(len(agent.trust.memory), 3)

    def test_memory_contains_attack_arguments(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        arena.run(DEMO_SCENARIO)

        linear = next(a for a in agents if a.name == "Linear_CEO")
        # Linear should have received attacks
        if linear.trust.memory:
            entry = linear.trust.memory[0]
            self.assertTrue(len(entry.attacks_received) > 0)

    def test_doubling_down_detected_in_arena(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=3, verbose=False)
        logs = arena.run(DEMO_SCENARIO)

        # After cycle 1, Linear should be flagged for doubling down in cycle 2+
        for log in logs[1:]:
            for change in log.trust_changes:
                if change["agent"] == "Linear_CEO":
                    self.assertIn("doubling_down", change)

    def test_mock_agents_adapt_confidence(self):
        agents = [MockLLMAgent("Linear_CEO"), MockLLMAgent("Systemic_HSP", is_hsp=True)]
        arena = Arena(agents=agents, max_cycles=3, verbose=False)
        logs = arena.run(DEMO_SCENARIO)

        # Collect Linear's claim confidences across cycles
        linear_confidences = []
        for log in logs:
            for claim in log.claims:
                if claim.agent_name == "Linear_CEO":
                    linear_confidences.append(claim.confidence)

        # After losses, confidence should trend downward
        if len(linear_confidences) >= 2:
            self.assertLessEqual(linear_confidences[-1], linear_confidences[0])


if __name__ == "__main__":
    unittest.main()
