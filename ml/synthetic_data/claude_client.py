"""Cached Claude API client with prompt caching support.

All API calls are cached to disk by default so repeated calls during
development cost zero tokens. The cache key is a SHA-256 hash of
(model, system_content, user_message, temperature, max_tokens).

Prompt caching (Anthropic's server-side cache) is applied automatically
to system content blocks that are large enough to benefit from it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL     = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1024
_MIN_CACHE_TOKENS  = 100   # only cache system prompts above this token estimate


class CachedClaudeClient:
    """Wraps the Anthropic SDK with disk-based response caching.

    Args:
        cache_dir: Directory for response cache files. Defaults to
                   the CACHE_DIR environment variable or `./data/cache`.
        api_key:   Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        api_key: str | None = None,
    ) -> None:
        self._client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
        )
        self._cache_dir = cache_dir or Path(os.getenv("CACHE_DIR", "./data/cache"))
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def complete(
        self,
        system: str | list[dict[str, Any]],
        user_message: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Send a message to Claude, returning the response dict.

        Checks disk cache first. On a miss, calls the API and caches the result.
        Applies `cache_control: ephemeral` to long system prompts automatically.

        Args:
            system:       System prompt — either a string or a list of content
                          blocks (for manual cache_control control).
            user_message: The user turn content.
            model:        Claude model ID.
            max_tokens:   Maximum tokens to generate.
            temperature:  Sampling temperature.

        Returns:
            Dict with keys: text (str), input_tokens (int), output_tokens (int),
            cached (bool), latency_ms (float).
        """
        system_blocks = self._normalize_system(system)
        cache_key     = self._make_key(model, system_blocks, user_message, temperature, max_tokens)
        cache_path    = self._cache_dir / f"{cache_key}.json"

        if cache_path.exists():
            logger.debug("Cache hit: %s", cache_key[:12])
            return json.loads(cache_path.read_text())

        logger.debug("Cache miss: %s — calling API.", cache_key[:12])
        t0 = time.monotonic()

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_blocks,
            messages=[{"role": "user", "content": user_message}],
        )

        latency_ms  = (time.monotonic() - t0) * 1000
        result: dict[str, Any] = {
            "text":         response.content[0].text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cached":       False,
            "latency_ms":   round(latency_ms, 1),
        }
        cache_path.write_text(json.dumps(result))
        logger.info(
            "API call complete: in=%d out=%d latency=%.0fms model=%s",
            result["input_tokens"], result["output_tokens"], latency_ms, model,
        )
        return result

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _normalize_system(
        self, system: str | list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert a plain string system prompt to a content-block list.

        Adds `cache_control: ephemeral` when the prompt is long enough to
        benefit from Anthropic's server-side prompt caching (saves ~90% on
        repeated calls with the same system prompt).
        """
        if isinstance(system, list):
            return system
        block: dict[str, Any] = {"type": "text", "text": system}
        # Rough token estimate: 4 chars ≈ 1 token
        if len(system) // 4 >= _MIN_CACHE_TOKENS:
            block["cache_control"] = {"type": "ephemeral"}
        return [block]

    @staticmethod
    def _make_key(
        model: str,
        system_blocks: list[dict[str, Any]],
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = json.dumps(
            {
                "model":       model,
                "system":      system_blocks,
                "user":        user_message,
                "temperature": temperature,
                "max_tokens":  max_tokens,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()
