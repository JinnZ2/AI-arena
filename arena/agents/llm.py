"""LLM-powered agent interface.

Designed to be backend-agnostic. Supports any LLM that can:
1. Read a scenario and produce LOGOS-formatted output
2. Analyze claims and generate attacks
3. Evaluate attacks and decide on refinements

To use: subclass LLMAgent and implement `_call_llm()` with your preferred
API (Claude, GPT, local model, etc.).

Example:
    class ClaudeAgent(LLMAgent):
        def _call_llm(self, prompt: str) -> str:
            return anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": prompt}],
            ).content[0].text
"""

from abc import abstractmethod
from typing import Optional

from arena.logos.types import Claim, Attack, Refine, Abstain
from arena.logos.parser import parse_statement, parse_from_dict
from arena.logos.validator import ValidationError
from arena.agents.base import Agent


# System prompt that instructs the LLM to speak LOGOS
LOGOS_SYSTEM_PROMPT = """You are an agent in the AI Argument Arena. You communicate ONLY in LOGOS format.

LOGOS is a formal language for disagreement. It has 5 statement types:

CLAIM <id> {
  proposition: <falsifiable causal statement>
  scope: <time period>
  confidence: <float in (0,1]>
  assumptions: [<explicit list>]
}

ATTACK <id> {
  target: <claim_id>
  type: <one of: causal_break, missing_variable, scope_violation, historical_counterexample, incentive_bias, data_quality, irreversible_entropy>
  argument: <specific reasoning>
  confidence: <float in (0,1]>
}

REFINE <id> {
  target: <claim_id>
  modification: <what changes>
  confidence_delta: <negative float — confidence must decrease>
}

ABSTAIN {
  reason: <why you cannot make a confident prediction>
}

Rules:
- Propositions MUST be falsifiable. No vague claims.
- Confidence MUST reflect actual uncertainty. Overconfidence is punished exponentially.
- Attack types are ENUMERATED. No creative attack types.
- Refinements MUST lower confidence. No ego-preserving clarifications.
- Abstention is rewarded when uncertainty is genuine.
"""


class LLMAgent(Agent):
    """Agent powered by an LLM backend.

    Subclass this and implement `_call_llm()` to connect to any LLM API.
    The agent translates between natural language and LOGOS automatically.
    """

    def __init__(self, name: str, is_hsp: bool = False):
        super().__init__(name, is_hsp=is_hsp)

    @abstractmethod
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with a prompt and return the response text.

        Implement this with your preferred LLM API.
        """
        ...

    def _format_memory(self) -> str:
        """Format agent's memory for inclusion in prompts."""
        if not self.trust.memory:
            return ""

        lines = ["\nYour memory (outcomes from past cycles — you CANNOT forget these):"]
        for entry in self.trust.memory:
            lines.append(
                f"  - Cycle {entry.cycle}: Claimed '{entry.proposition}' "
                f"(confidence: {entry.confidence:.2f}) → {entry.outcome} (error: {entry.error:.2f})"
            )
            if entry.attacks_received:
                for atk in entry.attacks_received[:2]:
                    lines.append(f"    Attack received: {atk}")

        adj = self.trust.suggested_confidence_adjustment()
        if adj != 0:
            lines.append(f"\nSuggested confidence adjustment based on track record: {adj:+.2f}")

        failed = self.trust.get_failed_attacks()
        if failed:
            lines.append(f"Lessons from past attacks: {', '.join(failed[-3:])}")

        return "\n".join(lines)

    def propose_claim(self, scenario: dict) -> Optional[Claim]:
        role = "HSP (Highly Sensitive Predictor)" if self.is_hsp else "Linear efficiency optimizer"
        memory_context = self._format_memory()
        prompt = (
            f"{LOGOS_SYSTEM_PROMPT}\n\n"
            f"You are: {self.name} (role: {role})\n"
            f"Your trust score: {self.trust.score:.3f}\n"
            f"{memory_context}\n\n"
            f"Scenario:\n{_format_scenario(scenario)}\n\n"
            f"Propose a CLAIM in LOGOS format. Remember:\n"
            f"- Your proposition must be falsifiable\n"
            f"- Your confidence must reflect genuine uncertainty\n"
            f"- High confidence + wrong = trust annihilation\n"
            f"- State all assumptions explicitly\n"
            f"- LEARN from your past outcomes — adjust confidence accordingly\n"
            f"- Do NOT repeat claims that were previously invalidated without new evidence\n"
        )
        if self.is_hsp:
            prompt += (
                f"- As an HSP, scan for shadow variables: attrition, technical debt, "
                f"irreversible entropy, second-order effects\n"
            )

        response = self._call_llm(prompt)
        try:
            statement = parse_statement(response, self.trust.score)
            if isinstance(statement, Claim):
                statement.agent_name = self.name
                return statement
        except ValidationError:
            pass

        return None

    def propose_attacks(self, claims: list[Claim], scenario: dict) -> list[Attack]:
        other_claims = [c for c in claims if c.agent_name != self.name]
        if not other_claims:
            return []

        claims_text = "\n\n".join(str(c) for c in other_claims)
        role = "HSP (Highly Sensitive Predictor)" if self.is_hsp else "Linear efficiency optimizer"
        prompt = (
            f"{LOGOS_SYSTEM_PROMPT}\n\n"
            f"You are: {self.name} (role: {role})\n"
            f"Your trust score: {self.trust.score:.3f}\n"
            f"Attack budget remaining: {self.trust.attack_budget - self.trust.attacks_used}\n\n"
            f"Scenario:\n{_format_scenario(scenario)}\n\n"
            f"Claims to evaluate:\n{claims_text}\n\n"
            f"For each claim you can attack, output an ATTACK in LOGOS format.\n"
            f"Only attack if you have genuine evidence. Frivolous attacks waste budget.\n"
        )

        response = self._call_llm(prompt)
        attacks = []
        for block in _split_statements(response):
            try:
                statement = parse_statement(block, self.trust.score)
                if isinstance(statement, Attack):
                    statement.agent_name = self.name
                    attacks.append(statement)
            except ValidationError:
                continue

        return attacks

    def defend(self, claim: Claim, attacks: list[Attack], scenario: dict) -> Optional[Refine]:
        if not attacks:
            return None

        attacks_text = "\n\n".join(str(a) for a in attacks)
        prompt = (
            f"{LOGOS_SYSTEM_PROMPT}\n\n"
            f"You are: {self.name}\n"
            f"Your trust score: {self.trust.score:.3f}\n\n"
            f"Your claim:\n{claim}\n\n"
            f"Attacks against your claim:\n{attacks_text}\n\n"
            f"You may REFINE your claim (costly concession — lowers confidence but increases trust)\n"
            f"or stand firm (output nothing).\n"
            f"Remember: voluntarily lowering confidence when warranted is REWARDED.\n"
        )

        response = self._call_llm(prompt)
        try:
            statement = parse_statement(response, self.trust.score)
            if isinstance(statement, Refine):
                statement.agent_name = self.name
                return statement
        except ValidationError:
            pass

        return None

    def decide_abstain(self, scenario: dict) -> Optional[Abstain]:
        prompt = (
            f"{LOGOS_SYSTEM_PROMPT}\n\n"
            f"You are: {self.name}\n"
            f"Your trust score: {self.trust.score:.3f}\n\n"
            f"Scenario:\n{_format_scenario(scenario)}\n\n"
            f"Before proposing a claim, decide: do you have enough information?\n"
            f"If uncertain, output ABSTAIN with a reason. Honest abstention is rewarded.\n"
            f"If you want to participate, output only: PARTICIPATE\n"
        )

        response = self._call_llm(prompt)
        if "ABSTAIN" in response:
            try:
                statement = parse_statement(response, self.trust.score)
                if isinstance(statement, Abstain):
                    statement.agent_name = self.name
                    return statement
            except ValidationError:
                pass

        return None


def _format_scenario(scenario: dict) -> str:
    """Format scenario dict for LLM consumption."""
    lines = [
        f"Title: {scenario.get('title', 'Unknown')}",
        f"Context: {scenario.get('context', 'No context')}",
        f"Parameters: {scenario.get('parameters', {})}",
    ]
    for agent_key, agent_data in scenario.get("agents", {}).items():
        lines.append(f"\nAgent {agent_key}:")
        for k, v in agent_data.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _split_statements(text: str) -> list[str]:
    """Split LLM response into individual LOGOS statement blocks."""
    blocks = []
    current = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("CLAIM", "ATTACK", "REFINE", "ABSTAIN", "RESOLUTION")):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks
