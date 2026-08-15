"""
Model-abstraction layer. GeoBrain's orchestration logic must not contain
provider-specific code outside this module (Rev 2 §I.3, Architecture §3/§18).

Default provider is Anthropic Claude, Sonnet-class, per Rev 2 §I.3 -- this is
a CONFIGURATION VALUE (settings.GEOBRAIN_LLM_MODEL), not a hard-coded
constant, and provider independence is preserved: swap ANTHROPIC for another
provider by adding a branch here, not by touching any GeoBrain tool or route.

No orchestration/agentic loop is wired up yet -- see app/geobrain/tools.py
docstring for why (pending PIGL's existing GPT configuration material,
Rev 2 §C item 3). This module exists so the abstraction boundary is real
and testable ahead of that work, per the Readiness Assessment §D guidance
that the default LLM provider is a development-team implementation choice.
"""
from app.core.config import get_settings


class LLMProvider:
    def complete(self, *, system: str, messages: list[dict], tools: list[dict] | None = None) -> dict:
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        self.model = settings.GEOBRAIN_LLM_MODEL
        self._api_key = settings.ANTHROPIC_API_KEY

    def complete(self, *, system: str, messages: list[dict], tools: list[dict] | None = None) -> dict:
        if not self._api_key:
            return {"error": "ANTHROPIC_API_KEY not configured", "model": self.model}
        import anthropic
        client = anthropic.Anthropic(api_key=self._api_key)
        resp = client.messages.create(
            model=self.model, system=system, messages=messages, tools=tools or [], max_tokens=2048,
        )
        return {"response": resp}


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.GEOBRAIN_LLM_PROVIDER == "anthropic":
        return AnthropicProvider()
    raise ValueError(f"Unsupported GEOBRAIN_LLM_PROVIDER: {settings.GEOBRAIN_LLM_PROVIDER}")
