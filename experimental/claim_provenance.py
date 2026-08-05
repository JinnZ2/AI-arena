"""
claim_provenance.py

Multi-agent claim provenance on subjective logic (Jøsang opinions).

A claim is not a truth value. It is a record of who said what, on whose
authority, and how much of the resulting confidence is borrowed rather than
earned. This module keeps that record attached to the claim for its whole
life — through evidence arrival, dialectical attack, revision, and dormancy.

Three properties the arithmetic is chosen for:

  uncertainty is first-class      an Opinion carries (b, d, u); "nobody knows"
                                  is a representable state, not a 0.5
  trust is per-source             agent A's trust in B is A's own Opinion about
                                  B. it is never a pool, never transferred from
                                  a "loser" to a "winner", never zero-sum
  correlation is priced           cumulative fusion assumes independent
                                  evidence. agents reading the same sources are
                                  not independent, so their redundancy is
                                  measured and their contribution diluted
                                  before fusion. echo is not evidence

consensus() collapses the fused opinion into a single status. That collapse is
v1-shaped and is kept because status transitions drive the iteration loop.
disagreement_map() is the non-collapsing view: per-agent opinions, the spread
between them, and named disagreement_categories — the shape v2 wants, and the
shape energy_english emits. When the two disagree, the map is the finding and
the status is a summary. DISPUTED exists so a split pool is never reported as
though it converged.

Trajectories, not verdicts. Re-runnable. Refutable.
stdlib only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Sequence, Set, Tuple

EPS = 1e-9


# ---------- Opinion (trust currency) ----------

@dataclass
class Opinion:
    """Subjective logic opinion: belief, disbelief, uncertainty, base rate."""

    b: float  # belief
    d: float  # disbelief
    u: float  # uncertainty
    a: float  # base rate (default prior)

    def __post_init__(self):
        # clamp float drift before normalizing; a negative mass is meaningless
        self.b = max(0.0, self.b)
        self.d = max(0.0, self.d)
        self.u = max(0.0, self.u)
        self.a = min(1.0, max(0.0, self.a))
        total = self.b + self.d + self.u
        if total < EPS:
            # no mass at all -> the honest reading is "no information"
            self.b, self.d, self.u = 0.0, 0.0, 1.0
            return
        if abs(total - 1.0) > 1e-6:
            self.b /= total
            self.d /= total
            self.u /= total

    @property
    def expectation(self) -> float:
        """Projected probability: belief plus the base-rate share of uncertainty."""
        return self.b + self.a * self.u

    @property
    def is_vacuous(self) -> bool:
        """Total uncertainty — carries no evidence either way."""
        return self.u > 1.0 - 1e-6

    def discount(self, trust: "Opinion") -> "Opinion":
        """Trust discounter: B's opinion about X discounted by A's trust in B.

        Distrust and ignorance both land in uncertainty — an untrusted source
        does not create disbelief in the claim, it creates no information.
        """
        b_new = trust.b * self.b
        d_new = trust.b * self.d
        u_new = 1.0 - b_new - d_new
        return Opinion(b_new, d_new, u_new, self.a)

    def dilute(self, weight: float) -> "Opinion":
        """Scale evidential mass by weight in [0, 1], moving the rest to uncertainty.

        weight=1 is identity, weight=0 is fully vacuous. Used to price
        redundancy: a second agent echoing the first's sources contributes
        proportionally less.
        """
        w = min(1.0, max(0.0, weight))
        return Opinion(self.b * w, self.d * w, 1.0 - w * (self.b + self.d), self.a)

    def negate(self) -> "Opinion":
        """Complementary opinion (for attack relations)."""
        return Opinion(self.d, self.b, self.u, 1.0 - self.a)

    @staticmethod
    def vacuous(a: float = 0.5) -> "Opinion":
        return Opinion(0.0, 0.0, 1.0, a)

    @staticmethod
    def from_relevance(relevance: float, a: float = 0.5) -> "Opinion":
        """Evidence relevance in [0, 1] read as a dogmatic belief/disbelief split."""
        r = min(1.0, max(0.0, relevance))
        return Opinion(r, 1.0 - r, 0.0, a)

    @staticmethod
    def cumulative_fuse(op1: "Opinion", op2: "Opinion") -> "Opinion":
        """Independent evidence fusion (cumulative).

        Assumes op1 and op2 rest on independent evidence. They usually do not;
        see ClaimNetwork.consensus for where that assumption is paid for.
        """
        if op1.u < EPS and op2.u < EPS:
            # two dogmatic opinions: fusion is undefined, average instead
            b = (op1.b + op2.b) / 2
            return Opinion(b, 1 - b, 0, (op1.a + op2.a) / 2)
        denom = op1.u + op2.u - (op1.u * op2.u)
        if denom < EPS:
            return Opinion(0, 0, 1, (op1.a + op2.a) / 2)
        u = (op1.u * op2.u) / denom
        b = (op1.b * op2.u + op2.b * op1.u) / denom
        d = 1 - b - u
        return Opinion(b, d, u, (op1.a + op2.a) / 2)


# ---------- Claim statuses (non-affirmative) ----------

class ClaimStatus(Enum):
    PROPOSED = "proposed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNKNOWN = "unknown"          # nobody has an opinion at all
    UNDEC = "undecided"          # opinions exist, none dominant
    NEI = "not_enough_info"      # uncertainty dominates the pool
    DORMANT = "dormant"          # superseded by a revision, kept for provenance
    DISPUTED = "disputed"        # the pool is split — do not collapse this


#: Statuses that end a claim's active life.
TERMINAL_STATUSES = (ClaimStatus.VERIFIED, ClaimStatus.REFUTED, ClaimStatus.DORMANT)


# ---------- Evidence ----------

@dataclass
class Evidence:
    source_agent_id: int
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    relevance: float = 0.5  # how much this evidence supports the claim (0-1)


# ---------- Claim with provenance ----------

@dataclass
class Claim:
    id: int
    statement: str
    status: ClaimStatus = ClaimStatus.PROPOSED
    opinion: Optional[Opinion] = None
    evidence: List[Evidence] = field(default_factory=list)
    derivation_method: str = ""
    was_revision_of: Optional[int] = None
    history: List[str] = field(default_factory=list)

    def add_evidence(self, ev: Evidence) -> bool:
        """Attach evidence. A source repeating itself verbatim is not new evidence.

        Returns False (and logs the echo) when the same source has already said
        the same thing — otherwise cumulative fusion would read one observation
        as two.
        """
        for existing in self.evidence:
            if existing.source_agent_id == ev.source_agent_id and existing.content == ev.content:
                self.history.append(f"Echo ignored from Agent{ev.source_agent_id}: {ev.content}")
                return False
        self.evidence.append(ev)
        self.history.append(f"Evidence from Agent{ev.source_agent_id}: {ev.content}")
        return True

    def log_event(self, msg: str):
        self.history.append(msg)

    @property
    def sources(self) -> Set[int]:
        """Every agent whose evidence this claim rests on."""
        return {ev.source_agent_id for ev in self.evidence}


# ---------- Agent with belief graph & trust ----------

class Agent:
    """An agent holds its own trust in others and its own opinion of each claim.

    Nothing here is shared state. Two agents seeing identical evidence can end
    at different opinions because they trust the sources differently, and that
    difference is the signal — not an error to be averaged out.
    """

    def __init__(self, agent_id: int, trust_opinions: Dict[int, Opinion] = None):
        self.id = agent_id
        self.trust = trust_opinions or {}  # other agent id -> Opinion (trust in them)
        self.belief_graph: Dict[int, Opinion] = {}  # claim_id -> Opinion
        self.knowledge_base: List[str] = []  # raw facts this agent has observed
        # claim_id -> the source agents that actually moved this agent's opinion.
        # this is what makes correlation measurable at consensus time.
        self.source_trace: Dict[int, Set[int]] = {}

    def trust_in(self, agent_id: int) -> Optional[Opinion]:
        """Explicit trust only. An unrated source is ignored, not assumed hostile."""
        return self.trust.get(agent_id)

    def evaluate_claim(self, claim: Claim, network: "ClaimNetwork") -> Opinion:
        """Form an opinion using local evidence, source trust, and graph edges.

        Dialectical edges read this agent's *existing* beliefs about antecedent
        claims, so an agent that has not yet evaluated an antecedent is simply
        not moved by it. Evaluate antecedents first if the edge should bite.
        """
        opinions: List[Opinion] = []
        sources: Set[int] = set()

        for ev in claim.evidence:
            trust_op = self.trust_in(ev.source_agent_id)
            if trust_op is None:
                continue
            base = Opinion.from_relevance(ev.relevance)
            opinions.append(base.discount(trust_op))
            sources.add(ev.source_agent_id)

        if not opinions:
            fused = Opinion.vacuous()  # complete uncertainty
        else:
            fused = opinions[0]
            for op in opinions[1:]:
                fused = Opinion.cumulative_fuse(fused, op)

        # Dialectical propagation (support / attack edges)
        for from_id, to_id, rel_type in network.argument_graph:
            if to_id != claim.id or from_id not in self.belief_graph:
                continue
            antecedent = self.belief_graph[from_id]
            if antecedent.is_vacuous:
                continue  # an opinion-free antecedent argues nothing
            if rel_type == "support":
                # support carries the antecedent's belief into the target
                carried = antecedent.b * fused.b
                supported = Opinion(carried, 1.0 - carried - antecedent.u, antecedent.u, fused.a)
                fused = Opinion.cumulative_fuse(fused, supported)
            elif rel_type == "attack":
                # attack carries the antecedent's belief into target disbelief
                fused = Opinion.cumulative_fuse(fused, antecedent.negate())
            sources.add(-from_id)  # negative keys mark claim-derived support

        self.source_trace[claim.id] = sources
        return fused


# ---------- Claim network ----------

def _jaccard(a: Set[int], b: Set[int]) -> float:
    """Overlap of two source sets. Two empty sets are treated as disjoint."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class DisagreementMap:
    """The non-collapsing view of a claim. This is the artifact, not the status."""

    claim_id: int
    per_agent: Dict[int, Opinion]
    spread: float                      # max - min projected probability
    mean_source_overlap: float         # 0 = independent pool, 1 = pure echo
    categories: List[str]
    believers: List[int]
    disbelievers: List[int]
    abstainers: List[int]              # agents holding a vacuous opinion

    @property
    def is_polarized(self) -> bool:
        return bool(self.believers) and bool(self.disbelievers)


class ClaimNetwork:
    def __init__(self, correlation_damping: float = 1.0):
        self.agents: Dict[int, Agent] = {}
        self.claims: Dict[int, Claim] = {}
        # (from_claim_id, to_claim_id, 'support' | 'attack')
        self.argument_graph: List[Tuple[int, int, str]] = []
        # 0 disables redundancy pricing (naive independence); 1 prices it fully
        self.correlation_damping = min(1.0, max(0.0, correlation_damping))

    def add_agent(self, agent: Agent):
        self.agents[agent.id] = agent

    def add_claim(self, claim: Claim):
        self.claims[claim.id] = claim

    def add_argument(self, from_claim: int, to_claim: int, relation: str):
        if relation not in ("support", "attack"):
            raise ValueError(f"unknown relation: {relation}")
        self.argument_graph.append((from_claim, to_claim, relation))
        self.claims[to_claim].log_event(f"{relation} edge from claim {from_claim}")

    def broadcast(self, claim_id: int, sender_id: Optional[int] = None):
        """All agents (except sender) evaluate the claim and update their beliefs."""
        claim = self.claims[claim_id]
        for agent_id in sorted(self.agents):
            if sender_id is not None and agent_id == sender_id:
                continue
            agent = self.agents[agent_id]
            opinion = agent.evaluate_claim(claim, self)
            agent.belief_graph[claim_id] = opinion
            claim.log_event(
                f"Agent{agent_id} opinion: b={opinion.b:.2f}, d={opinion.d:.2f}, u={opinion.u:.2f}"
            )

    # -- the collapsing view -------------------------------------------------

    def consensus(
        self,
        claim_id: int,
        tau_u: float = 0.3,
        tau_b: float = 0.6,
        tau_nei: float = 0.5,
    ) -> ClaimStatus:
        """Fuse agent opinions into one status, pricing correlation on the way.

        Agents are folded in a fixed order (by id). Each one is diluted by its
        maximum source overlap with the agents already folded in, so a pool of
        four agents reading one source cannot manufacture the confidence of four
        independent readings.

        A split pool returns DISPUTED. That is a real answer, not a failure to
        decide — see disagreement_map for what the split is made of.
        """
        ordered = [
            (aid, self.agents[aid].belief_graph[claim_id])
            for aid in sorted(self.agents)
            if claim_id in self.agents[aid].belief_graph
        ]
        if not ordered:
            return ClaimStatus.UNKNOWN

        dmap = self.disagreement_map(claim_id, tau_b=tau_b)

        fused: Optional[Opinion] = None
        folded: List[Set[int]] = []
        for aid, op in ordered:
            srcs = self.agents[aid].source_trace.get(claim_id, set())
            if fused is None:
                fused = op
            else:
                redundancy = max((_jaccard(srcs, prev) for prev in folded), default=0.0)
                weight = 1.0 - self.correlation_damping * redundancy
                fused = Opinion.cumulative_fuse(fused, op.dilute(weight))
            folded.append(srcs)

        claim = self.claims[claim_id]
        claim.opinion = fused  # store for provenance
        claim.log_event(
            f"fused: b={fused.b:.2f} d={fused.d:.2f} u={fused.u:.2f} "
            f"| spread={dmap.spread:.2f} overlap={dmap.mean_source_overlap:.2f}"
        )

        if dmap.is_polarized:
            return ClaimStatus.DISPUTED
        if fused.u < tau_u and fused.b > tau_b:
            return ClaimStatus.VERIFIED
        if fused.d > tau_b:
            return ClaimStatus.REFUTED
        if fused.u >= tau_nei:
            return ClaimStatus.NEI
        return ClaimStatus.UNDEC

    # -- the non-collapsing view --------------------------------------------

    def disagreement_map(self, claim_id: int, tau_b: float = 0.6) -> DisagreementMap:
        """Describe the disagreement instead of resolving it.

        categories are the handles v2 (and energy_english) work with:
          polarized          some agents believe, others disbelieve
          uncertainty_split  some agents hold evidence, others hold none
          echo               the pool is reading mostly the same sources
          independent_pool   the pool's sources barely overlap
          aligned            no meaningful spread
        """
        per_agent: Dict[int, Opinion] = {}
        traces: Dict[int, Set[int]] = {}
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            if claim_id in agent.belief_graph:
                per_agent[aid] = agent.belief_graph[claim_id]
                traces[aid] = agent.source_trace.get(claim_id, set())

        if not per_agent:
            return DisagreementMap(claim_id, {}, 0.0, 0.0, ["no_opinions"], [], [], [])

        believers = [aid for aid, op in per_agent.items() if op.b > tau_b]
        disbelievers = [aid for aid, op in per_agent.items() if op.d > tau_b]
        abstainers = [aid for aid, op in per_agent.items() if op.is_vacuous]

        expectations = [op.expectation for op in per_agent.values()]
        spread = max(expectations) - min(expectations)

        # abstainers have no sources; including them would dilute the overlap
        # figure and read a fully-echoing pool as independent
        ids = sorted(aid for aid in traces if traces[aid])
        pairs = [
            _jaccard(traces[i], traces[j])
            for k, i in enumerate(ids)
            for j in ids[k + 1:]
        ]
        overlap = sum(pairs) / len(pairs) if pairs else 0.0

        categories: List[str] = []
        if believers and disbelievers:
            categories.append("polarized")
        if abstainers and len(abstainers) < len(per_agent):
            categories.append("uncertainty_split")
        if len(per_agent) > 1:
            categories.append("echo" if overlap > 0.5 else "independent_pool")
        if not categories or (spread < 0.1 and "polarized" not in categories):
            categories.append("aligned")

        return DisagreementMap(
            claim_id=claim_id,
            per_agent=per_agent,
            spread=spread,
            mean_source_overlap=overlap,
            categories=categories,
            believers=believers,
            disbelievers=disbelievers,
            abstainers=abstainers,
        )

    # -- provenance ----------------------------------------------------------

    def provenance_chain(self, claim_id: int) -> List[int]:
        """Walk was_revision_of back to the root claim. Oldest first."""
        chain: List[int] = []
        seen: Set[int] = set()
        cur: Optional[int] = claim_id
        while cur is not None and cur in self.claims and cur not in seen:
            chain.append(cur)
            seen.add(cur)
            cur = self.claims[cur].was_revision_of
        return list(reversed(chain))

    def mark_dormant(self, claim_id: int, reason: str = "") -> ClaimStatus:
        """Retire a claim without deciding it. Provenance survives; the claim rests."""
        claim = self.claims[claim_id]
        if claim.status in (ClaimStatus.VERIFIED, ClaimStatus.REFUTED):
            return claim.status  # a decided claim is not put to sleep
        claim.status = ClaimStatus.DORMANT
        claim.log_event(f"dormant: {reason}" if reason else "dormant")
        return claim.status


# ---------- Integrated scientific method with multi-agent provenance ----------

class ProvenanceScientificFramework:
    """Combines SMF iteration with multi-agent claim testing and provenance."""

    def __init__(self, network: ClaimNetwork, verbose: bool = True, seed: Optional[int] = None):
        self.net = network
        self.claim_counter = 0
        self.current_claim: Optional[Claim] = None
        self.verbose = verbose
        self.rng = random.Random(seed)

    def _say(self, msg: str):
        if self.verbose:
            print(msg)

    def formulate_claim(
        self,
        statement: str,
        proposer_agent_id: int,
        initial_evidence: List[Evidence] = None,
        derivation_method: str = "",
        was_revision_of: Optional[int] = None,
    ) -> Claim:
        self.claim_counter += 1
        claim = Claim(
            id=self.claim_counter,
            statement=statement,
            status=ClaimStatus.PROPOSED,
            derivation_method=derivation_method,
            was_revision_of=was_revision_of,
        )
        claim.log_event(f"proposed by Agent{proposer_agent_id}")
        for ev in initial_evidence or []:
            claim.add_evidence(ev)
        self.net.add_claim(claim)
        self.current_claim = claim
        self._say(f"\n--- New claim formulated: [{claim.id}] {statement} ---")
        return claim

    def test_claim(self, claim_id: int) -> ClaimStatus:
        """Broadcast claim, let agents evaluate, then read both views."""
        claim = self.net.claims[claim_id]
        claim.status = ClaimStatus.VERIFYING
        self.net.broadcast(claim_id)
        status = self.net.consensus(claim_id)
        claim.status = status
        op = claim.opinion
        if op:
            self._say(
                f"Consensus opinion: b={op.b:.2f}, d={op.d:.2f}, u={op.u:.2f} -> {status.value}"
            )
        else:
            self._say(f"Consensus: {status.value}")
        dmap = self.net.disagreement_map(claim_id)
        self._say(f"Disagreement: {', '.join(dmap.categories)} (spread {dmap.spread:.2f})")
        return status

    def modify_claim(self, claim_id: int, new_evidence: List[Evidence] = None) -> Claim:
        """Create a revised version of an existing claim; retire the parent."""
        old_claim = self.net.claims[claim_id]
        proposer = min(old_claim.sources) if old_claim.sources else -1
        new_claim = self.formulate_claim(
            statement=f"(Revised) {old_claim.statement}",
            proposer_agent_id=proposer,
            initial_evidence=list(old_claim.evidence) + list(new_evidence or []),
            derivation_method="revision",
            was_revision_of=claim_id,
        )
        self.net.mark_dormant(claim_id, reason=f"superseded by claim {new_claim.id}")
        self._say(f"Claim modified -> [{new_claim.id}] {new_claim.statement}")
        return new_claim

    def hidden_variable_search(
        self,
        claim_id: int,
        content: str = "Hidden variable discovered: color coding",
        relevance: float = 0.9,
    ) -> Optional[Evidence]:
        """Look for evidence that would explain the anomaly, and record who found it.

        In a real system this queries the environment or re-runs inverse
        planning. Here the best-connected agent surfaces it — and the fact that
        it came from *that* agent stays attached to the claim.
        """
        if not self.net.agents:
            return None
        claim = self.net.claims[claim_id]
        best_agent = max(
            self.net.agents.values(),
            key=lambda a: (sum(o.b for o in a.trust.values()) if a.trust else 0.0, -a.id),
        )
        new_ev = Evidence(source_agent_id=best_agent.id, content=content, relevance=relevance)
        claim.add_evidence(new_ev)
        self._say(f"Hidden variable found by Agent{best_agent.id}: {new_ev.content}")
        return new_ev

    def iterate(self, max_iterations: int = 5):
        for i in range(max_iterations):
            self._say(f"\n========== Iteration {i+1} ==========")
            if self.current_claim is None:
                ev1 = Evidence(source_agent_id=1, content="Door is red", relevance=0.7)
                self.formulate_claim(
                    "The red door leads to the gem",
                    proposer_agent_id=1,
                    initial_evidence=[ev1],
                )
                continue

            status = self.test_claim(self.current_claim.id)

            if status in (ClaimStatus.VERIFIED, ClaimStatus.REFUTED):
                self._say(f"Claim resolved: {status.value}")
                if i < max_iterations - 1:
                    ev = Evidence(
                        source_agent_id=self.rng.choice(sorted(self.net.agents)),
                        content="Observed key color",
                        relevance=0.6,
                    )
                    self.formulate_claim(
                        "The key matches the door color",
                        proposer_agent_id=ev.source_agent_id,
                        initial_evidence=[ev],
                    )
            elif status is ClaimStatus.DISPUTED:
                # do not iterate a split into agreement. record it and move on.
                self._say("Claim disputed — split preserved, not resolved.")
                dmap = self.net.disagreement_map(self.current_claim.id)
                self._say(render_disagreement(dmap))
                self.net.mark_dormant(self.current_claim.id, reason="disputed split preserved")
                self.current_claim = None
            else:
                self._say(f"Claim unresolved ({status.value}), modifying...")
                self.hidden_variable_search(self.current_claim.id)
                self.current_claim = self.modify_claim(self.current_claim.id)

        self._say("\n=== Final claim statuses ===")
        for cid, claim in self.net.claims.items():
            self._say(f"Claim {cid}: {claim.status.value} | {claim.statement[:50]}...")


# ---------- Render ----------

def render_disagreement(dmap: DisagreementMap) -> str:
    lines = [
        f"claim {dmap.claim_id}: {', '.join(dmap.categories)}",
        f"  spread {dmap.spread:.2f} | source overlap {dmap.mean_source_overlap:.2f}",
    ]
    for aid, op in dmap.per_agent.items():
        tag = "believes" if aid in dmap.believers else (
            "disbelieves" if aid in dmap.disbelievers else (
                "abstains" if aid in dmap.abstainers else "undecided"))
        lines.append(f"  Agent{aid}: b={op.b:.2f} d={op.d:.2f} u={op.u:.2f}  {tag}")
    return "\n".join(lines)


def render_provenance(net: ClaimNetwork, claim_id: int) -> str:
    chain = net.provenance_chain(claim_id)
    lines = [f"provenance for claim {claim_id}: " + " -> ".join(str(c) for c in chain)]
    for cid in chain:
        claim = net.claims[cid]
        lines.append(f"  [{cid}] {claim.statement} ({claim.status.value})")
        for entry in claim.history:
            lines.append(f"      {entry}")
    return "\n".join(lines)


# ---------- Demo ----------

def build_demo_network(correlation_damping: float = 1.0) -> ClaimNetwork:
    """Four agents with asymmetric, non-reciprocal trust.

    Agent 4 trusts nobody but agent 1 — it will abstain where the others are
    confident, and that abstention is information about the source pool, not a
    deficiency to be corrected.
    """
    net = ClaimNetwork(correlation_damping=correlation_damping)
    trust = {
        1: {2: Opinion(0.8, 0.1, 0.1, 0.5), 3: Opinion(0.5, 0.2, 0.3, 0.5)},
        2: {1: Opinion(0.7, 0.1, 0.2, 0.5), 3: Opinion(0.6, 0.2, 0.2, 0.5)},
        3: {1: Opinion(0.4, 0.3, 0.3, 0.5), 2: Opinion(0.5, 0.3, 0.2, 0.5)},
        4: {1: Opinion(0.2, 0.5, 0.3, 0.5)},
    }
    for aid, t in trust.items():
        net.add_agent(Agent(aid, t))
    return net


def contested_scene() -> Tuple[ClaimNetwork, Claim]:
    """Two sources say opposite things; four observers trust them differently.

    Nothing about this is a tie to be broken. The pool splits because the
    observers weight the sources differently, and that split is the finding.
    """
    net = ClaimNetwork()
    net.add_agent(Agent(10, {1: Opinion(0.9, 0.05, 0.05, 0.5), 2: Opinion(0.1, 0.6, 0.3, 0.5)}))
    net.add_agent(Agent(11, {1: Opinion(0.1, 0.6, 0.3, 0.5), 2: Opinion(0.9, 0.05, 0.05, 0.5)}))
    net.add_agent(Agent(12, {1: Opinion(0.5, 0.2, 0.3, 0.5), 2: Opinion(0.5, 0.2, 0.3, 0.5)}))
    net.add_agent(Agent(13, {}))  # trusts nobody in this pool — abstains, loudly

    claim = Claim(id=1, statement="The slow-sand filter removes the pathogen")
    claim.add_evidence(Evidence(1, "field trial, 40 households, no cases", relevance=0.95))
    claim.add_evidence(Evidence(2, "lab assay finds pathogen post-filtration", relevance=0.05))
    net.add_claim(claim)
    return net, claim


def correlation_demo() -> str:
    """Same three agents, same single source, two prices for their agreement."""
    lines = []
    for damping, label in ((0.0, "damping 0.0 (naive independence)"), (1.0, "damping 1.0 (priced)")):
        net = ClaimNetwork(correlation_damping=damping)
        for aid in (10, 11, 12):
            net.add_agent(Agent(aid, {1: Opinion(0.8, 0.1, 0.1, 0.5)}))
        claim = Claim(id=1, statement="One source, three agents repeating it")
        claim.add_evidence(Evidence(1, "the single report everyone read", relevance=0.9))
        net.add_claim(claim)
        net.broadcast(1)
        status = net.consensus(1)
        op = net.claims[1].opinion
        lines.append(
            f"  {label}: b={op.b:.2f} d={op.d:.2f} u={op.u:.2f} -> {status.value}"
        )
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("SCENE 1 — iterated claims over an asymmetric trust pool")
    print("=" * 60)
    net = build_demo_network()
    smf = ProvenanceScientificFramework(net, seed=7)
    smf.iterate(max_iterations=5)
    print()
    for cid in sorted(net.claims):
        print(render_disagreement(net.disagreement_map(cid)))
    print()
    print(render_provenance(net, max(net.claims)))

    print()
    print("=" * 60)
    print("SCENE 2 — a split pool is reported as split")
    print("=" * 60)
    net2, claim2 = contested_scene()
    net2.broadcast(claim2.id)
    status = net2.consensus(claim2.id)
    print(f"status: {status.value}")
    print(render_disagreement(net2.disagreement_map(claim2.id)))

    print()
    print("=" * 60)
    print("SCENE 3 — echo is not evidence")
    print("=" * 60)
    print(correlation_demo())
    print("  the priced row is exactly one reading of the source, because that")
    print("  is exactly what three agents reading one source have.")


if __name__ == "__main__":
    main()
