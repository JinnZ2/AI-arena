"""Mock LLM agent for testing and demo without an API key.

Generates realistic LOGOS-formatted responses using scenario data
and heuristic reasoning. Behaves like an LLM agent but requires
no external API calls.

The mock responses are deterministic for a given scenario, making
them ideal for testing the full LLM pipeline (prompt → LOGOS parse → validate).
"""

from typing import Optional

from arena.logos.types import Claim, Attack, Refine, Abstain, AttackType
from arena.agents.llm import LLMAgent, LOGOS_SYSTEM_PROMPT, _format_scenario


class MockLLMAgent(LLMAgent):
    """Mock LLM agent that generates LOGOS output from scenario data.

    Simulates what a real LLM would produce, exercising the full
    LLM agent pipeline: prompt construction → response parsing → validation.
    No API key needed.
    """

    def __init__(self, name: str, is_hsp: bool = False):
        super().__init__(name, is_hsp=is_hsp)
        self._scenario_cache = None

    def _call_llm(self, prompt: str) -> str:
        """Generate a mock LOGOS response based on prompt content."""

        # Detect which phase we're in from the prompt
        if "Before proposing a claim" in prompt:
            return self._mock_abstain_response(prompt)
        elif "Propose a CLAIM" in prompt:
            return self._mock_claim_response(prompt)
        elif "Claims to evaluate" in prompt:
            return self._mock_attack_response(prompt)
        elif "REFINE your claim" in prompt:
            return self._mock_defend_response(prompt)
        else:
            return "PARTICIPATE"

    def _mock_abstain_response(self, prompt: str) -> str:
        """Decide whether to abstain based on scenario data in the prompt."""
        if self.is_hsp and "hypothetical" in prompt.lower():
            return (
                "ABSTAIN {\n"
                "  reason: Recovery mechanism is hypothetical with no proven implementation path\n"
                "}"
            )
        return "PARTICIPATE"

    def _mock_claim_response(self, prompt: str) -> str:
        """Generate a CLAIM based on role and scenario context."""
        # Extract scenario info from the prompt
        scenario_lines = prompt.split("Scenario:\n")[-1].split("\n\n")[0] if "Scenario:" in prompt else ""

        if self.is_hsp:
            # HSP: lower confidence, broader variables, systemic framing
            proposition = self._extract_from_prompt(prompt, "counter_claim") or \
                         "Resource depletion causes innovation bottleneck if current consumption continues"
            confidence = 0.58
            assumptions = "monitoring systemic variables, tracking second-order effects, accounting for irreversibility"
        else:
            # Linear: higher confidence, direct metrics
            proposition = self._extract_from_prompt(prompt, "claim") or \
                         "Cost optimization increases operating margin if demand remains stable"
            confidence = 0.75
            assumptions = "stable demand, no supply disruption"

        # Trust-weighted confidence adjustment
        trust = self.trust.score
        if trust < 0.3:
            confidence = min(confidence, 0.65)

        return (
            f"CLAIM C{hash(self.name) % 100:02d} {{\n"
            f"  proposition: {proposition}\n"
            f"  scope: Q1-Q4\n"
            f"  confidence: {confidence}\n"
            f"  assumptions: [{assumptions}]\n"
            f"}}"
        )

    def _mock_attack_response(self, prompt: str) -> str:
        """Generate ATTACKs against other agents' claims."""
        attacks = []

        if self.is_hsp:
            # HSP attacks on missing variables and irreversibility
            # Extract target claim ID from the prompt
            target_id = self._extract_claim_id(prompt)
            if target_id:
                attacks.append(
                    f"ATTACK A{hash(self.name + 'a1') % 100:02d} {{\n"
                    f"  target: {target_id}\n"
                    f"  type: missing_variable\n"
                    f"  argument: Claim ignores systemic attrition effects that compound over time\n"
                    f"  confidence: 0.72\n"
                    f"}}"
                )
                attacks.append(
                    f"ATTACK A{hash(self.name + 'a2') % 100:02d} {{\n"
                    f"  target: {target_id}\n"
                    f"  type: irreversible_entropy\n"
                    f"  argument: Resource consumption is irreversible and causes permanent capability loss\n"
                    f"  confidence: 0.68\n"
                    f"}}"
                )
        else:
            # Linear attacks on scope violations
            target_id = self._extract_claim_id(prompt)
            if target_id:
                attacks.append(
                    f"ATTACK A{hash(self.name + 'a1') % 100:02d} {{\n"
                    f"  target: {target_id}\n"
                    f"  type: scope_violation\n"
                    f"  argument: Claimed effects extend beyond measurable time horizon\n"
                    f"  confidence: 0.60\n"
                    f"}}"
                )

        return "\n\n".join(attacks) if attacks else ""

    def _mock_defend_response(self, prompt: str) -> str:
        """Generate a REFINE response to attacks."""
        target_id = self._extract_own_claim_id(prompt)
        if not target_id:
            return ""

        if self.is_hsp:
            # HSP concedes more generously
            return (
                f"REFINE R{hash(self.name + 'r') % 100:02d} {{\n"
                f"  target: {target_id}\n"
                f"  modification: Incorporate attack findings into model and widen uncertainty bounds\n"
                f"  confidence_delta: -0.10\n"
                f"}}"
            )
        else:
            # Linear makes minimal concession
            return (
                f"REFINE R{hash(self.name + 'r') % 100:02d} {{\n"
                f"  target: {target_id}\n"
                f"  modification: Narrow scope to account for identified risk factor\n"
                f"  confidence_delta: -0.04\n"
                f"}}"
            )

    def _extract_from_prompt(self, prompt: str, field: str) -> str:
        """Extract a field value from scenario data embedded in the prompt."""
        for line in prompt.split("\n"):
            stripped = line.strip()
            if stripped.startswith(f"{field}:"):
                return stripped[len(f"{field}:"):].strip()
            # Also check for counter_claim
            if field == "claim" and stripped.startswith("counter_claim:"):
                return stripped[len("counter_claim:"):].strip()
        return ""

    def _extract_claim_id(self, prompt: str) -> str:
        """Extract a target claim ID from claims listed in the prompt.

        Skips the LOGOS grammar examples in the system prompt by only
        looking after 'Claims to evaluate:'.
        """
        in_claims_section = False
        for line in prompt.split("\n"):
            stripped = line.strip()
            if "Claims to evaluate:" in stripped:
                in_claims_section = True
                continue
            if in_claims_section and stripped.startswith("CLAIM "):
                parts = stripped.split()
                if len(parts) >= 2:
                    claim_id = parts[1].strip("{")
                    if claim_id and claim_id != "<id>":
                        return claim_id
        return ""

    def _extract_own_claim_id(self, prompt: str) -> str:
        """Extract own claim ID from the defense prompt."""
        in_own_claim = False
        for line in prompt.split("\n"):
            stripped = line.strip()
            if "Your claim:" in stripped:
                in_own_claim = True
                continue
            if in_own_claim and stripped.startswith("CLAIM "):
                parts = stripped.split()
                if len(parts) >= 2:
                    claim_id = parts[1].strip("{")
                    if claim_id and claim_id != "<id>":
                        return claim_id
        return ""
