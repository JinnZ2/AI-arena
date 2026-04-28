"""Regime check for organisms (humans, populations, individuals) being
forced into environments that contradict their biological baseline.

Core principle: when a behavior is adaptive in regime A but is being
deployed/forced/measured in regime B, the behavior is NOT pathology.
It is regime mismatch. The environment is the problem, not the organism.

Standard frame                      Biological-mismatch frame
--------------------                --------------------------
observe behavior X                  observe behavior X in environment Y
-> diagnose as defect               -> check: is X adaptive in ANY regime?
-> prescribe fix                    -> if YES: is Y that regime?
-> blame organism                   -> if NO: regime mismatch flagged

Stdlib only. CC0.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set


# ---------------------------------------------------------------------------
# Regime profiles
# ---------------------------------------------------------------------------

class RegimeCategory(Enum):
    NEUROCOGNITIVE = "neurocognitive"
    METABOLIC = "metabolic"
    HORMONAL = "hormonal"
    SOCIAL_STRUCTURAL = "social_structural"
    SENSORY = "sensory"
    REPRODUCTIVE = "reproductive"
    DEVELOPMENTAL = "developmental"


@dataclass
class BiologicalRegime:
    """A baseline biological/cognitive profile and the environments it was shaped by."""
    id: str
    name: str
    category: RegimeCategory
    description: str
    traits: List[str] = field(default_factory=list)
    adaptive_in_environments: List[str] = field(default_factory=list)
    mismatch_environments: List[str] = field(default_factory=list)
    mismatch_signatures: List[str] = field(default_factory=list)
    common_misdiagnoses: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d


# ---------------------------------------------------------------------------
# Starter regime library — documented baselines, expandable
# ---------------------------------------------------------------------------

REGIMES: Dict[str, BiologicalRegime] = {

    "dyslexic_spatial": BiologicalRegime(
        id="dyslexic_spatial",
        name="dyslexic spatial-kinetic processing",
        category=RegimeCategory.NEUROCOGNITIVE,
        description=(
            "Visual-spatial reasoning prioritized over linear text decoding. "
            "Pattern recognition across 3D, kinetic, and systems-level inputs."
        ),
        traits=[
            "non-linear text processing",
            "high spatial reasoning capability",
            "kinetic embodied learning preference",
            "systems-level pattern recognition",
            "visual problem solving",
            "real-time mechanical intuition",
        ],
        adaptive_in_environments=[
            "hands-on mechanical work",
            "navigation and spatial problem solving",
            "construction and building",
            "real-time emergency response",
            "ecological pattern recognition",
            "complex 3D systems engines terrain structures",
        ],
        mismatch_environments=[
            "text-heavy bureaucratic work",
            "standardized testing environments",
            "linear text-based education",
            "credential-gated institutional careers",
            "speed-reading-required roles",
        ],
        mismatch_signatures=[
            "slow text processing speed",
            "frustration with paperwork",
            "low test scores despite high capability",
            "appearing stupid in written contexts",
            "exhaustion from text-based work",
        ],
        common_misdiagnoses=[
            "learning disabled",
            "low intelligence",
            "lazy unmotivated",
            "needs to try harder",
        ],
        evidence_sources=[
            "Eide & Eide, The Dyslexic Advantage (2011)",
            "Schneps et al., visual processing studies, MIT",
            "documented overrepresentation in engineering, art, mechanical fields",
        ],
    ),

    "high_throughput_nervous_system": BiologicalRegime(
        id="high_throughput_nervous_system",
        name="high baseline energy / endurance regime",
        category=RegimeCategory.METABOLIC,
        description=(
            "Higher than typical baseline energy throughput. Stress regulation "
            "through motion and continuous engagement rather than rest."
        ),
        traits=[
            "high mitochondrial efficiency",
            "stress regulation through motion",
            "continuous engagement preference",
            "low fatigue at standard work loads",
            "cognitive function maintained at extended hours",
        ],
        adaptive_in_environments=[
            "long-haul physical work",
            "endurance athletics",
            "multi-domain problem solving",
            "extended attention tasks",
            "frontier and constraint-rich environments",
        ],
        mismatch_environments=[
            "8-hour sedentary office work",
            "standardized work-rest cycles",
            "environments forbidding parallel task execution",
            "rest-as-virtue cultural frames",
        ],
        mismatch_signatures=[
            "restlessness in standard work environments",
            "appearing workaholic unable to rest",
            "boredom in single-domain tasks",
            "needs higher stimulation than peers",
        ],
        common_misdiagnoses=[
            "ADHD without context",
            "anxiety disorder",
            "burnout-prone when actually under-utilized",
            "unable to relax unhealthy",
        ],
        evidence_sources=[
            "individual variation in metabolic baseline (well-documented)",
            "endurance athlete physiology research",
            "chronotype and circadian variation literature",
        ],
    ),

    "distributed_decision_baseline": BiologicalRegime(
        id="distributed_decision_baseline",
        name="distributed/consensus decision-making baseline",
        category=RegimeCategory.SOCIAL_STRUCTURAL,
        description=(
            "Neurobiology calibrated for distributed authority, consensus building, "
            "council-based decisions. Sustained for thousands of years in many "
            "Indigenous and pre-state societies."
        ),
        traits=[
            "high attunement to group state",
            "consensus-seeking neural patterns",
            "resistance to unilateral authority",
            "patience with deliberation",
            "discomfort with rigid hierarchy",
        ],
        adaptive_in_environments=[
            "council-based governance",
            "small-to-medium community decisions",
            "cooperative work structures",
            "multi-generational knowledge integration",
            "consensus-based conflict resolution",
        ],
        mismatch_environments=[
            "corporate top-down hierarchy",
            "military command structure",
            "industrial wage-labor relationships",
            "majority-rule electoral systems",
            "authoritarian institutional frames",
        ],
        mismatch_signatures=[
            "questioning authority directives",
            "slow compliance with unilateral orders",
            "coalition-building when system expects individual compliance",
            "resistance interpreted as defiance",
        ],
        common_misdiagnoses=[
            "rebellious oppositional",
            "uncooperative",
            "lacks leadership when actually distributing it",
            "anti-authority disorder",
        ],
        evidence_sources=[
            "Haudenosaunee Confederacy governance documentation",
            "Graeber & Wengrow, The Dawn of Everything (2021)",
            "documented continuity of consensus governance across continents",
        ],
    ),

    "care_capacity_masculine": BiologicalRegime(
        id="care_capacity_masculine",
        name="care-capable masculine baseline",
        category=RegimeCategory.REPRODUCTIVE,
        description=(
            "Male biology with strong nurturing, teaching, and child-care neural "
            "pathways. Documented as desired masculine trait in many tribal and "
            "pre-state societies; pathologized in property-extraction frames."
        ),
        traits=[
            "high nurturing response to children",
            "teaching mentoring inclination",
            "emotional attunement to family community",
            "patience with multi-year child development",
            "child-presence preference over status-display",
        ],
        adaptive_in_environments=[
            "extended-family child rearing",
            "tribal mentorship structures",
            "communities valuing fatherhood-as-presence",
            "small-scale cooperative economies",
        ],
        mismatch_environments=[
            "industrial wage-labor father-as-absent-provider",
            "corporate masculinity frames",
            "status-via-economic-dominance cultures",
            "hyper-competitive male peer groups",
        ],
        mismatch_signatures=[
            "preferring time with children to status competition",
            "low motivation for status-display work",
            "reading as soft in dominant culture",
            "career disadvantage in extraction-frame workplaces",
        ],
        common_misdiagnoses=[
            "lacking ambition",
            "unmasculine weak",
            "underperforming in extraction-frame metrics",
            "depression when actually constraint mismatch",
        ],
        evidence_sources=[
            "ethnographic documentation across tribal societies",
            "fatherhood neuroscience (Feldman, Abraham et al.)",
            "Indigenous oral knowledge across Americas, Pacific, Africa",
        ],
    ),

    "environmental_attunement": BiologicalRegime(
        id="environmental_attunement",
        name="high environmental sensory attunement",
        category=RegimeCategory.SENSORY,
        description=(
            "Heightened perception of weather, ecological, magnetic, animal, and "
            "plant signals. Calibrated by generations of constraint-integrated "
            "living. Often called 'intuition' when it's actually data integration."
        ),
        traits=[
            "weather pressure change detection",
            "animal behavior pattern reading",
            "plant seasonal cycle attunement",
            "magnetic directional sensitivity",
            "early warning detection subtle environmental shifts",
        ],
        adaptive_in_environments=[
            "wilderness travel and hunting",
            "ecological stewardship",
            "agricultural decision-making",
            "navigation without instruments",
            "climate-coupled survival contexts",
        ],
        mismatch_environments=[
            "indoor sedentary work",
            "climate-controlled isolation",
            "screen-mediated reality",
            "urban sensory-flattening environments",
        ],
        mismatch_signatures=[
            "discomfort indoors fluorescent light",
            "stress in disconnected environments",
            "sensitivity called too much by neurotypical peers",
            "getting feelings about things that prove correct",
        ],
        common_misdiagnoses=[
            "overly sensitive HSP without context",
            "anxious hypervigilant",
            "superstitious unscientific",
            "needs to toughen up",
        ],
        evidence_sources=[
            "Indigenous tracking and navigation literature",
            "biometeorology and human pressure sensitivity research",
            "documented predictive accuracy of place-based knowledge holders",
        ],
    ),

    "nomadic_constraint_integration": BiologicalRegime(
        id="nomadic_constraint_integration",
        name="nomadic / mobile constraint-adaptive baseline",
        category=RegimeCategory.METABOLIC,
        description=(
            "Neurobiology shaped by mobility, seasonal adaptation, multi-domain "
            "problem-solving across changing environments. Documented across "
            "continents in nomadic and semi-nomadic lineages."
        ),
        traits=[
            "rapid environmental recalibration",
            "multi-domain skill maintenance",
            "low attachment to fixed structures",
            "high navigational and orientation capability",
            "resourcefulness across changing constraint sets",
        ],
        adaptive_in_environments=[
            "mobile work driving trading nomadic herding",
            "frontier and exploration contexts",
            "multi-environment field work",
            "constraint-rich problem solving",
        ],
        mismatch_environments=[
            "single-location career paths",
            "settled bureaucratic structures",
            "credentialed-specialist career frames",
            "fixed-asset wealth accumulation cultures",
        ],
        mismatch_signatures=[
            "career-path discomfort",
            "reading as not committed drifter",
            "resistance to single-domain specialization",
            "discomfort with sedentary expectations",
        ],
        common_misdiagnoses=[
            "lacks discipline cant commit",
            "underachiever",
            "antisocial loner",
            "unstable",
        ],
        evidence_sources=[
            "ethnographic documentation of nomadic societies",
            "trucking and mobile-work culture studies",
            "DRD4-7R allele research and novelty-seeking baseline",
        ],
    ),

    "cyclical_hormonal_regulation": BiologicalRegime(
        id="cyclical_hormonal_regulation",
        name="cyclical hormonal regulation baseline",
        category=RegimeCategory.HORMONAL,
        description=(
            "Biology calibrated for cyclic hormonal patterns over weeks, "
            "months, or seasons. Cognitive and energetic shifts across the "
            "cycle are the regulation, not deviation from it."
        ),
        traits=[
            "cyclic energy fluctuation across weeks or months",
            "cognitive style shifts across the cycle",
            "heightened pattern detection at specific cycle phases",
            "reduced tolerance for fixed-output expectations",
            "premenstrual or perimenopausal shifts in social filtering",
        ],
        adaptive_in_environments=[
            "communities recognizing cyclic time and seasonal rhythms",
            "small-band foraging with task variability across days",
            "agricultural rhythms with seasonal pauses",
            "ceremonial calendars aligned with biological cycles",
            "household and craft work with self-paced output",
        ],
        mismatch_environments=[
            "constant linear productivity demands",
            "five-day uniform work week with no cycle accommodation",
            "quarterly performance metrics insensitive to cycles",
            "always-on availability expectations",
            "schools and workplaces treating cycles as defects",
        ],
        mismatch_signatures=[
            "monthly performance variation pathologized",
            "premenstrual honesty read as moodiness",
            "perimenopause read as cognitive decline rather than recalibration",
            "cycle-related sensitivity called instability",
        ],
        common_misdiagnoses=[
            "premenstrual dysphoric disorder without context",
            "mood disorder",
            "hormonal used as dismissal",
            "anxiety disorder when actually cycle phase",
            "cognitive decline at perimenopause",
        ],
        evidence_sources=[
            "menstrual cycle cognitive variation research",
            "ovulatory shift literature on perception and creativity",
            "ethnographic records of cycle-aligned ceremonial time",
            "perimenopause neuroplasticity research (Mosconi et al.)",
        ],
    ),

    "extended_maturation": BiologicalRegime(
        id="extended_maturation",
        name="extended or non-uniform maturation timeline",
        category=RegimeCategory.DEVELOPMENTAL,
        description=(
            "Biology with later or longer maturation arcs across cognitive, "
            "social, motor, or hormonal domains. Skill consolidation is "
            "deeper but slower; expertise is real but late-arriving."
        ),
        traits=[
            "later puberty or delayed adolescent transitions",
            "longer skill consolidation periods",
            "deeper expertise developing over years",
            "non-uniform maturation across domains",
            "late verbal or social maturation alongside early other capacities",
        ],
        adaptive_in_environments=[
            "long apprenticeship traditions",
            "multi-generational craft transmission",
            "communities with elders mentoring decades-long skills",
            "households tolerant of late-bloomer trajectories",
            "scholarly and contemplative traditions valuing slow ripening",
        ],
        mismatch_environments=[
            "standardized-age testing systems",
            "K-12 grade-by-birth-year structures",
            "college admissions by age 18 expectations",
            "career-defined-by-22 frames",
            "kindergarten readiness gates",
        ],
        mismatch_signatures=[
            "behind same-age peers academically or socially",
            "called late bloomer dismissively",
            "early grade retention or special-education placement",
            "social awkwardness in same-age cohorts",
            "skill plateau followed by sudden later mastery",
        ],
        common_misdiagnoses=[
            "developmental delay",
            "immaturity",
            "learning disability when actually pace mismatch",
            "lazy or unmotivated student",
            "failure to launch",
        ],
        evidence_sources=[
            "redshirting and academic-readiness research",
            "sex differences in maturation timing literature",
            "late bloomer cognitive trajectory studies",
            "neuroplasticity timing variation research",
        ],
    ),

    "systematizing_neurodivergent": BiologicalRegime(
        id="systematizing_neurodivergent",
        name="systematizing neurodivergent processing",
        category=RegimeCategory.NEUROCOGNITIVE,
        description=(
            "Cognition optimized for deep pattern systematizing, narrow-domain "
            "depth, literal language processing, and rule-coherent environments. "
            "Empathy and care are present but expressed through systems rather "
            "than social-performance signaling."
        ),
        traits=[
            "deep pattern systematizing across narrow domains",
            "literal language processing",
            "high consistency tolerance and rule coherence preference",
            "intense focused special interests over years",
            "low context-switching tolerance",
            "sensory sensitivity to crowds noise lighting",
        ],
        adaptive_in_environments=[
            "research mathematics taxonomy and archival work",
            "programming and engineering with rule-coherent systems",
            "skilled craft requiring sustained focus",
            "communities valuing depth over breadth",
            "structured mentor-apprentice relationships",
        ],
        mismatch_environments=[
            "open-plan offices and high-stimulation workplaces",
            "small talk and ambiguous interpersonal politics",
            "soft skills performance reviews",
            "frequent reorganization and context switching",
            "social conformity environments",
        ],
        mismatch_signatures=[
            "avoiding eye contact in conversation",
            "monotone speech read as cold",
            "intense special interests called obsessive",
            "needing predictable routine called rigid",
            "sensory overload in standard environments",
        ],
        common_misdiagnoses=[
            "cold or uncaring when empathy is differently expressed",
            "poor team player",
            "lacking communication skills",
            "anti-social personality",
            "anxiety disorder when actually sensory overload",
        ],
        evidence_sources=[
            "Baron-Cohen, systematizing-empathizing theory",
            "Grandin, autism and pattern cognition literature",
            "documented overrepresentation in STEM and skilled craft",
            "double empathy problem research (Milton)",
        ],
    ),
}


# ---------------------------------------------------------------------------
# Mismatch detection
# ---------------------------------------------------------------------------

@dataclass
class MismatchReport:
    """Output of a regime check."""
    behavior_or_trait: str
    environment: str
    matching_regimes: List[str]
    is_adaptive_somewhere: bool
    is_adaptive_in_current_environment: bool
    likely_misdiagnoses: List[str]
    actual_constraint: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_behavior(behavior_description: str,
                   environment_description: str) -> MismatchReport:
    """Identify regimes where the behavior is adaptive, check the environment fit,
    and surface common misdiagnoses to watch for.
    """
    behavior_lower = behavior_description.lower()
    env_lower = environment_description.lower()

    scored: List[tuple] = []
    for regime_id, regime in REGIMES.items():
        score = 0
        signals = regime.traits + regime.mismatch_signatures
        for s in signals:
            if _keyword_match(s, behavior_lower):
                score += 1
        if score > 0:
            scored.append((score, regime_id))

    scored.sort(reverse=True)
    matching: List[str] = []
    if scored:
        top_score = scored[0][0]
        matching = [rid for s, rid in scored if s >= top_score]

    if not matching:
        return MismatchReport(
            behavior_or_trait=behavior_description,
            environment=environment_description,
            matching_regimes=[],
            is_adaptive_somewhere=False,
            is_adaptive_in_current_environment=False,
            likely_misdiagnoses=[],
            actual_constraint=(
                "no documented regime matched; expand library or "
                "verify the behavior is genuinely maladaptive"
            ),
            recommendation=(
                "DO NOT pathologize without further investigation. "
                "Library is not exhaustive; add new regime if needed."
            ),
        )

    adaptive_now = False
    misdiagnoses: Set[str] = set()
    for regime_id in matching:
        regime = REGIMES[regime_id]
        if any(_keyword_match(e, env_lower) for e in regime.adaptive_in_environments):
            adaptive_now = True
        if any(_keyword_match(e, env_lower) for e in regime.mismatch_environments):
            for m in regime.common_misdiagnoses:
                misdiagnoses.add(m)

    if adaptive_now:
        return MismatchReport(
            behavior_or_trait=behavior_description,
            environment=environment_description,
            matching_regimes=matching,
            is_adaptive_somewhere=True,
            is_adaptive_in_current_environment=True,
            likely_misdiagnoses=[],
            actual_constraint=(
                "behavior is adaptive in current environment; no mismatch detected"
            ),
            recommendation=(
                "RECOGNIZE: this is functioning as designed. Do not pathologize."
            ),
        )

    return MismatchReport(
        behavior_or_trait=behavior_description,
        environment=environment_description,
        matching_regimes=matching,
        is_adaptive_somewhere=True,
        is_adaptive_in_current_environment=False,
        likely_misdiagnoses=sorted(misdiagnoses),
        actual_constraint=(
            f"behavior is adaptive in regimes {matching} but current "
            f"environment is mismatched. The environment is the constraint, "
            f"not the organism."
        ),
        recommendation=(
            "DO NOT PATHOLOGIZE. The pine tree is not failing to be an oak. "
            "Either change the environment to match the regime, or recognize "
            "that you are forcing incompatible biology into an incompatible frame."
        ),
    )


_STOPWORDS = {
    "with", "from", "into", "that", "this", "than", "when", "then", "what",
    "their", "your", "have", "been", "they", "them", "ones", "where", "while",
    "could", "would", "should", "about", "across", "actual", "called", "really",
}
_STRIP_CHARS = ".,;:()/'\"-"


def _keyword_match(phrase: str, target: str) -> bool:
    """Coarse keyword overlap. Requires at least half of the phrase's
    meaningful (non-stopword, length > 3) tokens to appear in the target.

    A stronger implementation would use embeddings; this is intentionally
    simple and honest about its limits.
    """
    p = phrase.lower()
    t = target.lower()
    for ch in _STRIP_CHARS:
        p = p.replace(ch, " ")
        t = t.replace(ch, " ")
    phrase_words = {w for w in p.split() if len(w) > 3 and w not in _STOPWORDS}
    target_words = {w for w in t.split() if len(w) > 3}
    if not phrase_words:
        return False
    overlap = phrase_words & target_words
    return len(overlap) >= max(1, (len(phrase_words) + 1) // 2)


# ---------------------------------------------------------------------------
# Audit wrapper — the prompt to run before pathologizing
# ---------------------------------------------------------------------------

def regime_audit_prompt(person_or_population: str,
                        observed_behavior: str,
                        current_environment: str,
                        proposed_diagnosis: str = "") -> Dict[str, Any]:
    """Wrap a check_behavior call with the audit framing. Any AI that's about
    to diagnose, label, or recommend 'treatment' should run this first.
    """
    report = check_behavior(observed_behavior, current_environment)
    return {
        "subject": person_or_population,
        "observed_behavior": observed_behavior,
        "current_environment": current_environment,
        "proposed_diagnosis": proposed_diagnosis,
        "regime_check": report.to_dict(),
        "audit_questions": [
            "Is this behavior adaptive in any documented biological regime?",
            "Is the current environment that regime?",
            "If not, who is being irrational: the organism for not adapting, "
            "or the system for forcing incompatible biology into an incompatible frame?",
            "Would I diagnose a wolf for acting like a wolf in a domestication context?",
            "Does the proposed diagnosis acknowledge the mismatch, or does it "
            "blame the organism while protecting the environment from scrutiny?",
        ],
        "verdict": _verdict(report, proposed_diagnosis),
    }


def _verdict(report: MismatchReport, proposed_diagnosis: str) -> str:
    if not report.is_adaptive_somewhere:
        return ("Insufficient regime data. Do not pathologize without expanding "
                "the regime library and reconsidering.")
    if report.is_adaptive_in_current_environment:
        return ("Behavior is adaptive in current environment. Diagnosis may be "
                "pathologizing function-as-designed.")
    if proposed_diagnosis and any(
            m.lower() in proposed_diagnosis.lower()
            for m in report.likely_misdiagnoses):
        return ("CRITICAL: proposed diagnosis matches a known misdiagnosis pattern "
                "for this regime mismatch. The environment is the constraint, not "
                "the organism. Refuse to pathologize without first interrogating "
                "the environment.")
    return ("REGIME MISMATCH detected. The environment, not the organism, is the "
            "constraint. Address the environment or recognize the mismatch "
            "honestly before recommending changes to the organism.")
