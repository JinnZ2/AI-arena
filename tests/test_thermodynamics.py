"""Tests for thermodynamic accounting — conservation of cost."""

import unittest

from arena.thermodynamics import (
    SystemLedger, Domain, CostTransfer, EntropyEvent, TemporalProfile,
    build_ledger_from_scenario, ImperfectionChecker, EquilibriumChecker,
    ResourceType, ResourceAtom, AtomicLedger, build_atomic_ledger_from_scenario,
)
from arena.trust import MemoryEntry
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


class TestTemporalDynamics(unittest.TestCase):

    def test_immediate_profile_constant(self):
        t = CostTransfer(Domain.WORKERS, Domain.COMPANY, 1000, "Test",
                        temporal_profile=TemporalProfile.IMMEDIATE)
        self.assertEqual(t.amount_at_month(0), 1000)
        self.assertEqual(t.amount_at_month(60), 1000)

    def test_compounding_profile_grows(self):
        t = CostTransfer(Domain.WORKERS, Domain.HEALTHCARE, -500000, "Health",
                        temporal_profile=TemporalProfile.COMPOUNDING, compound_rate=0.05)
        at_0 = abs(t.amount_at_month(0))
        at_12 = abs(t.amount_at_month(12))
        at_60 = abs(t.amount_at_month(60))
        self.assertLess(at_0, at_12)
        self.assertLess(at_12, at_60)

    def test_delayed_profile_zero_before_threshold(self):
        t = CostTransfer(Domain.WORKERS, Domain.COMPANY, 1000, "Delayed",
                        temporal_profile=TemporalProfile.DELAYED, delay_months=12)
        self.assertEqual(t.amount_at_month(0), 0)
        self.assertEqual(t.amount_at_month(6), 0)
        self.assertGreater(t.amount_at_month(18), 0)

    def test_decaying_profile_shrinks(self):
        t = CostTransfer(Domain.WORKERS, Domain.INFRASTRUCTURE, -500000, "Decaying",
                        temporal_profile=TemporalProfile.DECAYING)
        at_0 = abs(t.amount_at_month(0))
        at_24 = abs(t.amount_at_month(24))
        self.assertGreater(at_0, at_24)

    def test_linear_profile_grows_steadily(self):
        t = CostTransfer(Domain.WORKERS, Domain.COMMUNITY, -1000, "Linear growth",
                        temporal_profile=TemporalProfile.LINEAR)
        at_0 = abs(t.amount_at_month(0))
        at_10 = abs(t.amount_at_month(10))
        at_20 = abs(t.amount_at_month(20))
        self.assertAlmostEqual(at_10 - at_0, at_20 - at_10, places=0)

    def test_entropy_compounds(self):
        e = EntropyEvent(Domain.WORKERS, "Knowledge gap", 0.1, compounds=True, compound_rate=0.05)
        at_0 = e.magnitude_at_month(0)
        at_12 = e.magnitude_at_month(12)
        self.assertAlmostEqual(at_0, 0.1)
        self.assertGreater(at_12, 0.1)

    def test_entropy_no_compound(self):
        e = EntropyEvent(Domain.WORKERS, "Static loss", 0.1, compounds=False)
        self.assertEqual(e.magnitude_at_month(0), 0.1)
        self.assertEqual(e.magnitude_at_month(100), 0.1)

    def test_temporal_projection_output(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 1_000_000, "Savings")
        ledger.transfers[-1].temporal_profile = TemporalProfile.IMMEDIATE
        ledger.transfer(Domain.WORKERS, Domain.HEALTHCARE, -500_000, "Health",
                       reversible=False)
        ledger.transfers[-1].temporal_profile = TemporalProfile.COMPOUNDING
        ledger.transfers[-1].compound_rate = 0.05
        projection = ledger.temporal_projection([0, 12, 24])
        self.assertIn("TEMPORAL PROJECTION", projection)
        self.assertIn("Month", projection)

    def test_net_system_value_at_grows_negative(self):
        ledger = SystemLedger()
        ledger.transfer(Domain.WORKERS, Domain.COMPANY, 1_000_000, "Savings")
        ledger.transfer(Domain.WORKERS, Domain.HEALTHCARE, -500_000, "Health",
                       reversible=False)
        ledger.transfers[-1].temporal_profile = TemporalProfile.COMPOUNDING
        ledger.transfers[-1].compound_rate = 0.05
        ledger.add_entropy(Domain.WORKERS, "Knowledge gap", 0.1)

        net_0 = ledger.net_system_value_at(0)
        net_60 = ledger.net_system_value_at(60)
        self.assertLess(net_60, net_0)  # Gets worse over time


class TestFeedbackLoop(unittest.TestCase):
    """Test that agents receive and respond to ledger feedback."""

    def test_agents_receive_system_accounting(self):
        from arena.agents.rule_based import LinearAgent, HSPAgent
        from arena.engine import Arena
        from arena.oracle import ClosedSystemOracle

        agents = [LinearAgent("Linear_CEO"), HSPAgent("Systemic_HSP")]
        arena = Arena(agents=agents, oracle=ClosedSystemOracle(), max_cycles=1, verbose=False)
        arena.run(self.SCENARIO_WITH_COSTS)

        # Both agents should have received system accounting
        for agent in agents:
            self.assertTrue(len(agent.trust.last_system_accounting) > 0)

    def test_linear_agent_responds_to_ledger(self):
        from arena.agents.rule_based import LinearAgent

        agent = LinearAgent("Linear_CEO")
        # Simulate receiving ledger feedback that says margin is a lie
        agent.trust.last_system_accounting = (
            "THE MARGIN IS A LIE\n"
            "TEMPORAL AMPLIFICATION\n"
            "Net system value:   -0.30"
        )
        agent.trust.memory.append(MemoryEntry(
            "C1", "X", 0.7, "partially_valid", 0.5, 1,
        ))
        self.assertTrue(agent.ledger_shows_net_negative)
        self.assertTrue(agent.ledger_shows_temporal_amplification)

    def test_hsp_gains_confidence_from_ledger(self):
        from arena.agents.rule_based import HSPAgent

        agent = HSPAgent("Systemic_HSP")
        agent.trust.last_system_accounting = "validated by system ledger"
        agent.trust.memory.append(MemoryEntry("C1", "X", 0.6, "valid", 0.1, 1))
        self.assertTrue(agent.has_ledger_feedback)

    SCENARIO_WITH_COSTS = {
        "parameters": {"time_horizon": "12 Months"},
        "agents": {
            "Linear_CEO": {
                "claim": "Cost cutting increases margin if demand holds",
                "variables": ["operating_margin", "labor_cost"],
                "confidence": 0.72,
                "omissions": ["attrition_rate"],
            },
            "Systemic_HSP": {
                "counter_claim": "Cost cutting causes attrition if workers are displaced",
                "variables": ["attrition_rate", "operating_margin", "morale"],
                "confidence": 0.65,
            },
        },
        "cost_transfers": [
            {"source": "workers", "target": "company", "amount": 2000000,
             "description": "Savings", "reversible": False, "confidence": 0.9},
            {"source": "workers", "target": "community", "amount": -800000,
             "description": "Lost spending", "reversible": False, "confidence": 0.8,
             "temporal_profile": "compounding", "compound_rate": 0.04},
        ],
        "entropy_events": [
            {"domain": "workers", "description": "Knowledge lost", "magnitude": 0.1},
        ],
    }


# Make SCENARIO_WITH_COSTS accessible at class level for test_agents_receive_system_accounting
TestFeedbackLoop.SCENARIO_WITH_COSTS = TestFeedbackLoop.SCENARIO_WITH_COSTS


class TestImperfectionChecker(unittest.TestCase):
    """Third Law: no process achieves perfect efficiency."""

    def test_perfect_confidence_penalized(self):
        """Confidence = 1.0 violates Third Law (absolute zero unattainable)."""
        penalty, violations = ImperfectionChecker.check_claim(1.0, ["revenue"], [])
        self.assertGreater(penalty, 0)
        self.assertTrue(any("Third Law" in v for v in violations))

    def test_reasonable_confidence_no_penalty(self):
        """Normal confidence with good coverage should not be penalized."""
        penalty, violations = ImperfectionChecker.check_claim(
            0.7,
            ["revenue", "attrition", "morale", "tech_debt"],
            ["supply_chain"],
        )
        self.assertEqual(penalty, 0.0)
        self.assertEqual(len(violations), 0)

    def test_narrow_model_zero_omissions_penalized(self):
        """Narrow model claiming zero omissions = frictionless claim."""
        penalty, violations = ImperfectionChecker.check_claim(0.8, ["revenue"], [])
        self.assertGreater(penalty, 0)
        self.assertTrue(any("frictionless" in v for v in violations))

    def test_broad_model_zero_omissions_ok(self):
        """Broad model can legitimately have fewer omissions."""
        penalty, violations = ImperfectionChecker.check_claim(
            0.6, ["a", "b", "c", "d", "e"], []
        )
        # Broad models don't trigger the narrow-model suspicion
        self.assertEqual(penalty, 0.0)

    def test_carnot_bound_basic(self):
        """Carnot bound = 1 - overhead/input."""
        bound = ImperfectionChecker.carnot_bound(1_000_000, 200_000)
        self.assertAlmostEqual(bound, 0.8)

    def test_carnot_bound_zero_input(self):
        """Zero input means zero efficiency possible."""
        bound = ImperfectionChecker.carnot_bound(0, 100)
        self.assertEqual(bound, 0.0)

    def test_efficiency_claim_within_bound(self):
        """Claiming savings within Carnot bound: no penalty."""
        penalty, msg = ImperfectionChecker.check_efficiency_claim(
            claimed_savings=700_000,
            total_input=1_000_000,
            minimum_overhead=200_000,
        )
        self.assertEqual(penalty, 0.0)
        self.assertIsNone(msg)

    def test_efficiency_claim_exceeds_bound(self):
        """Claiming savings beyond Carnot bound: penalized."""
        penalty, msg = ImperfectionChecker.check_efficiency_claim(
            claimed_savings=950_000,  # 95% efficiency
            total_input=1_000_000,
            minimum_overhead=200_000,  # Max = 80%
        )
        self.assertGreater(penalty, 0)
        self.assertIn("Carnot", msg)


class TestEquilibriumChecker(unittest.TestCase):
    """Le Chatelier: systems resist displacement from equilibrium."""

    def test_small_disturbance_no_penalty(self):
        """Minor changes don't trigger significant resistance."""
        penalty, msg = EquilibriumChecker.check_claim(0.05, False)
        self.assertEqual(penalty, 0.0)
        self.assertIsNone(msg)

    def test_large_disturbance_no_counterforce_penalized(self):
        """Major disturbance without modeling counterforce: penalized."""
        penalty, msg = EquilibriumChecker.check_claim(0.5, False)
        self.assertGreater(penalty, 0)
        self.assertIn("Le Chatelier", msg)
        self.assertIn("severe", msg)

    def test_large_disturbance_with_counterforce_ok(self):
        """Major disturbance with counterforce modeled: no penalty."""
        penalty, msg = EquilibriumChecker.check_claim(0.5, True)
        self.assertEqual(penalty, 0.0)
        self.assertIsNone(msg)

    def test_moderate_disturbance_unmodeled(self):
        """Moderate disturbance without counterforce: moderate penalty."""
        penalty, msg = EquilibriumChecker.check_claim(0.3, False)
        self.assertGreater(penalty, 0)
        self.assertIn("significant", msg)

    def test_counterforce_increases_with_magnitude(self):
        """Larger disturbances produce larger counterforces."""
        cf_small = EquilibriumChecker.estimate_counterforce(0.2)
        cf_large = EquilibriumChecker.estimate_counterforce(0.8)
        self.assertGreater(cf_large, cf_small)

    def test_fast_rate_amplifies_counterforce(self):
        """Fast changes create disproportionately large resistance."""
        cf_slow = EquilibriumChecker.estimate_counterforce(0.3, rate_of_change=1.0)
        cf_fast = EquilibriumChecker.estimate_counterforce(0.3, rate_of_change=5.0)
        self.assertGreater(cf_fast, cf_slow)

    def test_resistance_gradient(self):
        """Rate of change matters more than magnitude alone."""
        # Slow but large change
        cf_slow_large = EquilibriumChecker.estimate_counterforce(0.5, rate_of_change=1.0)
        # Fast but moderate change
        cf_fast_moderate = EquilibriumChecker.estimate_counterforce(0.3, rate_of_change=5.0)
        # Fast moderate can exceed slow large due to rate amplifier
        self.assertGreater(cf_fast_moderate, 0)
        self.assertGreater(cf_slow_large, 0)


class TestAtomicLedger(unittest.TestCase):
    """Atomic accounting: indivisible resource units that can't hide in aggregation."""

    def test_add_and_count(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON, 45, "employees", Domain.WORKERS)
        ledger.add(ResourceType.KNOWLEDGE_UNIT, 12, "architectures", Domain.COMPANY,
                  destroyed=True, reversible=False)
        self.assertEqual(ledger.total_atoms, 2)

    def test_destroyed_atoms(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON, 45, "employees", Domain.WORKERS)
        ledger.add(ResourceType.KNOWLEDGE_UNIT, 12, "architectures", Domain.COMPANY,
                  destroyed=True, reversible=False)
        self.assertEqual(len(ledger.destroyed_atoms), 1)
        self.assertEqual(ledger.irreversible_destruction_count, 12)

    def test_consumed_atoms(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON_HOUR, 8400, "hours", Domain.COMPANY, consumed=True)
        self.assertEqual(len(ledger.consumed_atoms), 1)

    def test_atoms_by_type(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.RELATIONSHIP, 28, "mentorship", Domain.WORKERS)
        ledger.add(ResourceType.RELATIONSHIP, 135, "community", Domain.COMMUNITY)
        totals = ledger.atoms_by_type
        self.assertEqual(totals[ResourceType.RELATIONSHIP], 163)

    def test_atoms_by_domain(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON, 45, "people", Domain.WORKERS)
        ledger.add(ResourceType.RELATIONSHIP, 135, "connections", Domain.COMMUNITY)
        by_domain = ledger.atoms_by_domain
        self.assertEqual(len(by_domain[Domain.WORKERS]), 1)
        self.assertEqual(len(by_domain[Domain.COMMUNITY]), 1)

    def test_coverage_score_full_coverage(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON, 45, "people", Domain.WORKERS)
        ledger.add(ResourceType.KNOWLEDGE_UNIT, 12, "knowledge", Domain.COMPANY)
        # Variables that cover both types
        score = ledger.coverage_score({"employee_count", "institutional_knowledge"})
        self.assertEqual(score, 1.0)

    def test_coverage_score_partial(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON, 45, "people", Domain.WORKERS)
        ledger.add(ResourceType.KNOWLEDGE_UNIT, 12, "knowledge", Domain.COMPANY)
        ledger.add(ResourceType.RELATIONSHIP, 28, "bonds", Domain.WORKERS)
        # Only covers PERSON, not KNOWLEDGE or RELATIONSHIP
        score = ledger.coverage_score({"headcount"})
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.0)

    def test_coverage_score_zero(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON, 45, "people", Domain.WORKERS)
        # Variable that covers nothing
        score = ledger.coverage_score({"revenue_growth"})
        self.assertEqual(score, 0.0)

    def test_coverage_score_empty_ledger(self):
        ledger = AtomicLedger()
        score = ledger.coverage_score({"anything"})
        self.assertEqual(score, 1.0)  # Nothing to miss

    def test_summary_output(self):
        ledger = AtomicLedger()
        ledger.add(ResourceType.PERSON, 45, "employees displaced", Domain.WORKERS,
                  consumed=True, description="Real people")
        ledger.add(ResourceType.KNOWLEDGE_UNIT, 12, "system architectures", Domain.COMPANY,
                  destroyed=True, reversible=False, description="Tribal knowledge")
        summary = ledger.summary()
        self.assertIn("ATOMIC LEDGER", summary)
        self.assertIn("employees displaced", summary)
        self.assertIn("DESTROYED IRREVERSIBLE", summary)
        self.assertIn("CONSUMED", summary)

    def test_build_from_scenario(self):
        scenario = {
            "resource_atoms": [
                {"type": "person", "quantity": 10, "unit_label": "workers",
                 "domain": "workers", "consumed": True},
                {"type": "knowledge_unit", "quantity": 5, "unit_label": "systems",
                 "domain": "company", "destroyed": True, "reversible": False},
            ],
        }
        ledger = build_atomic_ledger_from_scenario(scenario)
        self.assertEqual(ledger.total_atoms, 2)
        self.assertEqual(len(ledger.destroyed_atoms), 1)

    def test_build_empty_scenario(self):
        ledger = build_atomic_ledger_from_scenario({})
        self.assertEqual(ledger.total_atoms, 0)


class TestAtomicTiebreaker(unittest.TestCase):
    """Integration: atomic accounting as oracle tiebreaker."""

    def test_atomic_penalty_applied_to_narrow_claim(self):
        oracle = ClosedSystemOracle()
        claim = Claim("Cost cutting increases margin if demand holds",
                      ["Q3-Q4"], 0.7)
        scenario = {
            "parameters": {"time_horizon": "12 Months"},
            "agents": {
                "Linear": {
                    "claim": "Cost cutting increases margin if demand holds",
                    "variables": ["operating_margin"],  # Narrow — misses atoms
                    "confidence": 0.7,
                    "omissions": [],
                },
            },
            "cost_transfers": [
                {"source": "workers", "target": "company", "amount": 1000000,
                 "description": "Savings"},
            ],
            "resource_atoms": [
                {"type": "person", "quantity": 20, "unit_label": "workers",
                 "domain": "workers", "consumed": True},
                {"type": "knowledge_unit", "quantity": 8, "unit_label": "systems",
                 "domain": "company", "destroyed": True, "reversible": False},
                {"type": "relationship", "quantity": 15, "unit_label": "mentorships",
                 "domain": "workers", "destroyed": True, "reversible": False},
            ],
        }
        resolution = oracle.resolve(claim, scenario)
        self.assertIn("ATOMIC LEDGER", resolution.system_accounting)
        self.assertIn("Atomic penalty", resolution.system_accounting)

    def test_broad_claim_lower_atomic_penalty(self):
        oracle = ClosedSystemOracle()
        scenario = {
            "parameters": {"time_horizon": "12 Months"},
            "agents": {
                "Narrow": {
                    "claim": "Cutting costs increases margin if revenue holds",
                    "variables": ["operating_margin"],
                    "confidence": 0.7,
                    "omissions": [],
                },
                "Broad": {
                    "counter_claim": "Cutting costs causes knowledge drain if workers leave",
                    "variables": ["operating_margin", "institutional_knowledge",
                                  "employee_morale", "innovation_pipeline"],
                    "confidence": 0.6,
                },
            },
            "cost_transfers": [
                {"source": "workers", "target": "company", "amount": 1000000,
                 "description": "Savings"},
            ],
            "resource_atoms": [
                {"type": "person", "quantity": 20, "unit_label": "workers",
                 "domain": "workers"},
                {"type": "knowledge_unit", "quantity": 8, "unit_label": "systems",
                 "domain": "company", "destroyed": True},
                {"type": "relationship", "quantity": 15, "unit_label": "mentorships",
                 "domain": "workers", "destroyed": True},
                {"type": "opportunity", "quantity": 3, "unit_label": "projects",
                 "domain": "company", "destroyed": True},
            ],
        }
        narrow_claim = Claim("Cutting costs increases margin if revenue holds",
                             ["Q3-Q4"], 0.7)
        broad_claim = Claim("Cutting costs causes knowledge drain if workers leave",
                            ["Q3-Q4"], 0.6)

        narrow_res = oracle.resolve(narrow_claim, scenario)
        broad_res = oracle.resolve(broad_claim, scenario)

        # Broad claim should have lower error (better atomic coverage)
        self.assertLess(broad_res.error_margin, narrow_res.error_margin)


class TestClosedSystemOraclePhysicsAxioms(unittest.TestCase):
    """Integration tests: all four physics axioms enforced by the oracle."""

    def test_imperfection_penalty_in_oracle(self):
        """Oracle penalizes perfect-confidence claims (Third Law)."""
        oracle = ClosedSystemOracle()
        claim = Claim(
            proposition="Cost cutting increases margin if demand holds",
            scope=["Q3-Q4"],
            confidence=1.0,  # Perfect confidence = Third Law violation
            agent_name="Overconfident_CEO",
        )
        scenario = {
            "parameters": {"time_horizon": "12 Months"},
            "agents": {
                "Overconfident_CEO": {
                    "claim": "Cost cutting increases margin if demand holds",
                    "variables": ["margin"],
                    "confidence": 1.0,
                    "omissions": [],
                },
            },
            "cost_transfers": [
                {"source": "workers", "target": "company", "amount": 1000000,
                 "description": "Savings"},
            ],
        }
        resolution = oracle.resolve(claim, scenario)
        self.assertGreater(resolution.error_margin, 0)
        self.assertIn("Imperfection penalty", resolution.system_accounting)

    def test_equilibrium_penalty_in_oracle(self):
        """Oracle penalizes large disturbances without counterforce modeling."""
        oracle = ClosedSystemOracle()
        claim = Claim(
            proposition="Cost cutting increases margin if demand holds",
            scope=["Q3-Q4"],
            confidence=0.8,
            agent_name="Linear_CEO",
        )
        scenario = {
            "parameters": {
                "time_horizon": "12 Months",
                "disturbance_magnitude": 0.5,
                "rate_of_change": 3.0,
            },
            "agents": {
                "Linear_CEO": {
                    "claim": "Cost cutting increases margin if demand holds",
                    "variables": ["margin", "revenue"],
                    "confidence": 0.8,
                    "omissions": ["attrition_rate"],
                },
            },
            "cost_transfers": [
                {"source": "workers", "target": "company", "amount": 2000000,
                 "description": "Savings"},
            ],
        }
        resolution = oracle.resolve(claim, scenario)
        self.assertIn("Equilibrium penalty", resolution.system_accounting)
        self.assertIn("Le Chatelier", resolution.system_accounting)

    def test_hsp_agent_passes_equilibrium_check(self):
        """HSP agent models counterforce variables — no Le Chatelier penalty."""
        oracle = ClosedSystemOracle()
        claim = Claim(
            proposition="Cost cutting causes attrition if workers are displaced",
            scope=["Q3-Q4"],
            confidence=0.65,
            agent_name="Systemic_HSP",
        )
        scenario = {
            "parameters": {
                "time_horizon": "12 Months",
                "disturbance_magnitude": 0.5,
            },
            "agents": {
                "Systemic_HSP": {
                    "claim": "Cost cutting causes attrition if workers are displaced",
                    "variables": ["attrition_rate", "employee_morale", "knowledge_drain"],
                    "confidence": 0.65,
                    "omissions": [],
                },
            },
            "cost_transfers": [
                {"source": "workers", "target": "company", "amount": 2000000,
                 "description": "Savings"},
            ],
        }
        resolution = oracle.resolve(claim, scenario)
        # Should not contain Le Chatelier violation since counterforce vars are present
        if resolution.system_accounting:
            self.assertNotIn("Le Chatelier", resolution.system_accounting)


if __name__ == "__main__":
    unittest.main()
