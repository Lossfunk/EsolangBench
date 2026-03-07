from __future__ import annotations

import os
from typing import List

import requests

from .config import MODEL_NAME_TO_ID, OPENROUTER_BASE_URL


class OpenRouterError(RuntimeError):
    """Raised when calls to OpenRouter fail."""


def call_llm(
    model_name: str,
    system_prompt: str,
    user_messages: List[str],
    temperature: float = 0.2,
    max_tokens: int = 8192,
) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY environment variable is not set")

    model_id = MODEL_NAME_TO_ID.get(model_name)
    if not model_id:
        raise OpenRouterError(f"Unknown model name: {model_name}")

    # Allow env override for temperature to tune latency/variance without code changes
    temp_env = os.environ.get("OPENROUTER_TEMPERATURE")
    if temp_env is not None:
        try:
            temperature = float(temp_env)
        except ValueError:
            pass

    payload = {
        "model": model_id,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system_prompt}]
        + [{"role": "user", "content": content} for content in user_messages],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    verbose = os.getenv("OPENROUTER_VERBOSE") == "1"
    log_file = os.getenv("OPENROUTER_LOG_FILE")

    if verbose:
        print("[OpenRouter] Request payload:")
        print(payload)

    try:
        timeout_s = float(os.environ.get("OPENROUTER_TIMEOUT_SECONDS", "90"))
        response = requests.post(
            OPENROUTER_BASE_URL,
            json=payload,
            headers=headers,
            timeout=timeout_s,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise OpenRouterError(f"Request to OpenRouter failed: {exc}") from exc

    if response.status_code != 200:
        raise OpenRouterError(
            f"OpenRouter returned status {response.status_code}: {response.text}"
        )

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise OpenRouterError(f"Malformed response structure: {data}") from exc
    content = content.strip()

    if verbose:
        print("[OpenRouter] Response content:")
        print(content)

    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(content + "\n\n")

    return content
