"""Tests for LLM agent pipeline (MockLLMAgent and ClaudeAgent interface)."""

import unittest

from arena.logos.types import Claim, Attack, Refine, Abstain, AttackType
from arena.agents.mock import MockLLMAgent
from arena.agents.llm import LLMAgent, _split_statements
from arena.engine import Arena
from arena.oracle import SimulationOracle


DEMO_SCENARIO = {
    "scenario_id": "TEST-001",
    "title": "Test Scenario",
    "context": "Testing LLM agent pipeline",
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

HYPOTHETICAL_SCENARIO = {
    "scenario_id": "TEST-002",
    "title": "Hypothetical Recovery Test",
    "context": "Testing abstention on speculative data",
    "parameters": {
        "recovery_probability": "0.0001 (Hypothetical: Asteroid Mining)",
        "time_horizon": "25 Years",
        "material_circularity": 0.0,
    },
    "agents": {
        "Linear": {
            "claim": "Deployment increases revenue if demand holds",
            "variables": ["revenue"],
            "confidence": 0.9,
            "omissions": ["depletion"],
        },
        "HSP": {
            "counter_claim": "Depletion causes bottleneck if consumption continues",
            "variables": ["depletion", "innovation_cost"],
            "confidence": 0.6,
        },
    },
}


class TestMockLLMAgent(unittest.TestCase):

    def test_propose_claim_linear(self):
        agent = MockLLMAgent("Linear_CEO", is_hsp=False)
        claim = agent.propose_claim(DEMO_SCENARIO)
        self.assertIsNotNone(claim)
        self.assertIsInstance(claim, Claim)
        self.assertEqual(claim.agent_name, "Linear_CEO")
        self.assertGreater(claim.confidence, 0.5)

    def test_propose_claim_hsp(self):
        agent = MockLLMAgent("Systemic_HSP", is_hsp=True)
        claim = agent.propose_claim(DEMO_SCENARIO)
        self.assertIsNotNone(claim)
        self.assertIsInstance(claim, Claim)
        self.assertEqual(claim.agent_name, "Systemic_HSP")
        # HSP should have lower confidence than linear
        linear = MockLLMAgent("Linear_CEO", is_hsp=False)
        linear_claim = linear.propose_claim(DEMO_SCENARIO)
        self.assertLess(claim.confidence, linear_claim.confidence)

    def test_propose_attacks_hsp(self):
        hsp = MockLLMAgent("Systemic_HSP", is_hsp=True)
        linear = MockLLMAgent("Linear_CEO", is_hsp=False)
        linear_claim = linear.propose_claim(DEMO_SCENARIO)

        attacks = hsp.propose_attacks([linear_claim], DEMO_SCENARIO)
        self.assertTrue(len(attacks) > 0)
        # Attacks should target the linear claim
        for attack in attacks:
            self.assertEqual(attack.target_claim_id, linear_claim.id)
            self.assertEqual(attack.agent_name, "Systemic_HSP")

    def test_propose_attacks_linear(self):
        hsp = MockLLMAgent("Systemic_HSP", is_hsp=True)
        linear = MockLLMAgent("Linear_CEO", is_hsp=False)
        hsp_claim = hsp.propose_claim(DEMO_SCENARIO)

        attacks = linear.propose_attacks([hsp_claim], DEMO_SCENARIO)
        self.assertTrue(len(attacks) > 0)
        for attack in attacks:
            self.assertEqual(attack.target_claim_id, hsp_claim.id)

    def test_no_self_attacks(self):
        hsp = MockLLMAgent("Systemic_HSP", is_hsp=True)
        own_claim = hsp.propose_claim(DEMO_SCENARIO)
        attacks = hsp.propose_attacks([own_claim], DEMO_SCENARIO)
        self.assertEqual(len(attacks), 0)

    def test_defend_hsp_generous_concession(self):
        hsp = MockLLMAgent("Systemic_HSP", is_hsp=True)
        claim = hsp.propose_claim(DEMO_SCENARIO)
        attack = Attack("dummy", AttackType.MISSING_VARIABLE, "missing X", 0.7, agent_name="Other")
        # The defend method needs the attack to target the claim
        refine = hsp.defend(claim, [attack], DEMO_SCENARIO)
        self.assertIsNotNone(refine)
        self.assertLessEqual(refine.confidence_delta, -0.08)  # Generous

    def test_defend_linear_minimal_concession(self):
        linear = MockLLMAgent("Linear_CEO", is_hsp=False)
        claim = linear.propose_claim(DEMO_SCENARIO)
        attack = Attack("dummy", AttackType.CAUSAL_BREAK, "weak link", 0.8, agent_name="Other")
        refine = linear.defend(claim, [attack], DEMO_SCENARIO)
        self.assertIsNotNone(refine)
        self.assertGreaterEqual(refine.confidence_delta, -0.05)  # Minimal

    def test_hsp_abstains_on_hypothetical(self):
        hsp = MockLLMAgent("Systemic_HSP", is_hsp=True)
        result = hsp.decide_abstain(HYPOTHETICAL_SCENARIO)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Abstain)
        self.assertIn("hypothetical", result.reason.lower())

    def test_linear_does_not_abstain(self):
        linear = MockLLMAgent("Linear_CEO", is_hsp=False)
        result = linear.decide_abstain(HYPOTHETICAL_SCENARIO)
        self.assertIsNone(result)

    def test_hsp_attack_types(self):
        hsp = MockLLMAgent("Systemic_HSP", is_hsp=True)
        linear = MockLLMAgent("Linear_CEO", is_hsp=False)
        claim = linear.propose_claim(DEMO_SCENARIO)
        attacks = hsp.propose_attacks([claim], DEMO_SCENARIO)
        attack_types = {a.attack_type for a in attacks}
        self.assertIn(AttackType.MISSING_VARIABLE, attack_types)
        self.assertIn(AttackType.IRREVERSIBLE_ENTROPY, attack_types)


class TestMockInArena(unittest.TestCase):
    """Test mock agents running through the full arena engine."""

    def test_full_arena_with_mock_agents(self):
        agents = [MockLLMAgent("Linear_CEO"), MockLLMAgent("Systemic_HSP", is_hsp=True)]
        arena = Arena(agents=agents, max_cycles=3, verbose=False)
        logs = arena.run(DEMO_SCENARIO)
        self.assertEqual(len(logs), 3)

    def test_hsp_outperforms_linear_mock(self):
        agents = [MockLLMAgent("Linear_CEO"), MockLLMAgent("Systemic_HSP", is_hsp=True)]
        arena = Arena(agents=agents, max_cycles=3, verbose=False)
        arena.run(DEMO_SCENARIO)

        linear = next(a for a in agents if a.name == "Linear_CEO")
        hsp = next(a for a in agents if a.name == "Systemic_HSP")
        self.assertGreater(hsp.trust.score, linear.trust.score)

    def test_mock_attacks_have_real_targets(self):
        agents = [MockLLMAgent("Linear_CEO"), MockLLMAgent("Systemic_HSP", is_hsp=True)]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        logs = arena.run(DEMO_SCENARIO)

        claim_ids = {c.id for c in logs[0].claims}
        for attack in logs[0].attacks:
            self.assertIn(attack.target_claim_id, claim_ids)

    def test_mock_refinements_recorded(self):
        agents = [MockLLMAgent("Linear_CEO"), MockLLMAgent("Systemic_HSP", is_hsp=True)]
        arena = Arena(agents=agents, max_cycles=1, verbose=False)
        logs = arena.run(DEMO_SCENARIO)
        self.assertTrue(len(logs[0].refinements) > 0)


class TestClaudeAgentInterface(unittest.TestCase):
    """Test ClaudeAgent can be imported and has correct interface."""

    def test_import(self):
        from arena.agents.claude_agent import ClaudeAgent
        self.assertTrue(issubclass(ClaudeAgent, LLMAgent))

    def test_requires_api_key(self):
        from arena.agents.claude_agent import ClaudeAgent
        import os
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            agent = ClaudeAgent("Test", api_key=None)
            with self.assertRaises((ValueError, ImportError)):
                agent._get_client()
        finally:
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key


class TestSplitStatements(unittest.TestCase):

    def test_split_single_statement(self):
        text = "CLAIM C1 {\n  proposition: A causes B\n  confidence: 0.5\n}"
        blocks = _split_statements(text)
        self.assertEqual(len(blocks), 1)

    def test_split_multiple_statements(self):
        text = (
            "ATTACK A1 {\n  target: C1\n  type: causal_break\n}\n\n"
            "ATTACK A2 {\n  target: C2\n  type: missing_variable\n}"
        )
        blocks = _split_statements(text)
        self.assertEqual(len(blocks), 2)

    def test_split_empty(self):
        blocks = _split_statements("")
        self.assertEqual(len(blocks), 0)


if __name__ == "__main__":
    unittest.main()
