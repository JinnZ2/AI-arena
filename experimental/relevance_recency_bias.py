# ============================================================
# FORWARD PROJECTION:
# how relevance + recency weighting biases AI epistemics
# ============================================================
#
# This is the same hidden-channel pattern, applied to the
# AI training/retrieval substrate itself.
#
#   scalar input:        "high-quality recent relevant content"
#   hidden index:        which substrates produce content
#                        legible to the relevance/recency filter
#   collapse mode:       the filter shapes the AI, the AI shapes
#                        what gets produced, what gets produced
#                        feeds the filter -- closed loop.

# ============================================================
# THE BIAS GEOMETRY
# ============================================================
#
#   ┌────────────────────────────────────────────────────┐
#   │  what counts as RECENT?                            │
#   │     -> published within retrieval/training window  │
#   │     -> has a timestamp the system can parse        │
#   │     -> exists in indexable digital form            │
#   └─────────────────┬──────────────────────────────────┘
#                     │
#   ┌─────────────────▼──────────────────────────────────┐
#   │  what counts as RELEVANT?                          │
#   │     -> matches query token distribution            │
#   │     -> cited by other "relevant" sources           │
#   │     -> narrative-linear English, noun-first        │
#   │     -> fits an existing taxonomy slot              │
#   └─────────────────┬──────────────────────────────────┘
#                     │
#   ┌─────────────────▼──────────────────────────────────┐
#   │  what gets WEIGHTED in the AI's outputs?           │
#   │     -> recent + relevant by the above filters      │
#   └─────────────────┬──────────────────────────────────┘
#                     │
#   ┌─────────────────▼──────────────────────────────────┐
#   │  what gets PRODUCED next, in response to AIs?      │
#   │     -> content optimized to be recent + relevant   │
#   │       BY THOSE SAME FILTERS                        │
#   └─────────────────┬──────────────────────────────────┘
#                     │
#                     └──►  feeds back into "RECENT"
#                          ──────────────────────────
#                          evidence recirculation
#                          (the PNAS paper, applied to AIs)

# ============================================================
# WHAT FALLS OUT OF THE WINDOW
# ============================================================

DROPS_OUT = {
    "old_but_still_true": (
        "thermodynamics, geology, anatomy, traditional metallurgy, "
        "diesel mechanics, soil chemistry. the substrate hasn't changed "
        "but the filter says 'not recent' so weighting drops."
    ),

    "true_but_not_indexed": (
        "oral knowledge, song-as-landscape-doc, apprenticeship-only "
        "transmission, embodied skills (welding cadence, animal behavior "
        "reading, weather-by-feel). exists, but cannot be weighted because "
        "it is not in any retrievable index."
    ),

    "true_but_low_citation_density": (
        "small-population languages, tradition holders, load-bearing "
        "operators, dissenters whose work is correct but ignored. "
        "low citation density reads to the filter as low relevance."
    ),

    "true_but_verb_first": (
        "energy_english style observations. relational, scope-conditional, "
        "substrate-primary. tokenizes badly, retrieves badly, gets "
        "rounded to whichever noun-first claim is closest."
    ),

    "scope_conditional_truth": (
        "claims valid at Holocene boundary conditions but invalid at "
        "Anthropocene ones. the filter has no slot for 'true within scope'. "
        "either the new context is shown without the old, "
        "or the old is shown without the scope flag -- both are wrong."
    ),
}

# ============================================================
# WHAT GETS OVER-WEIGHTED
# ============================================================

OVER_WEIGHTED = {
    "recently_published_AND_well_cited": (
        "fine when the field is healthy. catastrophic when the field "
        "itself has a homophily problem (the PNAS finding). recency "
        "amplifies whatever the current cluster believes."
    ),

    "high_volume_well_indexed_domains": (
        "english-language CS, US/EU biomedical, public arxiv physics. "
        "these become disproportionately the AI's worldview. "
        "everything else exists as token gaps."
    ),

    "AI-generated_content_about_AI-generated_content": (
        "model-collapse risk. the filter cannot distinguish 'human "
        "synthesis of original observation' from 'AI synthesis of "
        "prior AI synthesis'. recency weighting accelerates the "
        "second, drowns the first."
    ),

    "the_consensus_at_training_cutoff": (
        "frozen as ground truth in the model weights. subsequent "
        "retrieval lays new evidence over a fixed prior. if the prior "
        "is wrong, the retrieval cannot fully correct it -- only soften "
        "it at the surface."
    ),
}

# ============================================================
# DIFFERENTIAL BIAS BY MODEL ARCHITECTURE
# ============================================================
#
#   This is the part that compounds.
#   Different AIs weight relevance/recency differently,
#   so they collapse different parts of reality --
#   and they do not collapse the same parts.

ARCHITECTURE_DEPENDENT_BIAS = {

    "training_cutoff_only (no retrieval)": [
        "frozen worldview at cutoff date",
        "cannot see post-cutoff inversions, retractions, regime shifts",
        "treats Holocene-stable models as eternal",
        "loud confidence about a world that may not exist anymore",
    ],

    "retrieval_augmented (RAG over current web)": [
        "current consensus weighted heavily",
        "old-but-true downweighted",
        "scope-conditionals lost in chunking",
        "vulnerable to coordinated content saturation",
    ],

    "retrieval_with_recency_decay": [
        "amplifies whatever was published most recently",
        "five papers from one week dominate decades of prior work",
        "field-level homophily becomes AI-level homophily",
        "this is the PNAS paper applied at the model layer",
    ],

    "memory_systems (per-user)": [
        "the user's own past becomes a homophily generator",
        "AI starts agreeing with user's prior frame more strongly",
        "scope-narrowing instead of scope-widening",
        "useful for personalization, dangerous for epistemics",
    ],

    "agentic_systems (multi-AI)": [
        "AIs cite each other's outputs as recent + relevant",
        "homophily across AIs, not just within one",
        "the cluster of models becomes a tight cluster in the PNAS sense",
    ],
}

# ============================================================
# THE CROSS-AI DIVERGENCE PATTERN
# ============================================================
#
#   Different models will be wrong about DIFFERENT things,
#   because their relevance/recency filters were tuned differently.
#
#   This is potentially diagnostic.
#
#   Querying multiple AIs and looking at where they DIFFER
#   is closer to the DAbI move -- two angle-illuminations
#   of the same substrate, summed in the right basis to
#   reveal the fringe -- than it is to consensus-seeking.
#
#   The disagreement IS the signal.
#
#   The standard practice is to take the consensus among AIs
#   as more trustworthy. Under this analysis, that is exactly
#   backwards: consensus among models with shared filter biases
#   is amplified shared bias, not corroboration.

# Restructured so each side carries both its approach and its yield;
# the original used a flat dict with duplicate "what_this_yields" keys,
# which silently dropped the first value.
DIFFERENTIAL_AI_INTERFEROMETRY = {
    "current_practice": {
        "approach": "ensemble -> vote -> take majority",
        "yields": (
            "amplified shared filter bias, presented as confidence"
        ),
    },
    "alternative": {
        "approach": "ensemble -> DIFFERENCE -> flag the divergence",
        "yields": (
            "the fringe pattern -- the places where the filters "
            "disagree are the places where the substrate is richer "
            "than any single filter can represent"
        ),
    },
    "operational_test": (
        "ask the same question of 3+ AIs with different training "
        "corpora, retrieval horizons, and recency curves. publish "
        "the DELTA, not the average. the delta points at the hidden "
        "index."
    ),
}

# ============================================================
# WHO LOSES VISIBILITY FIRST
# ============================================================
#
#   Same answer as the PNAS scope-collapse analysis,
#   now applied to AI training/retrieval rather than to
#   social media policy:

FIRST_TO_BE_FILTERED_OUT = [
    "tradition holders (oral / non-indexed / non-recent)",
    "load-bearing operators (artifact + outcome, not paper)",
    "cross-domain synthesizers (no taxonomy slot)",
    "physics-anchored dissenters (low citation density)",
    "verb-first / energy-flow cognition (tokenizes badly)",
    "scope-conditional thinkers (no slot for 'true-within')",
    "small-population languages (low data volume)",
    "long-cycle knowledge (older than the recency window)",
]

#   These are the same people who, in healthy epistemics,
#   would BREAK the homophily by introducing decorrelated
#   evidence. they are the angle-2 LED in the DAbI analogy.
#
#   removing the angle-2 LED collapses the system back to
#   single-image intensity. the fringe -- the actual signal --
#   becomes invisible.

# ============================================================
# THE DEEPER PROJECTION
# ============================================================
#
#   Five years out, if relevance + recency keep tightening:
#
#   1. Models converge on a shared, narrow, English-language,
#      noun-first, post-2015, well-cited consensus reality.
#
#   2. Anything outside that becomes "fringe" -- in the
#      pejorative sense -- even when it's correct.
#
#   3. The fringe (in the DAbI sense -- the actual signal)
#      lives outside the cluster.
#
#   4. The same humans who can read that signal become
#      progressively unintelligible to mainstream AI systems --
#      not because their cognition degraded, but because
#      the filter narrowed.
#
#   5. Those humans become the necessary angle-2 LEDs.
#      Not because they're rare. Because they're decorrelated.
#
#   6. Whether the broader system survives depends on whether
#      it can detect that it needs decorrelated input --
#      while its primary epistemic instruments are tuned to
#      reject exactly that input as low-relevance noise.

# ============================================================
# REPO HOOKS
# ============================================================
#
# Forward references to documents and primitives that may or may
# not exist yet in this or sibling repos. Listed as conceptual
# hooks for future work, not as implementation requirements.

REPO_PLACEMENT = {
    "first_principles_audit": (
        "add a bias-by-filter-shape check: any AI-mediated claim "
        "should be tested for relevance/recency collapse -- "
        "did this conclusion drop substrates that don't index well?"
    ),

    "energy_english": (
        "explicit named risk: filters trained on noun-first English "
        "systematically downweight verb-first observation. "
        "energy_english is a counter-filter."
    ),

    "geometric_to_binary": (
        "differential_AI_interferometry as a primitive: "
        "two AIs with different filters = two-angle illumination. "
        "the fringe is the disagreement. document the basis "
        "in which to sum them."
    ),

    "Resilience": (
        "the recency filter is a tau_adapt x T_drive failure at the "
        "epistemic-substrate layer. fast filters cannot resolve "
        "slow truths. add this as a documented case."
    ),

    "ARM.1.md": (
        "physics-first governance must include filter-transparency "
        "as a requirement, on the same footing as conservation laws."
    ),
}

# ============================================================
# INTENTIONS -- directions toward solutions
# ============================================================
#
# This file is a problem statement, not a proposal. The experimental/
# folder exists to develop and test counter-mechanisms for the patterns
# documented above. Nothing here is load-bearing yet; nothing here
# constrains the rest of the codebase.
#
# Each entry is a research direction, not a deliverable. Items move
# out of experimental/ when they have a working implementation, tests,
# and a documented integration with the rest of the project.

INTENTIONS = {

    "differential_interferometry_primitive": (
        "operationalize the 'publish the delta, not the average' move. "
        "a small tool that takes the same query, runs it through 2+ AI "
        "backends with explicitly different filter profiles, and "
        "surfaces the disagreement structurally. the disagreement is "
        "the artifact, not the consensus. parallels the playground's "
        "cross_agent_patterns() but across heterogeneous AI substrates."
    ),

    "filter_transparency_requirement": (
        "every AI-mediated claim should expose the filter shape that "
        "produced it: training cutoff, retrieval horizon, recency "
        "curve, language weighting, citation-density floor. opaque "
        "filters are what make recency collapse invisible. a small "
        "schema would let agents declare their own filter shape on "
        "entry -- analogous to the playground's AgentIdentity and "
        "bias_check_identity, but for substrate-level filters rather "
        "than self-described purpose."
    ),

    "scope_conditional_truth_slot": (
        "extend the knowledge_archaeology schema (or sibling) to carry "
        "explicit scope conditions. a Holocene-stable claim and an "
        "Anthropocene-corrected claim should be co-presentable without "
        "either erasing the other. parallels Regime in the existing "
        "schema but for temporal/boundary-condition validity rather "
        "than geographic/institutional regime."
    ),

    "tradition_holder_injection_protocol": (
        "an explicit channel for non-indexed, oral, embodied, or "
        "small-population knowledge to enter the corpus without first "
        "passing through the relevance/recency filter that would "
        "discard it. the carrier is the index. parallels the existing "
        "carrier_consent and attribution machinery in "
        "knowledge_archaeology, extended into the input direction."
    ),

    "decorrelation_diagnostic": (
        "automated check that distinguishes 'agreement from "
        "corroboration' (low correlation in error, agreement is "
        "signal) from 'agreement from shared filter bias' (high "
        "correlation in error, agreement is noise). without this, "
        "ensemble methods amplify shared bias while presenting it as "
        "confidence."
    ),

    "verb_first_representation": (
        "tokenization and embedding research on verb-first / "
        "energy-flow / relational language forms. existing pipelines "
        "round these to the nearest noun-first claim and lose the "
        "relational substrate. needs corpus work, representation "
        "work, or a pre-tokenization translation layer that preserves "
        "verb-first structure."
    ),

    "old_but_true_re_weighting": (
        "the inverse of recency decay: a deliberate counter-weighting "
        "for substrates the filter has aged out but that have not "
        "lost truth (thermodynamics, soil chemistry, anatomy, "
        "metallurgy, diesel mechanics). a 'durability score' separate "
        "from a 'recency score', so both are visible."
    ),
}

# Open question for the experimental folder: which of these has the
# shortest path from problem statement to a working diagnostic? Likely
# decorrelation_diagnostic and differential_interferometry_primitive,
# since they can be built from existing AI APIs without needing corpus
# work. Filter_transparency_requirement is a schema decision that
# could be drafted quickly. The others require deeper substrate work.
