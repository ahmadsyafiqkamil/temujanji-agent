"""Shared LLM construction for the router and domain sub-agents."""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm


def build_model() -> str | LiteLlm:
    """Prefer TokenRouter (OpenAI-compatible) when configured; else Gemini."""
    api_base = os.environ.get("TOKENROUTER_BASE_URL", "").strip()
    api_key = os.environ.get("TOKENROUTER_API_KEY", "").strip()
    model_name = os.environ.get(
        "TOKENROUTER_MODEL", "moonshotai/kimi-k3-free"
    ).strip()
    if api_base and api_key:
        return LiteLlm(
            model=f"openai/{model_name}",
            api_base=api_base,
            api_key=api_key,
            drop_params=True,
            timeout=180,
        )
    return os.environ.get("ADK_MODEL", "gemini-2.5-flash")
