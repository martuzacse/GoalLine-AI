"""OpenAI-compatible chat client for DeepSeek."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx


class DeepSeekError(RuntimeError):
    pass


def _base_url() -> str:
    base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1").rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base


def chat_json(messages: list[dict[str, str]], *, model: str | None = None) -> tuple[dict[str, Any], str]:
    """
    Send chat completion and parse a JSON object from the assistant message.
    Returns (parsed_dict, raw_text).
    """
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise DeepSeekError("DEEPSEEK_API_KEY is not set. Copy env.example to .env and add your key.")

    payload = {
        "model": model or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    url = f"{_base_url()}/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:  # pragma: no cover - network
        raise DeepSeekError(f"DeepSeek HTTP error: {exc}") from exc

    try:
        raw = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise DeepSeekError(f"Unexpected API payload: {data!r}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise DeepSeekError("Model did not return valid JSON.") from None
        parsed = json.loads(m.group(0))

    if not isinstance(parsed, dict):
        raise DeepSeekError("Parsed JSON was not an object.")
    return parsed, raw

