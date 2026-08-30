"""
VARUNA — Unified LLM Cognitive Gateway
Routes prompt completions and embeddings through Google Gemini or OpenRouter based on configuration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.config import settings
from src.llm import gemini_client, openrouter_client

log = logging.getLogger("varuna.llm.gateway")


def get_active_provider() -> str:
    provider = getattr(settings, "llm_provider", "").lower().strip()
    if provider:
        return provider
    if getattr(settings, "gemini_api_key", "") or getattr(settings, "gemini_api_keys_pool", ""):
        return "gemini"
    if getattr(settings, "openrouter_api_key", "") or getattr(settings, "openrouter_api_keys_pool", ""):
        return "openrouter"
    return "gemini"


async def chat_complete(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    task_tag: str = "general",
    trace: Optional[Any] = None,
) -> str:
    """
    Dispatches chat completion request to the active provider (Gemini or OpenRouter).
    """
    provider = get_active_provider()
    if provider == "gemini":
        return await gemini_client.chat_complete(
            messages=messages,
            model=model or getattr(settings, "gemini_model", "gemini-2.0-flash"),
            temperature=temperature,
            max_tokens=max_tokens,
            task_tag=task_tag,
            trace=trace,
        )
    else:
        return await openrouter_client.chat_complete(
            messages=messages,
            model=model or getattr(settings, "openrouter_model", "google/gemini-2.5-flash"),
            temperature=temperature,
            max_tokens=max_tokens,
            task_tag=task_tag,
            trace=trace,
        )


async def embed_texts(
    texts: List[str],
    model: Optional[str] = None,
) -> List[List[float]]:
    """
    Dispatches dense embedding generation to active provider.
    """
    provider = get_active_provider()
    if provider == "gemini":
        return await gemini_client.embed_texts(texts, model=model)
    else:
        return await openrouter_client.embed_texts(texts, model=model)
