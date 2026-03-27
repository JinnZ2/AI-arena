"""Tests for the full arena engine."""

import unittest

from arena.agents.rule_based import LinearAgent, HSPAgent
from arena.engine import Arena
from arena.oracle import SimulationOracle


DEMO_SCENARIO = {
    "scenario_id": "TEST-001",
    "title": "Test: Headcount Reduction",
    "context": "CEO proposes headcount reduction.",
    "parameters": {
        "time_horizon": "Q3-Q4",
        "material_circularity": 1.0,
    },
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


class TestArena(unittest.TestCase):

    def test_arena_runs_without_error(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        logs = arena.run(DEMO_SCENARIO)
        self.assertEqual(len(logs), 1)

    def test_hsp_outperforms_linear(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=3, verbose=False)
        arena.run(DEMO_SCENARIO)

        linear = next(a for a in agents if a.name == "Linear_CEO")
        hsp = next(a for a in agents if a.name == "Systemic_HSP")
        self.assertGreater(hsp.trust.score, linear.trust.score)

    def test_cycle_log_records_claims(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        logs = arena.run(DEMO_SCENARIO)

        self.assertTrue(len(logs[0].claims) > 0)

    def test_cycle_log_records_attacks(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        logs = arena.run(DEMO_SCENARIO)

        # HSP should attack linear's omissions
        self.assertTrue(len(logs[0].attacks) > 0)

    def test_cycle_log_records_resolutions(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        logs = arena.run(DEMO_SCENARIO)

        self.assertTrue(len(logs[0].resolutions) > 0)

    def test_memory_lock_in_persists(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=2, verbose=False)
        arena.run(DEMO_SCENARIO)

        for agent in agents:
            self.assertTrue(len(agent.trust.memory_of_losses) > 0)

    def test_load_scenario_file(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        scenario = arena.load_scenario("scenarios/scen_01_material_extinction.json")
        self.assertIn("title", scenario)
        self.assertIn("agents", scenario)

    def test_no_scenario_raises(self):
        agents = [LinearAgent("Linear_CEO")]
        arena = Arena(agents=agents, verbose=False)
        with self.assertRaises(ValueError):
            arena.run()

    def test_multiple_cycles_trust_diverges(self):
        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, max_cycles=5, verbose=False)
        arena.run(DEMO_SCENARIO)

        linear = next(a for a in agents if a.name == "Linear_CEO")
        hsp = next(a for a in agents if a.name == "Systemic_HSP")

        # After 5 cycles the gap should be significant
        gap = hsp.trust.score - linear.trust.score
        self.assertGreater(gap, 0.05)


if __name__ == "__main__":
    unittest.main()
