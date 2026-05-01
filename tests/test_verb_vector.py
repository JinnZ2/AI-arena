"""Tests for experimental/verb_vector.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from verb_vector import (
    Axis,
    Component,
    DEFAULT_AXES,
    VerbSpace,
    VerbVector,
    cosine,
    default_space,
    distance_matrix,
)


class TestComponent(unittest.TestCase):

    def test_repr_truncates_long_evidence(self):
        c = Component(axis="x", value=1.0,
                      evidence=["a", "b", "c", "d", "e"])
        self.assertIn("(+2 more)", repr(c))


class TestVerbVector(unittest.TestCase):

    def test_value_returns_zero_for_missing_axis(self):
        v = VerbVector(components={}, basis=["x"])
        self.assertEqual(v.value("x"), 0.0)

    def test_as_array_follows_basis_order(self):
        c1 = Component(axis="a", value=1.0)
        c2 = Component(axis="b", value=2.0)
        v = VerbVector(components={"a": c1, "b": c2}, basis=["b", "a"])
        self.assertEqual(v.as_array(), [2.0, 1.0])

    def test_norm(self):
        c1 = Component(axis="a", value=3.0)
        c2 = Component(axis="b", value=4.0)
        v = VerbVector(components={"a": c1, "b": c2}, basis=["a", "b"])
        self.assertEqual(v.norm(), 5.0)

    def test_explain_runs_without_error_on_empty(self):
        v = VerbVector(components={}, basis=[])
        v.explain()  # should not raise


class TestVerbSpaceBasics(unittest.TestCase):

    def setUp(self):
        self.space = VerbSpace([
            Axis("flow", "x", [r"\bflow"]),
            Axis("bind", "x", [r"\bbind"]),
        ])

    def test_basis_order(self):
        self.assertEqual(self.space.basis, ["flow", "bind"])

    def test_add_axis_recompiles(self):
        self.space.add_axis(Axis("switch", "x", [r"\bswitch"]))
        v = self.space.encode("the system switches modes")
        self.assertGreater(v.value("switch"), 0)

    def test_encode_records_evidence_with_context(self):
        v = self.space.encode("the river flows downstream")
        comp = v.components["flow"]
        self.assertGreater(comp.value, 0)
        self.assertTrue(comp.evidence)
        self.assertIn("flow", comp.evidence[0].lower())


class TestNegationGuard(unittest.TestCase):

    def setUp(self):
        self.space = VerbSpace([Axis("flow", "x", [r"\bflows?\b"])])

    def test_negated_match_suppressed(self):
        v = self.space.encode("the river does not flow in winter")
        self.assertEqual(v.value("flow"), 0.0)

    def test_unnegated_match_counted(self):
        v = self.space.encode("the river flows in spring")
        self.assertGreater(v.value("flow"), 0.0)

    def test_negation_guard_off(self):
        space = VerbSpace([
            Axis("flow", "x", [r"\bflows?\b"], negation_guard=False),
        ])
        v = space.encode("the river does not flow in winter")
        self.assertGreater(v.value("flow"), 0.0)


class TestDegeneracyFlags(unittest.TestCase):

    def setUp(self):
        self.space = default_space()

    def test_copula_collapse_on_bare_is_sentence(self):
        v = self.space.encode("social media is bad")
        self.assertIn("COPULA_COLLAPSE", v.flags)

    def test_noun_first_degenerate_on_heavy_nominalization(self):
        v = self.space.encode(
            "the implementation of the regulation is a "
            "manifestation of the situation")
        self.assertIn("NOUN_FIRST_DEGENERATE", v.flags)

    def test_no_flags_on_well_formed_relational_claim(self):
        v = self.space.encode(
            "extracellular K+ binds the receptor and triggers a "
            "mode switch above the threshold")
        self.assertNotIn("COPULA_COLLAPSE", v.flags)
        self.assertNotIn("NOUN_FIRST_DEGENERATE", v.flags)


class TestEncodePaper(unittest.TestCase):

    def setUp(self):
        self.space = default_space()

    def test_encode_paper_uses_title_as_label(self):
        paper = {"title": "My Paper", "abstract": "river carries sediment"}
        v = self.space.encode_paper(paper)
        self.assertEqual(v.source, "My Paper")

    def test_encode_paper_combines_claims_and_abstract(self):
        paper = {
            "title": "X",
            "abstract": "river carries sediment",
            "claims": ["the receptor toggles between two states"],
        }
        v = self.space.encode_paper(paper)
        self.assertGreater(v.value("flows_into"), 0)
        self.assertGreater(v.value("mode_switches"), 0)


class TestCosine(unittest.TestCase):

    def setUp(self):
        self.space = VerbSpace([
            Axis("a", "x", [r"alpha"]),
            Axis("b", "x", [r"beta"]),
        ])

    def test_identical_vectors(self):
        v = self.space.encode("alpha alpha beta")
        self.assertAlmostEqual(cosine(v, v), 1.0, places=5)

    def test_orthogonal_vectors(self):
        v1 = self.space.encode("alpha")
        v2 = self.space.encode("beta")
        self.assertAlmostEqual(cosine(v1, v2), 0.0, places=5)

    def test_null_vector_returns_zero(self):
        v1 = self.space.encode("nothing relevant here")
        v2 = self.space.encode("alpha")
        self.assertEqual(cosine(v1, v2), 0.0)

    def test_handles_mismatched_bases(self):
        space2 = VerbSpace([Axis("a", "x", [r"alpha"])])
        v1 = self.space.encode("alpha")
        v2 = space2.encode("alpha")
        self.assertGreater(cosine(v1, v2), 0.0)


class TestDistanceMatrix(unittest.TestCase):

    def test_matrix_has_unity_diagonal(self):
        space = default_space()
        vectors = [
            space.encode("river carries sediment"),
            space.encode("receptor binds the ligand"),
        ]
        m = distance_matrix(vectors)
        self.assertAlmostEqual(m[0][0], 1.0, places=5)
        self.assertAlmostEqual(m[1][1], 1.0, places=5)


class TestDefaultAxes(unittest.TestCase):

    def test_twelve_axes(self):
        self.assertEqual(len(DEFAULT_AXES), 12)

    def test_each_axis_has_triggers(self):
        for ax in DEFAULT_AXES:
            self.assertTrue(ax.triggers, ax.name)

    def test_axis_names_unique(self):
        names = [ax.name for ax in DEFAULT_AXES]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
