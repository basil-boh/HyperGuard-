"""Thin async wrapper over the chat-completions API.

Every method is null-safe: when no key is configured `enabled` is False and the
callers fall back to their deterministic heuristics. The wrapper never raises into
agent code, a transport error degrades to `None`, not a crashed intervention.

Calls are *tiered* — see `services/model_policy`. Pass `tier="fast"` (the default)
for work on the critical path of a live call, `tier="deep"` once a case has escalated
or for a written artefact. The tier resolves to a model id through settings, and each
call is recorded on the supplied `ModelUsage` so the saving is measurable.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import Settings
from app.services.model_policy import FAST, ModelCall, ModelUsage

logger = logging.getLogger("hyperguard.llm")


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    @property
    def enabled(self) -> bool:
        return self._settings.llm_enabled

    def model_for(self, tier: str) -> str:
        return self._settings.model_for(tier)

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

    async def _call(
        self,
        system: str,
        user: str,
        *,
        tier: str,
        purpose: str,
        usage: ModelUsage | None,
        temperature: float | None,
        json_mode: bool,
    ) -> str | None:
        client = self._ensure()
        if client is None:
            return None

        model = self.model_for(tier)
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature if temperature is not None else self._settings.llm_temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        try:
            resp = await self._create(client, **kwargs)
        except Exception as exc:
            logger.warning("LLM %s (%s/%s) failed, falling back: %s", purpose, tier, model, exc)
            self._record(usage, purpose, tier, model, started, ok=False)
            return None

        self._record(usage, purpose, tier, model, started, resp=resp)
        return resp.choices[0].message.content

    @staticmethod
    def _record(
        usage: ModelUsage | None,
        purpose: str,
        tier: str,
        model: str,
        started: float,
        *,
        resp: Any | None = None,
        ok: bool = True,
    ) -> None:
        latency_ms = int((time.perf_counter() - started) * 1000)
        prompt_tokens = completion_tokens = 0
        token_usage = getattr(resp, "usage", None) if resp is not None else None
        if token_usage is not None:
            prompt_tokens = getattr(token_usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(token_usage, "completion_tokens", 0) or 0
        logger.info(
            "llm %s tier=%s model=%s %dms in=%d out=%d%s",
            purpose, tier, model, latency_ms, prompt_tokens, completion_tokens,
            "" if ok else " FAILED",
        )
        if usage is not None:
            usage.record(
                ModelCall(
                    purpose=purpose, tier=tier, model=model, latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, ok=ok,
                )
            )

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        tier: str = FAST,
        purpose: str = "json",
        usage: ModelUsage | None = None,
    ) -> dict | None:
        raw = await self._call(
            system, user, tier=tier, purpose=purpose, usage=usage,
            temperature=temperature, json_mode=True,
        )
        if raw is None:
            return None
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            logger.warning("LLM %s returned invalid JSON, falling back: %s", purpose, exc)
            return None

    async def complete_text(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        tier: str = FAST,
        purpose: str = "text",
        usage: ModelUsage | None = None,
    ) -> str | None:
        raw = await self._call(
            system, user, tier=tier, purpose=purpose, usage=usage,
            temperature=temperature, json_mode=False,
        )
        return (raw or "").strip() or None
