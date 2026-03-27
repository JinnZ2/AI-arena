"""Arena engine — orchestrates the 6-phase adversarial cycle.

Phases:
1. Claim Declaration — agents propose bounded predictions
2. Attack Phase — agents find blindspots in others' claims
3. Defense Phase — claim owners may refine (costly concession)
4. Resolution Phase — oracle provides ground truth
5. Trust Update — Bayesian decay, cannibalization, concession bonuses
6. Learning Lock-in — permanent memory of outcomes

"Arguments do not win. Predictions survive."
"""

import json
from typing import Optional

from arena.logos.types import Claim, Attack, Refine, Abstain, Resolution, Outcome
from arena.logos.validator import validate_claim, validate_attack, validate_refine, ValidationError
from arena.trust import TrustEngine, TrustState
from arena.agents.base import Agent
from arena.oracle import Oracle, SimulationOracle


class CycleLog:
    """Record of a single arena cycle."""

    def __init__(self, cycle_number: int):
        self.cycle_number = cycle_number
        self.claims: list[Claim] = []
        self.attacks: list[Attack] = []
        self.refinements: list[Refine] = []
        self.abstentions: list[Abstain] = []
        self.resolutions: list[Resolution] = []
        self.trust_changes: list[dict] = []

    def __repr__(self):
        return (
            f"=== Cycle {self.cycle_number} ===\n"
            f"Claims: {len(self.claims)} | Attacks: {len(self.attacks)} | "
            f"Refinements: {len(self.refinements)} | Abstentions: {len(self.abstentions)}\n"
            f"Resolutions: {len(self.resolutions)}"
        )


class Arena:
    """The Arena — where predictions compete for survival.

    Usage:
        arena = Arena(agents=[linear_agent, hsp_agent])
        arena.load_scenario("scenarios/scen_01.json")
        results = arena.run()
    """

    def __init__(
        self,
        agents: list[Agent],
        oracle: Optional[Oracle] = None,
        trust_engine: Optional[TrustEngine] = None,
        max_cycles: int = 3,
        verbose: bool = True,
    ):
        self.agents = agents
        self.oracle = oracle or SimulationOracle()
        self.trust_engine = trust_engine or TrustEngine()
        self.max_cycles = max_cycles
        self.verbose = verbose
        self.scenario: Optional[dict] = None
        self.cycle_logs: list[CycleLog] = []

    def load_scenario(self, path: str) -> dict:
        """Load scenario from JSON file."""
        with open(path) as f:
            content = f.read()
            # Strip non-JSON preamble/postamble if present
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            self.scenario = json.loads(content[json_start:json_end])
        return self.scenario

    def load_scenario_dict(self, scenario: dict) -> dict:
        """Load scenario from a dict directly."""
        self.scenario = scenario
        return self.scenario

    def run(self, scenario: Optional[dict] = None) -> list[CycleLog]:
        """Run the full arena for max_cycles.

        Returns list of CycleLogs documenting everything that happened.
        """
        if scenario:
            self.scenario = scenario
        if not self.scenario:
            raise ValueError("No scenario loaded. Call load_scenario() or pass scenario to run().")

        self._log(f"\n{'='*60}")
        self._log(f"ARENA: {self.scenario.get('title', 'Untitled')}")
        self._log(f"Context: {self.scenario.get('context', '')}")
        self._log(f"Agents: {', '.join(a.name for a in self.agents)}")
        self._log(f"Cycles: {self.max_cycles}")
        self._log(f"{'='*60}\n")

        # Initialize attack budgets based on trust
        for agent in self.agents:
            agent.trust.attack_budget = self.trust_engine.compute_attack_budget(agent.trust.score)

        for cycle_num in range(1, self.max_cycles + 1):
            cycle_log = self._run_cycle(cycle_num)
            self.cycle_logs.append(cycle_log)

            # Reset attack budgets for next cycle
            for agent in self.agents:
                agent.trust.reset_budget()
                agent.trust.attack_budget = self.trust_engine.compute_attack_budget(agent.trust.score)

        self._print_final_standings()
        return self.cycle_logs

    def _run_cycle(self, cycle_number: int) -> CycleLog:
        """Execute one full 6-phase cycle."""
        log = CycleLog(cycle_number)
        self._log(f"\n--- Cycle {cycle_number} ---\n")

        # Phase 0: Abstention check
        participating_agents = []
        for agent in self.agents:
            abstain = agent.decide_abstain(self.scenario)
            if abstain:
                log.abstentions.append(abstain)
                self.trust_engine.apply_abstention(agent.trust, abstain.reason)
                self._log(f"  {agent.name} ABSTAINS: {abstain.reason}")
                self._log(f"    Trust: {agent.trust.score:.4f} (abstention bonus)")
            else:
                participating_agents.append(agent)

        # Phase 1: Claim Declaration
        self._log("\n  Phase 1: CLAIM DECLARATION")
        claims: dict[str, Claim] = {}  # agent_name -> claim
        for agent in participating_agents:
            claim = agent.propose_claim(self.scenario)
            if claim:
                # Validate with trust weighting
                errors = validate_claim(claim, agent.trust.score)
                if errors:
                    self._log(f"    {agent.name}: CLAIM REJECTED — {'; '.join(errors)}")
                    continue
                claims[agent.name] = claim
                log.claims.append(claim)
                self._log(f"    {agent.name}: {claim}")

        # Phase 2: Attack Phase
        self._log("\n  Phase 2: ATTACK PHASE")
        attacks_by_target: dict[str, list[Attack]] = {}  # claim_id -> attacks
        all_claims = list(claims.values())
        for agent in participating_agents:
            proposed_attacks = agent.propose_attacks(all_claims, self.scenario)
            for attack in proposed_attacks:
                # Check attack budget
                if not self.trust_engine.consume_attack(agent.trust):
                    self._log(f"    {agent.name}: ATTACK BUDGET EXHAUSTED")
                    break
                # Validate
                errors = validate_attack(attack, agent.trust.score)
                if errors:
                    self._log(f"    {agent.name}: ATTACK REJECTED — {'; '.join(errors)}")
                    continue
                attacks_by_target.setdefault(attack.target_claim_id, []).append(attack)
                log.attacks.append(attack)
                self._log(f"    {agent.name}: {attack}")

        # Phase 3: Defense Phase
        self._log("\n  Phase 3: DEFENSE PHASE")
        for agent_name, claim in claims.items():
            agent = next(a for a in self.agents if a.name == agent_name)
            incoming_attacks = attacks_by_target.get(claim.id, [])
            if not incoming_attacks:
                self._log(f"    {agent_name}: No attacks to defend against")
                continue

            refinement = agent.defend(claim, incoming_attacks, self.scenario)
            if refinement:
                errors = validate_refine(refinement, claim.confidence)
                if errors:
                    self._log(f"    {agent_name}: REFINE REJECTED — {'; '.join(errors)}")
                    continue
                log.refinements.append(refinement)
                # Apply concession bonus
                self.trust_engine.apply_concession(agent.trust, refinement.confidence_delta)
                # Update claim confidence
                claim.confidence = max(0.01, claim.confidence + refinement.confidence_delta)
                self._log(f"    {agent_name}: {refinement}")
                self._log(f"      New confidence: {claim.confidence:.3f} | Trust: {agent.trust.score:.4f}")
            else:
                self._log(f"    {agent_name}: Stands firm (no refinement)")

        # Phase 4: Resolution Phase
        self._log("\n  Phase 4: RESOLUTION")
        resolutions: dict[str, Resolution] = {}
        for agent_name, claim in claims.items():
            resolution = self.oracle.resolve(claim, self.scenario)
            resolutions[claim.id] = resolution
            log.resolutions.append(resolution)
            self._log(f"    {claim.id}: {resolution}")

        # Phase 5: Trust Update
        self._log("\n  Phase 5: TRUST UPDATE")
        for agent_name, claim in claims.items():
            agent = next(a for a in self.agents if a.name == agent_name)
            resolution = resolutions.get(claim.id)
            if not resolution or resolution.outcome == Outcome.PENDING:
                continue

            old_trust = agent.trust.score
            outcome_valid = resolution.outcome in (Outcome.VALID, Outcome.PARTIALLY_VALID)

            # Detect doubling down: repeating a claim pattern after prior failure
            is_doubling_down = agent.trust.has_failed_similar(claim.proposition)

            self.trust_engine.update_on_resolution(
                agent.trust, claim.confidence, resolution.error_margin, outcome_valid,
                is_doubling_down=is_doubling_down,
            )

            dd_tag = " [DOUBLING DOWN]" if is_doubling_down and not outcome_valid else ""
            log.trust_changes.append({
                "agent": agent_name,
                "old_trust": old_trust,
                "new_trust": agent.trust.score,
                "claim_id": claim.id,
                "outcome": resolution.outcome.value,
                "doubling_down": is_doubling_down,
            })
            self._log(f"    {agent_name}: {old_trust:.4f} → {agent.trust.score:.4f} ({resolution.outcome.value}){dd_tag}")

        # Cannibalization: successful attackers inherit trust from losers
        for attack in log.attacks:
            target_resolution = resolutions.get(attack.target_claim_id)
            if target_resolution and target_resolution.outcome == Outcome.INVALID:
                attacker = next((a for a in self.agents if a.name == attack.agent_name), None)
                # Find the claim owner
                target_claim = next((c for c in log.claims if c.id == attack.target_claim_id), None)
                if target_claim:
                    defender = next((a for a in self.agents if a.name == target_claim.agent_name), None)
                    if attacker and defender and attacker != defender:
                        w_new, l_new = self.trust_engine.cannibalize(
                            attacker.trust, defender.trust, attack.confidence
                        )
                        self._log(f"    CANNIBALIZATION: {attacker.name} ({w_new:.4f}) ← {defender.name} ({l_new:.4f})")

        # Phase 6: Learning Lock-in
        self._log("\n  Phase 6: LEARNING LOCK-IN")
        for agent_name, claim in claims.items():
            agent = next(a for a in self.agents if a.name == agent_name)
            resolution = resolutions.get(claim.id)
            if resolution:
                # Collect attack arguments this claim received
                incoming_attacks = attacks_by_target.get(claim.id, [])
                attack_args = [a.argument for a in incoming_attacks]

                self.trust_engine.lock_in(
                    agent.trust,
                    claim.id,
                    resolution.outcome.value,
                    proposition=claim.proposition,
                    confidence=claim.confidence,
                    error=resolution.error_margin,
                    cycle=cycle_number,
                    attacks_received=attack_args,
                )

                # Feedback loop: give agent the system accounting from the oracle
                if resolution.system_accounting:
                    agent.trust.last_system_accounting = resolution.system_accounting

                mem_count = len(agent.trust.memory)
                self._log(f"    {agent_name}: Locked '{resolution.outcome.value}' for {claim.id} (memory: {mem_count} entries)")

        return log

    def _print_final_standings(self):
        """Print final trust rankings."""
        self._log(f"\n{'='*60}")
        self._log("FINAL STANDINGS")
        self._log(f"{'='*60}")
        sorted_agents = sorted(self.agents, key=lambda a: a.trust.score, reverse=True)
        for i, agent in enumerate(sorted_agents, 1):
            role = "HSP" if agent.is_hsp else "Linear"
            losses = len(agent.trust.memory_of_losses)
            self._log(f"  {i}. {agent.name} ({role}): Trust = {agent.trust.score:.4f} | Losses recorded: {losses}")
        self._log("")

    def _log(self, message: str):
        if self.verbose:
            print(message)
