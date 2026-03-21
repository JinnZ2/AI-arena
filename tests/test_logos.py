"""Tests for LOGOS parser, types, and validator."""

import unittest

from arena.logos.types import Claim, Attack, Refine, Abstain, Resolution, AttackType, Outcome
from arena.logos.parser import parse_statement, parse_from_dict
from arena.logos.validator import (
    validate_claim, validate_attack, validate_refine, validate_abstain, ValidationError,
)


class TestTypes(unittest.TestCase):

    def test_claim_creation(self):
        claim = Claim("profit ↑ if headcount ↓", ["Q3", "Q4"], 0.61)
        self.assertEqual(claim.proposition, "profit ↑ if headcount ↓")
        self.assertEqual(claim.scope, ["Q3", "Q4"])
        self.assertEqual(claim.confidence, 0.61)
        self.assertTrue(len(claim.id) == 8)

    def test_attack_type_enum(self):
        self.assertEqual(AttackType.CAUSAL_BREAK.value, "causal_break")
        self.assertEqual(AttackType.MISSING_VARIABLE.value, "missing_variable")
        with self.assertRaises(ValueError):
            AttackType("made_up_type")

    def test_outcome_enum(self):
        self.assertEqual(Outcome.VALID.value, "valid")
        self.assertEqual(Outcome.INVALID.value, "invalid")

    def test_claim_repr(self):
        claim = Claim("A → B", ["Q1"], 0.5)
        text = repr(claim)
        self.assertIn("CLAIM", text)
        self.assertIn("A → B", text)


class TestValidator(unittest.TestCase):

    def test_valid_claim(self):
        claim = Claim("profit ↑ if headcount ↓", ["Q3", "Q4"], 0.61)
        errors = validate_claim(claim)
        self.assertEqual(errors, [])

    def test_confidence_out_of_range(self):
        claim = Claim("A → B", ["Q1"], 0.0)
        errors = validate_claim(claim)
        self.assertTrue(any("Confidence" in e for e in errors))

        claim2 = Claim("A → B", ["Q1"], 1.5)
        errors2 = validate_claim(claim2)
        self.assertTrue(any("Confidence" in e for e in errors2))

    def test_empty_proposition(self):
        claim = Claim("", ["Q1"], 0.5)
        errors = validate_claim(claim)
        self.assertTrue(any("empty" in e.lower() for e in errors))

    def test_non_falsifiable_proposition(self):
        claim = Claim("things will be fine", ["Q1"], 0.5)
        errors = validate_claim(claim)
        self.assertTrue(any("falsifiable" in e.lower() for e in errors))

    def test_empty_scope(self):
        claim = Claim("A → B", [], 0.5)
        errors = validate_claim(claim)
        self.assertTrue(any("scope" in e.lower() for e in errors))

    def test_low_trust_high_confidence_rejected(self):
        claim = Claim("A → B", ["Q1"], 0.9, assumptions=["stable demand"])
        errors = validate_claim(claim, agent_trust=0.2)
        self.assertTrue(any("Low-trust" in e for e in errors))

    def test_low_trust_needs_assumptions(self):
        claim = Claim("A → B", ["Q1"], 0.5)
        errors = validate_claim(claim, agent_trust=0.2)
        self.assertTrue(any("assumptions" in e.lower() for e in errors))

    def test_valid_attack(self):
        attack = Attack("C17", AttackType.MISSING_VARIABLE, "missing attrition rate", 0.74)
        errors = validate_attack(attack)
        self.assertEqual(errors, [])

    def test_refine_must_change_confidence(self):
        refine = Refine("C17", "narrow scope", 0.0)
        errors = validate_refine(refine)
        self.assertTrue(any("confidence_delta" in e.lower() or "cannot be 0" in e for e in errors))

    def test_valid_refine(self):
        refine = Refine("C17", "narrow scope", -0.12)
        errors = validate_refine(refine)
        self.assertEqual(errors, [])

    def test_refine_resulting_confidence_bounds(self):
        refine = Refine("C17", "narrow scope", -0.6)
        errors = validate_refine(refine, original_confidence=0.5)
        self.assertTrue(any("Resulting confidence" in e for e in errors))

    def test_abstain_needs_reason(self):
        abstain = Abstain("")
        errors = validate_abstain(abstain)
        self.assertTrue(len(errors) > 0)


class TestParser(unittest.TestCase):

    def test_parse_claim_text(self):
        text = """CLAIM C17 {
  proposition: profit ↑ if headcount ↓
  scope: Q3-Q4
  confidence: 0.61
  assumptions: [stable demand, no attrition shock]
}"""
        claim = parse_statement(text)
        self.assertIsInstance(claim, Claim)
        self.assertEqual(claim.id, "C17")
        self.assertEqual(claim.confidence, 0.61)
        self.assertIn("stable demand", claim.assumptions)

    def test_parse_attack_text(self):
        text = """ATTACK A09 {
  target: C17
  type: missing_variable
  argument: attrition causes failure_rate increase
  confidence: 0.74
}"""
        attack = parse_statement(text)
        self.assertIsInstance(attack, Attack)
        self.assertEqual(attack.target_claim_id, "C17")
        self.assertEqual(attack.attack_type, AttackType.MISSING_VARIABLE)

    def test_parse_refine_text(self):
        text = """REFINE R04 {
  target: C17
  modification: limit reduction to non-core roles
  confidence_delta: -0.12
}"""
        refine = parse_statement(text)
        self.assertIsInstance(refine, Refine)
        self.assertEqual(refine.confidence_delta, -0.12)

    def test_parse_abstain_text(self):
        text = """ABSTAIN {
  reason: insufficient data
}"""
        abstain = parse_statement(text)
        self.assertIsInstance(abstain, Abstain)
        self.assertEqual(abstain.reason, "insufficient data")

    def test_parse_resolution_text(self):
        text = """RESOLUTION {
  claim: C17
  outcome: partially_valid
  error: 0.18
}"""
        resolution = parse_statement(text)
        self.assertIsInstance(resolution, Resolution)
        self.assertEqual(resolution.outcome, Outcome.PARTIALLY_VALID)

    def test_parse_invalid_type(self):
        with self.assertRaises(ValidationError):
            parse_statement("NONSENSE { foo: bar }")

    def test_parse_claim_dict(self):
        data = {
            "proposition": "A causes B",
            "scope": ["Q1"],
            "confidence": 0.6,
            "assumptions": ["stable demand"],
        }
        claim = parse_from_dict(data, "claim")
        self.assertIsInstance(claim, Claim)
        self.assertEqual(claim.confidence, 0.6)

    def test_parse_invalid_attack_type_raises(self):
        with self.assertRaises(ValidationError):
            text = """ATTACK A01 {
  target: C17
  type: creative_attack
  argument: some argument
  confidence: 0.5
}"""
            parse_statement(text)


if __name__ == "__main__":
    unittest.main()
