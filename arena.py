import argparse
import json
import math
import os
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


class Agent:
    def __init__(self, name, is_hsp=False, trust_score=0.5, cost_ledger=None, memory_of_losses=None):
        self.name = name
        self.is_hsp = is_hsp
        self.trust_score = trust_score
        self.cost_ledger = cost_ledger if cost_ledger is not None else {}
        self.memory_of_losses = memory_of_losses if memory_of_losses is not None else {}

    def __repr__(self):
        return f"Agent {{ name: {self.name}, is_hsp: {self.is_hsp}, trust_score: {self.trust_score}, cost_ledger: {self.cost_ledger}, memory_of_losses: {self.memory_of_losses} }}"


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

    def load_scenario(self, scenario_path):
        with open(scenario_path) as f:
            content = f.read()
            # Strip non-JSON preamble/postamble if present
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            return json.loads(content[json_start:json_end])

    def run_scenario(self, scenario):
        print(f"\n=== Scenario: {scenario['title']} ===")
        print(f"Context: {scenario['context']}\n")

        for agent_key, agent_data in scenario["agents"].items():
            agent = next((a for a in self.agents if a.name == agent_key), None)
            if agent is None:
                agent = Agent(agent_key, is_hsp="hsp" in agent_key.lower())
                self.agents.append(agent)

            proposition = agent_data.get("claim") or agent_data.get("counter_claim", "")
            confidence = agent_data.get("confidence", 0.5)
            scope = scenario.get("parameters", {}).get("time_horizon", "unknown")

            claim = self.claim_declaration(agent, proposition, [scope], confidence)

            # Cross-agent attacks
            for other_key, other_data in scenario["agents"].items():
                if other_key == agent_key:
                    continue
                omissions = other_data.get("omissions", [])
                for omission in omissions:
                    self.attack_phase(agent, claim.id, "missing_variable", omission, 0.7)

            self.resolution_phase(claim.id, "pending", 0.0)
            self.trust_update(agent, 0.5, 0.1, 0.05)
            self.learning_lock_in(agent, claim.id, "pending")

        print("\n=== Arena cycle complete ===")
        for agent in self.agents:
            print(agent)

    def run_demo(self):
        agent1 = next((a for a in self.agents if not a.is_hsp), self.agents[0])
        agent2 = next((a for a in self.agents if a.is_hsp), self.agents[-1])

        claim = self.claim_declaration(agent1, "Reducing headcount by 10% increases profitability", ["Q3", "Q4"], 0.62)
        self.attack_phase(agent2, claim.id, "causal_break", "Attrition increases downstream failure rates", 0.74)
        self.defense_phase(agent1, claim.id, "refinement", "Limit reduction to non-core roles", -0.08)
        self.resolution_phase(claim.id, "partially_valid", 0.15)

        for agent in self.agents:
            self.trust_update(agent, 0.5, 0.1, 0.05)
            self.learning_lock_in(agent, claim.id, "partially_valid")


def main():
    parser = argparse.ArgumentParser(description="AI Argument Arena")
    parser.add_argument("--mode", choices=["adversarial", "demo"], default="demo",
                        help="Arena mode (default: demo)")
    parser.add_argument("--agents", nargs="+", default=["Linear_CEO", "Systemic_HSP"],
                        help="Agent names (default: Linear_CEO Systemic_HSP)")
    parser.add_argument("--scenario", type=str, default=None,
                        help="Path to scenario JSON file")
    args = parser.parse_args()

    agents = []
    for name in args.agents:
        name = name.strip().rstrip(",")
        is_hsp = "hsp" in name.lower()
        agents.append(Agent(name, is_hsp=is_hsp))

    arena = Arena(agents)

    if args.scenario:
        scenario = arena.load_scenario(args.scenario)
        arena.run_scenario(scenario)
    else:
        arena.run_demo()


if __name__ == "__main__":
    main()
