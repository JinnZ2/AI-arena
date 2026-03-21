"""Claude-powered agent for the AI Arena.

Uses the Anthropic API to power autonomous LOGOS-speaking agents.
Requires `pip install anthropic` and ANTHROPIC_API_KEY env var.

Usage:
    from arena.agents.claude_agent import ClaudeAgent

    agent = ClaudeAgent("Strategic_HSP", is_hsp=True)
    # or with a specific model:
    agent = ClaudeAgent("Linear_Optimizer", model="claude-haiku-4-5-20251001")
"""

import os
from arena.agents.llm import LLMAgent


class ClaudeAgent(LLMAgent):
    """Agent powered by the Claude API via the Anthropic SDK.

    Supports all Claude models. Defaults to claude-sonnet-4-20250514 for
    a balance of speed and reasoning quality.
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        name: str,
        is_hsp: bool = False,
        model: str = None,
        api_key: str = None,
        max_tokens: int = 1024,
    ):
        super().__init__(name, is_hsp=is_hsp)
        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "ClaudeAgent requires the anthropic package. "
                    "Install it with: pip install anthropic"
                )
            if not self._api_key:
                raise ValueError(
                    "ClaudeAgent requires an API key. Set ANTHROPIC_API_KEY "
                    "environment variable or pass api_key to constructor."
                )
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _call_llm(self, prompt: str) -> str:
        """Call Claude API and return the response text."""
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
