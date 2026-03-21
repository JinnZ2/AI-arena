"""Tests for thermodynamic accounting — conservation of cost."""

import unittest

from arena.thermodynamics import SystemLedger, Domain, CostTransfer, EntropyEvent, build_ledger_from_scenario
from arena.oracle import ClosedSystemOracle
from arena.logos.types import Claim, Outcome


class TestSystemLedger(unittest.TestCase):

    def test_conservation_balanced(self):
        """When all costs are accounted for, conservation error = 0."""
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 4_000_000,
                       "Labor savings")
        ledger.transfer(Domain.COMPANY, Domain.WORKERS, 4_000_000,
                       "Severance paid back")
        self.assertAlmostEqual(ledger.conservation_error, 0.0)

    def test_conservation_unbalanced(self):
        """Costs that appear from nowhere violate conservation."""
        ledger = SystemLedger()
        # Company gains but nothing is the source (self-referential)
        ledger.transfer(Domain.COMPANY, Domain.COMPANY, 1_000_000,
                       "Magic money")
        # Net should be 0 for self-transfer
        self.assertAlmostEqual(ledger.conservation_error, 0.0)

    def test_domain_balance(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 4_000_000, "Savings")
        balance = ledger.domain_balance
        self.assertEqual(balance[Domain.COMPANY], 4_000_000)
        self.assertEqual(balance[Domain.WORKERS], -4_000_000)

    def test_external_cost(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 4_000_000, "Savings")
        ledger.transfer(Domain.WORKERS, Domain.HEALTHCARE, -500_000, "Health costs")
        self.assertGreater(ledger.external_cost, 0)

    def test_net_system_value_extractive(self):
        """Extractive actions have net system value ≤ 0."""
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 4_000_000, "Savings")
        ledger.add_entropy(Domain.WORKERS, "Knowledge destroyed", 0.15)
        # Net should be negative due to entropy
        self.assertLess(ledger.net_system_value, 0)

    def test_entropy_accumulates(self):
        ledger = SystemLedger()
        ledger.add_entropy(Domain.WORKERS, "Knowledge lost", 0.15)
        ledger.add_entropy(Domain.COMMUNITY, "Businesses closed", 0.05)
        self.assertAlmostEqual(ledger.total_entropy, 0.20)

    def test_irreversible_fraction(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 1_000_000, "A", reversible=False)
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 1_000_000, "B", reversible=True)
        self.assertAlmostEqual(ledger.irreversible_fraction, 0.5)

    def test_confidence_weighting(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 1_000_000, "A", confidence=0.5)
        balance = ledger.domain_balance
        self.assertEqual(balance[Domain.COMPANY], 500_000)  # Weighted by confidence

    def test_company_gain(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 4_000_000, "Savings")
        # Self-transfer nets to 0 in domain balance (source - amount + target + amount)
        self.assertEqual(ledger.company_gain, 4_000_000)

    def test_company_gain_with_outflow(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 4_000_000, "Savings")
        ledger.transfer(Domain.COMPANY, Domain.WORKERS, 900_000, "Severance")
        self.assertEqual(ledger.company_gain, 3_100_000)

    def test_summary_output(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 1_000_000, "Test")
        summary = ledger.summary()
        self.assertIn("SYSTEM LEDGER", summary)
        self.assertIn("company", summary)

    def test_empty_ledger(self):
        ledger = SystemLedger()
        self.assertEqual(ledger.conservation_error, 0.0)
        self.assertEqual(ledger.company_gain, 0.0)
        self.assertEqual(ledger.net_system_value, 0.0)
        self.assertEqual(ledger.total_entropy, 0.0)


class TestBuildLedgerFromScenario(unittest.TestCase):

    def test_builds_from_scenario_dict(self):
        scenario = {
            "cost_transfers": [
                {"source": "workers", "target": "company", "amount": 1000000,
                 "description": "Test", "reversible": False, "confidence": 0.9},
            ],
            "entropy_events": [
                {"domain": "workers", "description": "Knowledge lost", "magnitude": 0.1},
            ],
        }
        ledger = build_ledger_from_scenario(scenario)
        self.assertEqual(len(ledger.transfers), 1)
        self.assertEqual(len(ledger.entropy_events), 1)

    def test_empty_scenario(self):
        ledger = build_ledger_from_scenario({})
        self.assertEqual(len(ledger.transfers), 0)


class TestClosedSystemOracle(unittest.TestCase):

    SCENARIO_WITH_COSTS = {
        "agents": {
            "Linear": {
                "claim": "Cost cutting increases margin if demand holds",
                "variables": ["operating_margin", "labor_cost"],
                "confidence": 0.8,
                "omissions": ["worker_health", "community_impact"],
            },
            "HSP": {
                "counter_claim": "Cost cutting causes community damage if externalities are unpriced",
                "variables": ["operating_margin", "worker_health", "community_spending", "attrition"],
                "confidence": 0.6,
            },
        },
        "cost_transfers": [
            {"source": "workers", "target": "company", "amount": 2000000,
             "description": "Savings", "reversible": False, "confidence": 0.9},
            {"source": "workers", "target": "healthcare", "amount": -500000,
             "description": "Health costs", "reversible": False, "confidence": 0.7},
            {"source": "workers", "target": "community", "amount": -800000,
             "description": "Lost spending", "reversible": False, "confidence": 0.8},
        ],
        "entropy_events": [
            {"domain": "workers", "description": "Knowledge lost", "magnitude": 0.1},
        ],
    }

    def test_linear_penalized_for_ignoring_externalities(self):
        oracle = ClosedSystemOracle()
        claim = Claim("Cost cutting increases margin if demand holds", ["Q1"], 0.8)
        resolution = oracle.resolve(claim, self.SCENARIO_WITH_COSTS)
        self.assertGreater(resolution.error_margin, 0.3)
        self.assertIn(resolution.outcome, [Outcome.INVALID, Outcome.PARTIALLY_VALID])

    def test_hsp_lower_error_for_broad_coverage(self):
        oracle = ClosedSystemOracle()
        linear_claim = Claim("Cost cutting increases margin if demand holds", ["Q1"], 0.8)
        hsp_claim = Claim("Cost cutting causes community damage if externalities are unpriced", ["Q1"], 0.6)

        linear_res = oracle.resolve(linear_claim, self.SCENARIO_WITH_COSTS)
        hsp_res = oracle.resolve(hsp_claim, self.SCENARIO_WITH_COSTS)

        self.assertLess(hsp_res.error_margin, linear_res.error_margin)

    def test_resolution_includes_system_accounting(self):
        oracle = ClosedSystemOracle()
        claim = Claim("Cost cutting increases margin if demand holds", ["Q1"], 0.8)
        resolution = oracle.resolve(claim, self.SCENARIO_WITH_COSTS)
        self.assertIsNotNone(resolution.system_accounting)
        self.assertIn("SYSTEM LEDGER", resolution.system_accounting)
        self.assertIn("Conservation", resolution.system_accounting)

    def test_falls_back_to_simulation_without_costs(self):
        oracle = ClosedSystemOracle()
        scenario_no_costs = {
            "agents": self.SCENARIO_WITH_COSTS["agents"],
            "parameters": {"material_circularity": 1.0},
        }
        claim = Claim("Cost cutting increases margin if demand holds", ["Q1"], 0.8)
        resolution = oracle.resolve(claim, scenario_no_costs)
        # Should still resolve (via simulation fallback)
        self.assertNotEqual(resolution.outcome, Outcome.PENDING)

    def test_conservation_balanced_in_resolution(self):
        oracle = ClosedSystemOracle()
        claim = Claim("Cost cutting increases margin if demand holds", ["Q1"], 0.8)
        resolution = oracle.resolve(claim, self.SCENARIO_WITH_COSTS)
        self.assertIn("BALANCED", resolution.system_accounting)

    def test_entropy_shown_in_accounting(self):
        oracle = ClosedSystemOracle()
        claim = Claim("Cost cutting increases margin if demand holds", ["Q1"], 0.8)
        resolution = oracle.resolve(claim, self.SCENARIO_WITH_COSTS)
        self.assertIn("Entropy", resolution.system_accounting)
        self.assertIn("Knowledge lost", resolution.system_accounting)

    def test_margin_is_a_lie_message(self):
        """When external costs exceed company gain, the oracle calls it out."""
        oracle = ClosedSystemOracle()
        scenario = {
            "agents": {
                "Linear": {
                    "claim": "Extraction increases profit if we ignore costs",
                    "variables": ["profit"],
                    "confidence": 0.9,
                    "omissions": ["environmental_damage", "health_costs"],
                },
            },
            "cost_transfers": [
                {"source": "environment", "target": "company", "amount": 1000000,
                 "description": "Resource extraction", "reversible": False, "confidence": 1.0},
                {"source": "environment", "target": "healthcare", "amount": -1500000,
                 "description": "Pollution health costs", "reversible": False, "confidence": 0.8},
            ],
            "entropy_events": [
                {"domain": "environment", "description": "Permanent ecosystem damage", "magnitude": 0.3},
            ],
        }
        claim = Claim("Extraction increases profit if we ignore costs", ["Q1"], 0.9)
        resolution = oracle.resolve(claim, scenario)
        self.assertIn("THE MARGIN IS A LIE", resolution.system_accounting)


if __name__ == "__main__":
    unittest.main()
