"""Tests for experimental/differential_interferometry.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from differential_interferometry import (
    FilterProfile,
    LOW_DIVERGENCE_THRESHOLD,
    _jaccard,
    _tokenize,
    analyze_divergence,
    divergence_summary,
    query_ensemble,
)


class TestTokenize(unittest.TestCase):

    def test_lowercases_and_drops_short_tokens(self):
        toks = _tokenize("The Quick Brown Fox is here")
        self.assertIn("quick", toks)
        self.assertIn("brown", toks)
        self.assertNotIn("the", toks)  # stopword
        self.assertNotIn("is", toks)   # stopword

    def test_strips_punctuation(self):
        toks = _tokenize("river, sediment; downstream.")
        self.assertEqual(toks, {"river", "sediment", "downstream"})


class TestJaccard(unittest.TestCase):

    def test_identical_sets_one(self):
        self.assertEqual(_jaccard({"a", "b"}, {"a", "b"}), 1.0)

    def test_disjoint_sets_zero(self):
        self.assertEqual(_jaccard({"a"}, {"b"}), 0.0)

    def test_both_empty_zero(self):
        self.assertEqual(_jaccard(set(), set()), 0.0)


class TestQueryEnsemble(unittest.TestCase):

    def test_requires_at_least_two_backends(self):
        with self.assertRaises(ValueError):
            query_ensemble("q", [(lambda q: "x", FilterProfile(name="A"))])

    def test_collects_responses_from_each_backend(self):
        backends = [
            (lambda q: "river carries sediment", FilterProfile(name="A")),
            (lambda q: "river carries sediment", FilterProfile(name="B")),
        ]
        d = query_ensemble("q", backends)
        self.assertEqual(len(d.responses), 2)
        self.assertEqual({r.backend for r in d.responses}, {"A", "B"})

    def test_backend_error_captured_not_raised(self):
        def bad(q):
            raise RuntimeError("nope")
        backends = [
            (lambda q: "fine", FilterProfile(name="A")),
            (bad, FilterProfile(name="B")),
        ]
        d = query_ensemble("q", backends)
        errored = [r for r in d.responses if r.error]
        self.assertEqual(len(errored), 1)
        self.assertIn("RuntimeError", errored[0].error)

    def test_overlap_matrix_pairs_only(self):
        backends = [
            (lambda q: "alpha beta", FilterProfile(name="A")),
            (lambda q: "alpha beta", FilterProfile(name="B")),
            (lambda q: "alpha gamma", FilterProfile(name="C")),
        ]
        d = query_ensemble("q", backends)
        self.assertEqual(set(d.overlap_matrix.keys()),
                         {("A", "B"), ("A", "C"), ("B", "C")})
        self.assertEqual(d.overlap_matrix[("A", "B")], 1.0)
        self.assertLess(d.overlap_matrix[("A", "C")], 1.0)

    def test_unique_tokens_per_backend(self):
        backends = [
            (lambda q: "shared distinct_a", FilterProfile(name="A")),
            (lambda q: "shared distinct_b", FilterProfile(name="B")),
        ]
        d = query_ensemble("q", backends)
        self.assertIn("distinct_a", d.unique_tokens["A"])
        self.assertNotIn("shared", d.unique_tokens["A"])

    def test_shared_tokens_appear_in_at_least_two(self):
        backends = [
            (lambda q: "alpha unique_a", FilterProfile(name="A")),
            (lambda q: "alpha unique_b", FilterProfile(name="B")),
            (lambda q: "beta", FilterProfile(name="C")),
        ]
        d = query_ensemble("q", backends)
        self.assertIn("alpha", d.shared_tokens)
        self.assertNotIn("beta", d.shared_tokens)


class TestAnalyzeDivergence(unittest.TestCase):

    def test_insufficient_and_backend_error_when_one_fails(self):
        def bad(q):
            raise RuntimeError("x")
        d = analyze_divergence(query_ensemble("q", [
            (lambda q: "ok", FilterProfile(name="A", training_cutoff="2024")),
            (bad, FilterProfile(name="B", training_cutoff="2025")),
        ]))
        self.assertIn("INSUFFICIENT_RESPONSES", d.flags)
        self.assertIn("BACKEND_ERROR", d.flags)

    def test_undeclared_filter_flagged(self):
        d = analyze_divergence(query_ensemble("q", [
            (lambda q: "alpha", FilterProfile(name="A", training_cutoff="2024")),
            (lambda q: "beta", FilterProfile(name="B")),  # all defaults
        ]))
        self.assertIn("UNDECLARED_FILTER", d.flags)

    def test_filter_profile_too_similar_flag(self):
        d = analyze_divergence(query_ensemble("q", [
            (lambda q: "alpha", FilterProfile(name="A", training_cutoff="2024",
                                              retrieval="rag")),
            (lambda q: "beta", FilterProfile(name="B", training_cutoff="2024",
                                             retrieval="rag")),
        ]))
        self.assertIn("FILTER_PROFILE_TOO_SIMILAR", d.flags)

    def test_low_divergence_when_responses_match(self):
        # Identical responses -> overlap 1.0 -> above threshold.
        d = analyze_divergence(query_ensemble("q", [
            (lambda q: "river carries sediment downstream",
             FilterProfile(name="A", training_cutoff="2024")),
            (lambda q: "river carries sediment downstream",
             FilterProfile(name="B", training_cutoff="2025")),
        ]))
        self.assertIn("LOW_DIVERGENCE", d.flags)

    def test_no_flags_when_well_formed_and_diverse(self):
        d = analyze_divergence(query_ensemble("q", [
            (lambda q: "alpha gamma delta",
             FilterProfile(name="A", training_cutoff="2010", retrieval="none")),
            (lambda q: "epsilon zeta eta",
             FilterProfile(name="B", training_cutoff="2025", retrieval="rag",
                           recency_curve="exponential")),
        ]))
        self.assertEqual(d.flags, [])

    def test_low_divergence_threshold_is_strict(self):
        # Just below the threshold should not flag.
        # Construct two responses with overlap exactly LOW_DIVERGENCE_THRESHOLD
        # by counting shared tokens.
        # 2 shared / 3 union = 0.67 < 0.7, no flag.
        d = analyze_divergence(query_ensemble("q", [
            (lambda q: "alpha beta gamma",
             FilterProfile(name="A", training_cutoff="2024")),
            (lambda q: "alpha beta delta",
             FilterProfile(name="B", training_cutoff="2025")),
        ]))
        # overlap = 2/4 = 0.5
        self.assertNotIn("LOW_DIVERGENCE", d.flags)


class TestDivergenceSummary(unittest.TestCase):

    def test_summary_returns_string_with_query(self):
        d = analyze_divergence(query_ensemble("my query", [
            (lambda q: "alpha", FilterProfile(name="A", training_cutoff="2024")),
            (lambda q: "beta", FilterProfile(name="B", training_cutoff="2025")),
        ]))
        s = divergence_summary(d)
        self.assertIn("my query", s)
        self.assertIn("backends", s)


if __name__ == "__main__":
    unittest.main()
