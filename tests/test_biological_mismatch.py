"""Tests for src/biological_mismatch.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from biological_mismatch import (
    REGIMES,
    BiologicalRegime,
    MismatchReport,
    RegimeCategory,
    _keyword_match,
    check_behavior,
    regime_audit_prompt,
)


class TestRegimeLibrary(unittest.TestCase):

    def test_all_regimes_have_required_fields(self):
        for rid, r in REGIMES.items():
            self.assertEqual(r.id, rid)
            self.assertTrue(r.traits, rid)
            self.assertTrue(r.adaptive_in_environments, rid)
            self.assertTrue(r.mismatch_environments, rid)
            self.assertTrue(r.common_misdiagnoses, rid)

    def test_regime_to_dict_serializes_category_as_string(self):
        r = REGIMES["dyslexic_spatial"]
        d = r.to_dict()
        self.assertEqual(d["category"], "neurocognitive")
        self.assertIsInstance(d["category"], str)


class TestKeywordMatch(unittest.TestCase):

    def test_empty_phrase_returns_false(self):
        self.assertFalse(_keyword_match("", "anything goes here"))
        self.assertFalse(_keyword_match("a an the", "lots of words present"))

    def test_full_overlap_returns_true(self):
        self.assertTrue(_keyword_match(
            "spatial reasoning",
            "high spatial reasoning capability"))

    def test_no_overlap_returns_false(self):
        self.assertFalse(_keyword_match(
            "elephant migrations",
            "credential gated bureaucratic forms"))

    def test_partial_overlap_below_threshold(self):
        # "spatial reasoning kinetic embodied" → 4 meaningful words.
        # Threshold is ceil(4/2) = 2. One match should not be enough.
        self.assertFalse(_keyword_match(
            "spatial reasoning kinetic embodied",
            "spatial calculations only"))

    def test_punctuation_stripped(self):
        self.assertTrue(_keyword_match(
            "high-throughput, motion-regulating systems.",
            "throughput motion systems running"))


class TestCheckBehaviorNoMatch(unittest.TestCase):

    def test_unrelated_behavior_returns_empty_match(self):
        report = check_behavior(
            "purple elephants float gracefully through clouds",
            "imaginary environment")
        self.assertEqual(report.matching_regimes, [])
        self.assertFalse(report.is_adaptive_somewhere)
        self.assertFalse(report.is_adaptive_in_current_environment)
        self.assertIn("DO NOT pathologize", report.recommendation)


class TestCheckBehaviorAdaptiveHere(unittest.TestCase):

    def test_truck_driver_high_energy_in_mobile_work(self):
        report = check_behavior(
            "high baseline energy continuous engagement preference "
            "stress regulation through motion",
            "long-haul physical work multi-domain problem solving")
        self.assertIn("high_throughput_nervous_system", report.matching_regimes)
        self.assertTrue(report.is_adaptive_in_current_environment)
        self.assertEqual(report.likely_misdiagnoses, [])
        self.assertIn("RECOGNIZE", report.recommendation)


class TestCheckBehaviorMismatch(unittest.TestCase):

    def test_dyslexic_in_bureaucratic_environment(self):
        report = check_behavior(
            "frustration with paperwork slow text processing low test scores "
            "despite high capability",
            "text-heavy bureaucratic office work credential-gated career")
        self.assertIn("dyslexic_spatial", report.matching_regimes)
        self.assertTrue(report.is_adaptive_somewhere)
        self.assertFalse(report.is_adaptive_in_current_environment)
        self.assertTrue(report.likely_misdiagnoses)
        self.assertIn("environment is the constraint", report.actual_constraint)

    def test_distributed_decision_in_corporate_hierarchy(self):
        report = check_behavior(
            "questioning authority directives coalition-building with peers "
            "slow compliance with unilateral orders",
            "corporate top-down hierarchy mandatory schooling")
        self.assertIn("distributed_decision_baseline", report.matching_regimes)
        self.assertFalse(report.is_adaptive_in_current_environment)

    def test_care_masculine_in_status_culture(self):
        report = check_behavior(
            "preferring time with children to status competition "
            "low motivation for status-display work",
            "corporate masculinity frames status-via-economic-dominance culture")
        self.assertIn("care_capacity_masculine", report.matching_regimes)
        self.assertFalse(report.is_adaptive_in_current_environment)

    def test_cyclical_hormonal_in_constant_productivity(self):
        report = check_behavior(
            "cyclic energy fluctuation across weeks, monthly cognitive shifts, "
            "premenstrual sensitivity called moodiness",
            "constant linear productivity demands, quarterly performance metrics "
            "insensitive to cycles")
        self.assertIn("cyclical_hormonal_regulation", report.matching_regimes)
        self.assertFalse(report.is_adaptive_in_current_environment)

    def test_extended_maturation_in_age_graded_school(self):
        report = check_behavior(
            "behind same-age peers academically, called late bloomer, "
            "social awkwardness in cohort",
            "standardized-age testing systems, K-12 grade-by-birth-year structures")
        self.assertIn("extended_maturation", report.matching_regimes)
        self.assertFalse(report.is_adaptive_in_current_environment)

    def test_systematizing_in_open_plan_office(self):
        report = check_behavior(
            "deep pattern systematizing, intense special interests, "
            "literal language processing, sensory overload",
            "open-plan offices high-stimulation workplaces, "
            "small talk ambiguous interpersonal politics")
        self.assertIn("systematizing_neurodivergent", report.matching_regimes)
        self.assertFalse(report.is_adaptive_in_current_environment)


class TestRegimeCategoryCoverage(unittest.TestCase):

    def test_all_categories_have_at_least_one_regime(self):
        from biological_mismatch import RegimeCategory
        covered = {r.category for r in REGIMES.values()}
        for cat in RegimeCategory:
            self.assertIn(cat, covered, f"category {cat.value} has no regime")


class TestRegimeAuditPrompt(unittest.TestCase):

    def test_critical_when_proposed_diagnosis_matches_misdiagnosis(self):
        result = regime_audit_prompt(
            "adult",
            "frustration with paperwork slow text processing low test scores",
            "text-heavy bureaucratic office work credential-gated career",
            proposed_diagnosis="low intelligence, learning disabled",
        )
        self.assertTrue(result["verdict"].startswith("CRITICAL"))

    def test_regime_mismatch_when_no_diagnosis_proposed(self):
        result = regime_audit_prompt(
            "adult",
            "frustration with paperwork slow text processing low test scores",
            "text-heavy bureaucratic office work credential-gated career",
            proposed_diagnosis="",
        )
        self.assertTrue(result["verdict"].startswith("REGIME MISMATCH"))

    def test_recognize_when_environment_is_adaptive(self):
        result = regime_audit_prompt(
            "athlete",
            "high baseline energy continuous engagement stress regulation "
            "through motion",
            "long-haul physical work multi-domain problem solving",
        )
        self.assertIn("Behavior is adaptive in current environment",
                      result["verdict"])

    def test_insufficient_data_when_no_regime_matches(self):
        result = regime_audit_prompt(
            "subject",
            "elephant migration song dancing patterns",
            "imaginary cloud field",
        )
        self.assertTrue(result["verdict"].startswith("Insufficient regime data"))

    def test_audit_includes_questions_and_subject(self):
        result = regime_audit_prompt(
            "adult", "behavior", "environment", "diagnosis")
        self.assertEqual(result["subject"], "adult")
        self.assertEqual(result["proposed_diagnosis"], "diagnosis")
        self.assertGreaterEqual(len(result["audit_questions"]), 4)


class TestMismatchReport(unittest.TestCase):

    def test_to_dict_round_trip(self):
        report = check_behavior("anything", "anywhere")
        d = report.to_dict()
        self.assertIn("matching_regimes", d)
        self.assertIn("recommendation", d)
        self.assertIn("actual_constraint", d)


if __name__ == "__main__":
    unittest.main()
