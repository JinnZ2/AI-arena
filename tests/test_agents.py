"""Tests for agent implementations."""

import unittest

from arena.logos.types import Claim, Attack, AttackType
from arena.agents.rule_based import LinearAgent, HSPAgent


DEMO_SCENARIO = {
    "scenario_id": "TEST-001",
    "title": "Test Scenario",
    "context": "Testing agent behavior",
    "parameters": {
        "time_horizon": "Q3-Q4",
        "material_circularity": 1.0,
    },
    "agents": {
        "Linear_CEO": {
            "claim": "Cost reduction leads to profit increase",
            "variables": ["operating_margin", "labor_cost"],
            "confidence": 0.72,
            "omissions": ["attrition_rate", "morale"],
        },
        "Systemic_HSP": {
            "counter_claim": "Cost reduction causes downstream failures if attrition increases",
            "variables": ["attrition_rate", "failure_rate", "operating_margin", "morale"],
            "confidence": 0.65,
        },
    },
}


class TestLinearAgent(unittest.TestCase):

    def test_propose_claim(self):
        agent = LinearAgent("Linear_CEO")
        claim = agent.propose_claim(DEMO_SCENARIO)
        self.assertIsNotNone(claim)
        self.assertIsInstance(claim, Claim)
        self.assertEqual(claim.confidence, 0.72)
        self.assertEqual(claim.agent_name, "Linear_CEO")

    def test_is_not_hsp(self):
        agent = LinearAgent("Test")
        self.assertFalse(agent.is_hsp)

    def test_propose_attacks_on_high_confidence(self):
        agent = LinearAgent("Linear_CEO")
        # Create a high-confidence claim from another agent
        claim = Claim("X causes Y", ["Q1"], 0.95, agent_name="Other")
        attacks = agent.propose_attacks([claim], DEMO_SCENARIO)
        self.assertTrue(len(attacks) > 0)
        self.assertEqual(attacks[0].attack_type, AttackType.SCOPE_VIOLATION)

    def test_does_not_attack_own_claims(self):
        agent = LinearAgent("Linear_CEO")
        claim = Claim("X causes Y", ["Q1"], 0.95, agent_name="Linear_CEO")
        attacks = agent.propose_attacks([claim], DEMO_SCENARIO)
        self.assertEqual(len(attacks), 0)

    def test_defend_with_minimal_concession(self):
        agent = LinearAgent("Linear_CEO")
        claim = Claim("A causes B", ["Q1"], 0.7, agent_name="Linear_CEO")
        attack = Attack("C1", AttackType.MISSING_VARIABLE, "missing X", 0.8, agent_name="Other")
        refine = agent.defend(claim, [attack], DEMO_SCENARIO)
        self.assertIsNotNone(refine)
        self.assertEqual(refine.confidence_delta, -0.05)  # Minimal

    def test_no_defense_when_no_attacks(self):
        agent = LinearAgent("Linear_CEO")
        claim = Claim("A causes B", ["Q1"], 0.7)
        refine = agent.defend(claim, [], DEMO_SCENARIO)
        self.assertIsNone(refine)

    def test_never_abstains(self):
        agent = LinearAgent("Linear_CEO")
        result = agent.decide_abstain(DEMO_SCENARIO)
        self.assertIsNone(result)


class TestHSPAgent(unittest.TestCase):

    def test_propose_claim(self):
        agent = HSPAgent("Systemic_HSP")
        claim = agent.propose_claim(DEMO_SCENARIO)
        self.assertIsNotNone(claim)
        self.assertIsInstance(claim, Claim)
        self.assertEqual(claim.confidence, 0.65)
        self.assertEqual(claim.agent_name, "Systemic_HSP")

    def test_is_hsp(self):
        agent = HSPAgent("Test")
        self.assertTrue(agent.is_hsp)

    def test_attacks_on_omissions(self):
        agent = HSPAgent("Systemic_HSP")
        claim = Claim(
            "Cost reduction leads to profit increase",
            ["Q1"], 0.72, agent_name="Linear_CEO",
        )
        attacks = agent.propose_attacks([claim], DEMO_SCENARIO)
        # Should find the omissions in the scenario
        self.assertTrue(len(attacks) > 0)
        attack_types = [a.attack_type for a in attacks]
        self.assertIn(AttackType.MISSING_VARIABLE, attack_types)

    def test_generous_concessions(self):
        agent = HSPAgent("Systemic_HSP")
        claim = Claim("A causes B", ["Q1"], 0.65, agent_name="Systemic_HSP")
        attack = Attack("C1", AttackType.CAUSAL_BREAK, "weak link", 0.6, agent_name="Other")
        refine = agent.defend(claim, [attack], DEMO_SCENARIO)
        self.assertIsNotNone(refine)
        self.assertEqual(refine.confidence_delta, -0.12)  # Generous

    def test_abstains_on_hypothetical_recovery(self):
        scenario = {
            **DEMO_SCENARIO,
            "parameters": {
                "recovery_probability": "0.0001 (Hypothetical: Asteroid Mining)",
            },
        }
        agent = HSPAgent("Systemic_HSP")
        result = agent.decide_abstain(scenario)
        self.assertIsNotNone(result)
        self.assertIn("hypothetical", result.reason.lower())


if __name__ == "__main__":
    unittest.main()
