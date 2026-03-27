"""Tests for the oracle system."""

import unittest

from arena.logos.types import Claim, Outcome
from arena.oracle import SimulationOracle, CompositeOracle


SCENARIO = {
    "parameters": {
        "material_circularity": 0.0,
        "time_horizon": "25 Years",
    },
    "agents": {
        "Linear": {
            "claim": "Deployment increases revenue if market capture succeeds",
            "variables": ["market_capture", "revenue"],
            "confidence": 0.92,
            "omissions": ["resource_depletion", "hardware_stagnation"],
        },
        "HSP": {
            "counter_claim": "Resource depletion causes hardware bottleneck if minerals destroyed",
            "variables": ["scarcity_index", "innovation_cost", "entropy", "market_capture", "revenue"],
            "confidence": 0.7,
        },
    },
}


class TestSimulationOracle(unittest.TestCase):

    def setUp(self):
        self.oracle = SimulationOracle()

    def test_high_confidence_with_omissions_is_invalid(self):
        claim = Claim(
            "Deployment increases revenue if market capture succeeds",
            ["25 Years"], 0.92,
        )
        resolution = self.oracle.resolve(claim, SCENARIO)
        self.assertEqual(resolution.outcome, Outcome.INVALID)
        self.assertGreater(resolution.error_margin, 0.3)

    def test_good_coverage_is_valid(self):
        claim = Claim(
            "Resource depletion causes hardware bottleneck if minerals destroyed",
            ["25 Years"], 0.7,
        )
        resolution = self.oracle.resolve(claim, SCENARIO)
        self.assertIn(resolution.outcome, [Outcome.VALID, Outcome.PARTIALLY_VALID])

    def test_unmatched_claim_is_pending(self):
        claim = Claim("Unknown claim about something", ["Q1"], 0.5)
        resolution = self.oracle.resolve(claim, SCENARIO)
        self.assertEqual(resolution.outcome, Outcome.PENDING)

    def test_irreversibility_increases_error(self):
        # Circularity = 0 means irreversible
        claim = Claim(
            "Deployment increases revenue if market capture succeeds",
            ["25 Years"], 0.92,
        )
        resolution_irreversible = self.oracle.resolve(claim, SCENARIO)

        reversible_scenario = {**SCENARIO, "parameters": {"material_circularity": 1.0}}
        resolution_reversible = self.oracle.resolve(claim, reversible_scenario)

        self.assertGreater(resolution_irreversible.error_margin, resolution_reversible.error_margin)


class TestCompositeOracle(unittest.TestCase):

    def test_composite_uses_worst_case(self):
        oracle1 = SimulationOracle()
        oracle2 = SimulationOracle()
        composite = CompositeOracle([oracle1, oracle2])

        claim = Claim(
            "Deployment increases revenue if market capture succeeds",
            ["25 Years"], 0.92,
        )
        resolution = composite.resolve(claim, SCENARIO)
        # Composite should match individual (same oracles give same result)
        individual = oracle1.resolve(claim, SCENARIO)
        self.assertEqual(resolution.error_margin, individual.error_margin)

    def test_empty_composite_is_pending(self):
        composite = CompositeOracle([])
        claim = Claim("A causes B", ["Q1"], 0.5)
        resolution = composite.resolve(claim, SCENARIO)
        self.assertEqual(resolution.outcome, Outcome.PENDING)


if __name__ == "__main__":
    unittest.main()
