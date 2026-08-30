"""
VARUNA — Google Gemini Native Async Client
Direct cloud cognitive engine powered by Google Gemini API (gemini-2.0-flash / gemini-1.5-flash).
Features zero-friction REST calls, multi-key rotation on rate-limits, and robust token usage tracking.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings

log = logging.getLogger("varuna.gemini")

DEFAULT_MODEL = settings.gemini_model if hasattr(settings, "gemini_model") else "gemini-2.0-flash"
DEFAULT_EMBED_MODEL = settings.gemini_embed_model if hasattr(settings, "gemini_embed_model") else "text-embedding-004"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _get_key_pool() -> List[str]:
    """Retrieve all available Gemini API keys from single config or multi-line/comma-separated pool."""
    keys: List[str] = []
    pool_str = getattr(settings, "gemini_api_keys_pool", "") or ""
    if pool_str:
        # Split by comma or newline
        for raw_line in pool_str.replace("\r\n", "\n").replace(",", "\n").split("\n"):
            line = raw_line.strip()
            # Strip comments and assignments
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                line = line.split("=", 1)[1].strip()
            line = line.strip(" '\"\t")
            if line and line not in keys:
                keys.append(line)

    single_key = (getattr(settings, "gemini_api_key", "") or "").strip(" '\"\t")
    if single_key and single_key not in keys and not single_key.startswith("#"):
        keys.append(single_key)
    return keys


_active_key_idx = 0


def _convert_messages_to_gemini_format(messages: List[Dict[str, str]]) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Translates standard OpenAI/OpenRouter style messages:
      [{role: 'system', content: '...'}, {role: 'user', content: '...'}, {role: 'assistant', content: '...'}]
    into Gemini's system_instruction and contents structure:
      contents: [{role: 'user'|'model', parts: [{text: '...'}]}]
    """
    system_instruction: Optional[Dict[str, Any]] = None
    contents: List[Dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "user").lower()
        content = msg.get("content", "")

        if role == "system":
            if system_instruction is None:
                system_instruction = {"parts": [{"text": content}]}
            else:
                system_instruction["parts"][0]["text"] += "\n\n" + content
        elif role == "user":
            contents.append({
                "role": "user",
                "parts": [{"text": content}]
            })
        elif role in ("assistant", "model"):
            contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })

    if not contents:
        contents.append({
            "role": "user",
            "parts": [{"text": "Hello"}]
        })

    return system_instruction, contents


async def chat_complete(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    task_tag: str = "general",
    trace: Optional[Any] = None,
) -> str:
    """
    Executes chat completion via Google Gemini REST API with multi-key rotation and multi-model failover.
    """
    global _active_key_idx
    chosen_model = model or getattr(settings, "gemini_model", "gemini-2.0-flash")
    start_time = time.perf_counter()
    key_pool = _get_key_pool()

    if not key_pool:
        log.warning("No GEMINI API keys configured in pool. Returning offline prompt fallback for [%s].", task_tag)
        return _offline_chat_fallback(messages, task_tag)

    system_instruction, contents = _convert_messages_to_gemini_format(messages)

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": max(0.0, min(1.0, temperature)),
            "maxOutputTokens": max_tokens,
        }
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    models_to_try = [chosen_model]
    for fallback_m in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite-preview-02-05"]:
        if fallback_m not in models_to_try:
            models_to_try.append(fallback_m)

    num_keys = len(key_pool)
    max_offsets = min(num_keys, 4)

    for offset in range(max_offsets):
        if (time.perf_counter() - start_time) > 25.0:
            log.warning("Gemini retry cascade exceeded 25s budget, stopping.")
            break

        current_idx = (_active_key_idx + offset) % num_keys
        attempt_key = key_pool[current_idx]

        for attempt_model in models_to_try:
            url = f"{GEMINI_BASE_URL}/{attempt_model}:generateContent?key={attempt_key}"
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        url,
                        headers={"Content-Type": "application/json"},
                        json=payload,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        text_parts = []
                        candidates = data.get("candidates", [])
                        if candidates:
                            content_obj = candidates[0].get("content", {})
                            parts = content_obj.get("parts", [])
                            for p in parts:
                                if "text" in p:
                                    text_parts.append(p["text"])

                        content = "".join(text_parts).strip()
                        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                        _active_key_idx = current_idx  # Sticky success

                        usage_meta = data.get("usageMetadata", {})
                        if trace:
                            trace.log(
                                "GEMINI_COMPLETION",
                                f"Completed {task_tag} via {attempt_model} (key: ...{attempt_key[-6:]}) in {elapsed_ms:.1f}ms",
                                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                            )
                        return content

                    # Handle Rate Limits (429) or Quota Exceeded (403/402)
                    if resp.status_code in (429, 403, 402):
                        log.warning(
                            "Gemini key ...%s rate-limited (status %s) on %s. Rotating key...",
                            attempt_key[-6:], resp.status_code, attempt_model
                        )
                        _active_key_idx = (current_idx + 1) % num_keys
                        break  # Try next key
                    else:
                        log.warning(
                            "Gemini model %s returned status %s: %s",
                            attempt_model, resp.status_code, resp.text[:150]
                        )
            except Exception as e:
                log.warning("Gemini request to %s with key ...%s failed: %s", attempt_model, attempt_key[-6:], str(e))

    log.error("All Gemini API keys and candidate models in pool failed for task: %s", task_tag)
    return _offline_chat_fallback(messages, task_tag)


async def embed_texts(
    texts: List[str],
    model: Optional[str] = None,
) -> List[List[float]]:
    """
    Generates dense embeddings via Google Gemini Embedding API with 768-dim normalization.
    """
    chosen_model = model or getattr(settings, "gemini_embed_model", "text-embedding-004")
    key_pool = _get_key_pool()

    if not key_pool:
        return _deterministic_fallback_vectors(texts)

    attempt_key = key_pool[0]
    url = f"{GEMINI_BASE_URL}/{chosen_model}:batchEmbedContents?key={attempt_key}"

    requests = []
    for t in texts:
        requests.append({
            "model": f"models/{chosen_model}",
            "content": {"parts": [{"text": t[:2048]}]},
            "outputDimensionality": 768
        })

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"requests": requests}
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = []
                for item in data.get("embeddings", []):
                    embeddings.append(item.get("values", []))
                if len(embeddings) == len(texts):
                    return embeddings
    except Exception as e:
        log.warning("Gemini embeddings API call failed, falling back to deterministic local vectors: %s", str(e))

    return _deterministic_fallback_vectors(texts)


def _deterministic_fallback_vectors(texts: List[str], dim: int = 768) -> List[List[float]]:
    """Deterministic hash vectors for testing and offline fallback."""
    import hashlib
    import random
    vectors = []
    for t in texts:
        seed = int(hashlib.md5(t.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        vec = [rng.gauss(0, 1) for _ in range(dim)]
        norm = sum(x**2 for x in vec) ** 0.5 or 1.0
        vectors.append([round(x / norm, 6) for x in vec])
    return vectors


def _offline_chat_fallback(messages: List[Dict[str, str]], task_tag: str) -> str:
    """Friendly fallback message when LLM API keys are not provided yet."""
    return f"[VARUNA AI Copilot] Gemini API Key is required to generate dynamic reasoning. Please configure GEMINI_API_KEY in backend/.env."
