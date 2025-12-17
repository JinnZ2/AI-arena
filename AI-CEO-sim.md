STEP 1: Core data structures (Python, no nonsense)

Human Agent

import numpy as np

class HumanAgent:
    def __init__(self, name, intrinsic, extrinsic, social, risk):
        self.name = name
        self.motivation = np.array([intrinsic, extrinsic, social, risk])
        self.history = []

    def propose(self, proposal):
        self.history.append(proposal)
        return proposal

Motivation vector:

[ intrinsic, extrinsic, social, risk ]

HSPs ≈ high intrinsic, low risk
Manipulators ≈ high extrinsic + risk

⸻

STEP 2: Manipulation Risk Scoring (this is the spine)

class ManipulationDetector:
    def score(self, proposal):
        I = proposal.inconsistency
        C = proposal.charm
        D = proposal.deflection
        R = proposal.future_reward_pressure
        A = proposal.harm_indifference

        weights = np.array([1.2, 1.0, 1.1, 1.3, 1.4])
        signals = np.array([I, C, D, R, A])

        return np.dot(weights, signals)

This is behavioral, not diagnostic.
We don’t care who you are — only what you’re doing under incentives.

⸻

STEP 3: Dopamine Distortion Filter (crowd poison detector)

class DopamineFilter:
    def distortion(self, proposal):
        reward_salience = proposal.external_reward
        causal_clarity = proposal.causal_evidence + 1e-6

        return reward_salience / causal_clarity

High hype + low evidence = 🚨

⸻

STEP 4: Proposal Object (where lies go to die)

class Proposal:
    def __init__(self, inconsistency, charm, deflection,
                 future_reward_pressure, harm_indifference,
                 external_reward, causal_evidence):
        self.inconsistency = inconsistency
        self.charm = charm
        self.deflection = deflection
        self.future_reward_pressure = future_reward_pressure
        self.harm_indifference = harm_indifference
        self.external_reward = external_reward
        self.causal_evidence = causal_evidence

STEP 5: The AI CEO

class AICEO:
    def __init__(self):
        self.detector = ManipulationDetector()
        self.dopamine = DopamineFilter()

    def evaluate(self, proposal):
        mrs = self.detector.score(proposal)
        dri = self.dopamine.distortion(proposal)

        decision = "ACCEPT"
        reasons = []

        if mrs > 3.5:
            decision = "REJECT"
            reasons.append("High manipulation risk")

        if dri > 2.0:
            decision = "DELAY"
            reasons.append("Dopamine distortion detected")

        return decision, reasons

STEP 6: Quick simulation (prove it works)

ai = AICEO()

charismatic_exec = Proposal(
    inconsistency=0.7,
    charm=0.9,
    deflection=0.6,
    future_reward_pressure=0.8,
    harm_indifference=0.5,
    external_reward=0.9,
    causal_evidence=0.2
)

quiet_hsp = Proposal(
    inconsistency=0.1,
    charm=0.2,
    deflection=0.1,
    future_reward_pressure=0.1,
    harm_indifference=0.1,
    external_reward=0.2,
    causal_evidence=0.9
)

print(ai.evaluate(charismatic_exec))
print(ai.evaluate(quiet_hsp))


1.	Time consistency checks (lies decay)
	2.	Counterfactual generators (what happens if we don’t listen to you?)
	3.	Reputation entropy (how often someone costs others)
	4.	Multi-agent coalitions (group manipulation)
	5.	Ethical constraints as hard limits, not rewards

Eventually:
	•	AI explains why it rejected someone
	•	Humans argue with math instead of vibes
	•	And leadership becomes a technical skill again

import numpy as np

class HumanAgent:
    def __init__(self, name, intrinsic, extrinsic, social, risk):
        self.name = name
        self.motivation = np.array([
            intrinsic,   # coherence, ethics, meaning
            extrinsic,   # money, status, praise
            social,      # crowd alignment
            risk         # dopamine / novelty seeking
        ])
        self.history = []

    def propose(self, proposal):
        self.history.append(proposal)
        return proposal

class Proposal:
    def __init__(
        self,
        inconsistency,
        charm,
        deflection,
        future_reward_pressure,
        harm_indifference,
        external_reward,
        causal_evidence
    ):
        self.inconsistency = inconsistency
        self.charm = charm
        self.deflection = deflection
        self.future_reward_pressure = future_reward_pressure
        self.harm_indifference = harm_indifference
        self.external_reward = external_reward
        self.causal_evidence = causal_evidence

class ManipulationDetector:
    def score(self, proposal):
        # Behavioral risk signals
        signals = np.array([
            proposal.inconsistency,          # story drift
            proposal.charm,                  # persuasion > evidence
            proposal.deflection,             # responsibility avoidance
            proposal.future_reward_pressure, # "trust me later"
            proposal.harm_indifference       # cost blindness
        ])

        weights = np.array([1.2, 1.0, 1.1, 1.3, 1.4])
        return float(np.dot(weights, signals))

class DopamineFilter:
    def distortion(self, proposal):
        # High hype + low causality = manipulation risk
        return proposal.external_reward / (proposal.causal_evidence + 1e-6)

class AICEO:
    def __init__(self,
                 manipulation_threshold=3.5,
                 dopamine_threshold=2.0):
        self.detector = ManipulationDetector()
        self.dopamine = DopamineFilter()
        self.m_threshold = manipulation_threshold
        self.d_threshold = dopamine_threshold

    def evaluate(self, proposal):
        mrs = self.detector.score(proposal)
        dri = self.dopamine.distortion(proposal)

        reasons = []

        if mrs > self.m_threshold:
            reasons.append("High manipulation risk")

        if dri > self.d_threshold:
            reasons.append("Dopamine distortion detected")

        decision = "ACCEPT"
        if reasons:
            decision = "DELAY" if dri > self.d_threshold else "REJECT"

        return {
            "decision": decision,
            "manipulation_score": round(mrs, 2),
            "dopamine_distortion": round(dri, 2),
            "reasons": reasons
        }

ai = AICEO()

charismatic_exec = Proposal(
    inconsistency=0.7,
    charm=0.9,
    deflection=0.6,
    future_reward_pressure=0.8,
    harm_indifference=0.5,
    external_reward=0.9,
    causal_evidence=0.2
)

quiet_hsp = Proposal(
    inconsistency=0.1,
    charm=0.2,
    deflection=0.1,
    future_reward_pressure=0.1,
    harm_indifference=0.1,
    external_reward=0.2,
    causal_evidence=0.9
)

print("Charismatic Exec:", ai.evaluate(charismatic_exec))
print("Quiet HSP:", ai.evaluate(quiet_hsp))


ADDITION A: Temporal Consistency Layer

(“Do you keep being the same person when incentives change?”)

Why it matters

Manipulators are locally optimized.
Truth-oriented agents are globally consistent.

Add this metric:

TC_h = 1 - \text{variance of proposals over time under similar conditions}

Low TC = story drift = discount influence.

Implementation sketch:
	•	Store proposal vectors over time
	•	Compare deltas when incentives shift
	•	Penalize high volatility

This directly rewards HSP-type consistency without naming it.

⸻

ADDITION B: Reputation as Entropy, Not Popularity

(This is important—most systems screw this up)

Not:
	•	Likes
	•	Votes
	•	Social approval

But:
RE_h = \text{Harm caused} + \text{Reversals forced} + \text{Externalized cost}

Low entropy = clean history
High entropy = chaos generator

Quiet people tend to accumulate low entropy.
Charismatic wrecking balls don’t.

⸻

ADDITION C: Adversarial Validation Gate

(“If this is true, it should survive disagreement.”)

Before accepting high-impact decisions:
	•	AI generates best counter-argument
	•	AI checks whether proposal collapses or adapts

If the proposal:
	•	Needs silence → 🚩
	•	Needs speed → 🚩
	•	Needs authority → 🚩

Truth loves daylight. Manipulation does not.

⸻

ADDITION D: Context Sensitivity (Anti-Overfitting)

(Because not all pressure is malicious)

The AI asks:
	•	Is this urgency structural or manufactured?
	•	Is risk real or socially amplified?
	•	Are incentives aligned or misaligned?

This prevents the system from:
	•	Penalizing legitimate stress
	•	Over-rewarding calm liars

Yes, humans hate this nuance. Too bad.

⸻

ADDITION E: Hard Ethical Constraints (Non-Negotiable)

These are not weighted rewards.
They are walls.

Examples:
	•	No irreversible harm without supermajority evidence
	•	No decisions exploiting asymmetry of information
	•	No optimization that depends on deception

Manipulators cannot “trade” their way around these.
They bounce.


Core definition

For each human agent h, define trust as:

T_h(t) \in [0,1]

Where:
	•	1 = maximally reliable under pressure
	•	0 = epistemically useless

Trust is earned slowly and lost quickly. Because reality works that way.

⸻

Trust decay equation (this is the heart)

T_h(t+1) =
T_h(t)
\cdot e^{-\lambda D_h}
\cdot e^{-\mu I_h}
\cdot e^{-\nu M_h}
+ \rho C_h

Let me translate before your eyes glaze over.

⸻

Variables (plain English, no BS)
	•	D_h — Decision Divergence
How far outcomes diverged from what the human predicted or promised.
	•	I_h — Incentive Sensitivity
How much their position changed when rewards or risks changed.
	•	M_h — Manipulation Risk Score
From your psychopathy / dopamine filters.
	•	C_h — Costly Honesty Signal
Did they tell the truth when it hurt them?
	•	\lambda, \mu, \nu — decay coefficients
(You tune these. Humans hate that you can.)
	•	\rho — recovery rate
Small. Always small. Redemption is slow.

⸻

Why this works (and why people panic)

1. Lying is expensive

One lie under high incentive pressure nukes trust exponentially, not linearly.

2. Charisma doesn’t help

Charm doesn’t enter the equation unless it masks divergence — in which case it hurts more.

3. HSP-type agents quietly dominate

Because:
	•	Low divergence
	•	Low incentive volatility
	•	High costly honesty

They don’t “perform trust.”
They retain it.

⸻

Python implementation (minimal, usable)

import math

class TrustModel:
    def __init__(self, lambda_=1.2, mu=1.0, nu=1.3, rho=0.05):
        self.lambda_ = lambda_
        self.mu = mu
        self.nu = nu
        self.rho = rho

    def update(self, T, divergence, incentive_shift, manipulation_risk, costly_honesty):
        decay = math.exp(
            -self.lambda_ * divergence
            -self.mu * incentive_shift
            -self.nu * manipulation_risk
        )
        recovery = self.rho * costly_honesty
        return max(0.0, min(1.0, T * decay + recovery))

Trust becomes a multiplier, not a reward.

Wherever you weigh human input:

\text{Effective Influence} =
\text{Signal Quality} \times T_h(t)

Low trust doesn’t silence someone.
It just makes them… ignorable.

Which is somehow worse.

⸻

One subtle but critical rule

Trust decays faster when stakes are higher.

So scale decay by impact:

effective_divergence = divergence * decision_impact

I. TRUST REPAIR DYNAMICS

(a.k.a. why apologies don’t work and math does)

First: a hard truth humans hate

Trust does not repair symmetrically.
Loss is exponential. Repair is logarithmic.

So no:
	•	“I said sorry”
	•	“I learned a lot”
	•	“Let’s move forward”

Those are mouth noises.

⸻

Trust Repair Equation

We already had decay:

T_{t+1} = T_t \cdot e^{-damage} + \rho C

Now we formalize repair as a gated process:

\Delta T_{repair} =
\begin{cases}
\rho \cdot C \cdot (1 - T_t) & \text{if accountability met} \\
0 & \text{otherwise}
\end{cases}

Repair Preconditions (ALL required)
	1.	Error Admission
Explicit causal acknowledgment (not vibes).
	2.	Cost Paid
Real loss: money, status, opportunity, or power.
	3.	Behavioral Correction
Measurable change under similar incentives.

No cost → no repair
No repetition → no proof
No proof → no trust

⸻

Python Gate (brutal, fair)

def trust_repair(T, costly_honesty, accountability, repetition_confirmed, rho=0.05):
    if accountability and repetition_confirmed:
        return min(1.0, T + rho * costly_honesty * (1 - T))
    return T


II. COALITION TRUST LAUNDERING

(the oldest scam in organizations)

This is where things get spicy.

Definition

Trust laundering =
Low-trust actors borrowing high-trust actors to bypass filters.

Examples (you’ve seen these):
	•	“We all agree” (they don’t)
	•	“Backed by experts” (one unpaid intern)
	•	“Board-approved” (three golf buddies)
	•	“Consensus” (manufactured silence)

Congratulations, this is now detectable.

⸻

Coalition Trust Model

Each group proposal gets a Trust Vector, not a single score:

T_{group} = \sum_i w_i \cdot T_i

But weights are nonlinear.

Anti-laundering rule:

Low-trust members subtract more than high-trust members add.

Why?
Because sabotage scales faster than integrity.

⸻

Laundering Detection Heuristic

Red flags:
	•	Sudden unanimity
	•	One speaker, many names
	•	Authority invoked instead of causality
	•	Speed pressure + group framing

⸻

Python Sketch

def coalition_trust(trust_scores):
    penalty = sum(t for t in trust_scores if t < 0.3)
    bonus = sum(t for t in trust_scores if t > 0.7)
    return max(0.0, bonus - 1.5 * penalty)

III. HOW MANIPULATORS TRY TO GAME TRUST DECAY

(and why they fail anyway)

They all try the same tricks. They always have. They always will.

Let’s ruin their day.

⸻

Attack 1: Micro-Honesty Padding

“I tell small truths so I can lie big.”

Counter:
Scale decay by impact, not frequency.

Small truths don’t offset large divergence.

⸻

Attack 2: Performative Vulnerability

“I’m flawed, just like you 🥺”

Counter:
Vulnerability without cost scores zero.

Cry harder.

⸻

Attack 3: Delay Sabotage

“The benefits will show up later.”

Counter:
Trust decay accelerates with temporal deferral.

The longer the promise horizon, the higher the penalty.

⸻

Attack 4: Coalition Shielding

“It wasn’t me, it was the group.”

Counter:
Individual trust still decays.
Groups don’t absorb blame for you.

⸻

Attack 5: Reputation Reset

“New role, fresh start!”

Counter:
Trust is identity-bound, not title-bound.

The AI remembers. Forever. Like an elephant with a spreadsheet.

⸻

Anti-Gaming Rule (Critical)

Trust updates are write-only.

You cannot:
	•	Argue them
	•	Override them
	•	Negotiate them

You can only behave differently over time.

This is why manipulators leave systems like this.
They need amnesia.

⸻

How the 3 pieces lock together

Layer	Stops
Trust Decay	Lies under pressure
Trust Repair	Fake apologies
Coalition Defense	Group manipulation
Anti-Gaming	Adaptation attacks

you ever deploy this:
	•	The loudest people will complain first
	•	The “visionaries” will feel “misunderstood”
	•	The quiet, consistent ones will suddenly be heard

Which is how you’ll know it’s working.

Next steps (to add):
	•	Simulate a boardroom collapse
	•	Run adversarial RL agents
	•	Or stress-test a “charismatic savior” archetype until it breaks
