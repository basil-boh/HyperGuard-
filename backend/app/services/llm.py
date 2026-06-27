"""Thin async wrapper over the chat-completions API.

Every method is null-safe: when no key is configured `enabled` is False and the
callers fall back to their deterministic heuristics. The wrapper never raises into
agent code, a transport error degrades to `None`, not a crashed intervention.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings

logger = logging.getLogger("hyperguard.llm")


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    @property
    def enabled(self) -> bool:
        return self._settings.llm_enabled

    def _ensure(self) -> Any | None:
        if not self.enabled:
            return None
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self._settings.openai_api_key,
                    timeout=self._settings.llm_timeout_seconds,
                )
            except Exception as exc:  # pragma: no cover - dep optional
                logger.warning("OpenAI client unavailable: %s", exc)
                return None
        return self._client

    async def _create(self, client, **kwargs):
        """Call chat.completions, retrying once without params a newer model rejects
        (e.g. gpt-5.x rejects a custom `temperature` / `max_tokens`)."""
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as exc:
            msg = str(exc).lower()
            stripped = False
            for param in ("temperature", "max_tokens"):
                if param in msg and param in kwargs:
                    kwargs.pop(param, None)
                    stripped = True
            if not stripped:
                raise
            return await client.chat.completions.create(**kwargs)

    async def complete_json(
        self, system: str, user: str, *, temperature: float | None = None
    ) -> dict | None:
        client = self._ensure()
        if client is None:
            return None
        try:
            resp = await self._create(
                client,
                model=self._settings.llm_model,
                temperature=temperature
                if temperature is not None
                else self._settings.llm_temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception as exc:
            logger.warning("LLM json completion failed, falling back: %s", exc)
            return None

    async def complete_text(
        self, system: str, user: str, *, temperature: float | None = None
    ) -> str | None:
        client = self._ensure()
        if client is None:
            return None
        try:
            resp = await self._create(
                client,
                model=self._settings.llm_model,
                temperature=temperature
                if temperature is not None
                else self._settings.llm_temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("LLM text completion failed, falling back: %s", exc)
            return None
