"""Runtime configuration.

Every external dependency (LLM, telephony, persistence, event bus) is *optional*.
When a credential is absent the corresponding subsystem degrades to a deterministic
in-process simulation, so the full swarm runs end-to-end before any key is supplied.
The `*_enabled` properties are the single source of truth for that capability gating.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "HyperGuard"
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # NoDecode keeps pydantic-settings from JSON-parsing this list from the env;
    # the validator below accepts a plain comma-separated string instead.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # ── Risk policy ────────────────────────────────────────────────────────────
    # Score at/above which the swarm escalates from silent scoring to live intervention.
    intervention_threshold: float = 0.58
    # Score at/above which a transfer is auto-held pending human/guardian confirmation.
    hard_block_threshold: float = 0.88
    max_negotiation_turns: int = 8

    # Synthetic cadence between narrated steps in demo mode, so the console reads as
    # a live operation rather than an instant dump. Set to 0 for tests.
    demo_step_delay: float = 0.75

    # ── LLM ────────────────────────────────────────────────────────────────────
    openai_api_key: str | None = None
    llm_model: str = "gpt-5.5"
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 30.0

    # ── Voice / telephony ──────────────────────────────────────────────────────
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # ── Persistence & transport ────────────────────────────────────────────────
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    redis_url: str | None = None

    # ── Overrides ──────────────────────────────────────────────────────────────
    # Force the deterministic simulation path even when credentials are present —
    # useful for a hermetic stage demo.
    force_demo_mode: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # ── Capability gates ───────────────────────────────────────────────────────
    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key) and not self.force_demo_mode

    @property
    def telephony_enabled(self) -> bool:
        return bool(
            self.twilio_account_sid and self.twilio_auth_token and self.twilio_phone_number
        ) and not self.force_demo_mode

    @property
    def speech_enabled(self) -> bool:
        return bool(self.elevenlabs_api_key) and not self.force_demo_mode

    @property
    def persistence_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def event_bus_enabled(self) -> bool:
        return bool(self.redis_url)

    @property
    def demo_mode(self) -> bool:
        """True when no live LLM is wired, the swarm runs on deterministic scripts."""
        return self.force_demo_mode or not self.llm_enabled

    def capability_report(self) -> dict[str, bool]:
        return {
            "llm": self.llm_enabled,
            "telephony": self.telephony_enabled,
            "speech": self.speech_enabled,
            "persistence": self.persistence_enabled,
            "distributed_bus": self.event_bus_enabled,
            "demo_mode": self.demo_mode,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
