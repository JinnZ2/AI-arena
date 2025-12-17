import uuid

class Claim:
    def __init__(self, proposition, scope, confidence):
        self.id = str(uuid.uuid4())
        self.proposition = proposition
        self.scope = scope
        self.confidence = confidence

    def __repr__(self):
        return f"CLAIM {{ id: {self.id}, proposition: '{self.proposition}', scope: {self.scope}, confidence: {self.confidence} }}"

class Evidence:
    def __init__(self, claim_id, source, reliability, causal_link):
        self.claim_id = claim_id
        self.source = source
        self.reliability = reliability
        self.causal_link = causal_link

    def __repr__(self):
        return f"EVIDENCE {{ claim_id: {self.claim_id}, source: '{self.source}', reliability: {self.reliability}, causal_link: '{self.causal_link}' }}"

class Attack:
    def __init__(self, target_claim, mode, argument, confidence):
        self.target_claim = target_claim
        self.mode = mode
        self.argument = argument
        self.confidence = confidence

    def __repr__(self):
        return f"ATTACK {{ target_claim: {self.target_claim}, mode: '{self.mode}', argument: '{self.argument}', confidence: {self.confidence} }}"

class Defense:
    def __init__(self, claim_id, response_type, adjustment, confidence_update):
        self.claim_id = claim_id
        self.response_type = response_type
        self.adjustment = adjustment
        self.confidence_update = confidence_update

    def __repr__(self):
        return f"DEFENSE {{ claim_id: {self.claim_id}, response_type: '{self.response_type}', adjustment: '{self.adjustment}', confidence_update: {self.confidence_update} }}"

class Resolution:
    def __init__(self, claim_id, outcome, error_margin):
        self.claim_id = claim_id
        self.outcome = outcome
        self.error_margin = error_margin

    def __repr__(self):
        return f"RESOLUTION {{ claim_id: {self.claim_id}, outcome: '{self.outcome}', error_margin: {self.error_margin} }}"


class Arena:
    def __init__(self, agents):
        self.agents = agents
        self.claims = []
        self.evidence = []
        self.attacks = []
        self.defenses = []
        self.resolutions = []

    def claim_declaration(self, agent, proposition, scope, confidence):
        claim = Claim(proposition, scope, confidence)
        self.claims.append(claim)
        print(claim)
        return claim

    def attack_phase(self, agent, target_claim, mode, argument, confidence):
        attack = Attack(target_claim, mode, argument, confidence)
        self.attacks.append(attack)
        print(attack)
        return attack

    def defense_phase(self, agent, claim_id, response_type, adjustment, confidence_update):
        defense = Defense(claim_id, response_type, adjustment, confidence_update)
        self.defenses.append(defense)
        print(defense)
        return defense

    def resolution_phase(self, claim_id, outcome, error_margin):
        resolution = Resolution(claim_id, outcome, error_margin)
        self.resolutions.append(resolution)
        print(resolution)
        return resolution

    def trust_update(self, agent, impact, error, costly_honesty):
        agent.trust_score *= math.exp(-impact * error) + costly_honesty
        print(f"Trust update for {agent.name}: {agent.trust_score}")

    def learning_lock_in(self, agent, claim_id, outcome):
        agent.memory_of_losses[claim_id] = outcome
        print(f"Learning lock-in for {agent.name}: {agent.memory_of_losses}")

    def run_arena(self):
        for agent in self.agents:
            claim = self.claim_declaration(agent, "Reducing headcount by 10% increases profitability", ["Q3", "Q4"], 0.62)
            self.attack_phase(agent, claim.id, "causal_break", "Attrition increases downstream failure rates", 0.74)
            self.defense_phase(agent, claim.id, "refinement", "Limit reduction to non-core roles", -0.08)
            self.resolution_phase(claim.id, "partially_valid", 0.15)
            self.trust_update(agent, 0.5, 0.1, 0.05)
            self.learning_lock_in(agent, claim.id, "partially_valid")


import math

class Agent:
    def __init__(self, name, trust_score, cost_ledger, memory_of_losses):
        self.name = name
        self.trust_score = trust_score
        self.cost_ledger = cost_ledger
        self.memory_of_losses = memory_of_losses

    def __repr__(self):
        return f"Agent {{ name: {self.name}, trust_score: {self.trust_score}, cost_ledger: {self.cost_ledger}, memory_of_losses: {self.memory_of_losses} }}"

# Example agents
agent1 = Agent("Agent1", 0.8, {}, {})
agent2 = Agent("Agent2", 0.7, {}, {})

# Create the arena and run it
arena = Arena([agent1, agent2])
arena.run_arena()
