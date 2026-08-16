"""Runtime configuration.

Every external dependency (LLM, telephony, persistence, event bus) is *optional*.
When a credential is absent the corresponding subsystem degrades to a deterministic
in-process simulation, so the full swarm runs end-to-end before any key is supplied.
The `*_enabled` properties are the single source of truth for that capability gating.
"""

from __future__ import annotations

import logging
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

    # ── Multi-user / behaviour ──────────────────────────────────────────────────
    # The account a request maps to when no X-User-Id header is sent (back-compat
    # with the single-user demo client).
    default_app_user_id: str = "acc_alex"
    # ISO country customers bank in; transfers to other countries score as overseas.
    home_country: str = "SG"
    # Minimum outbound transactions before behavioural baselines are "learned"
    # rather than using lenient cold-start defaults.
    baseline_min_transactions: int = 5

    # ── Auth ───────────────────────────────────────────────────────────────────
    # HMAC key for session tokens. Unset is fine for local work (a fixed dev key is
    # used and a warning logged); set it in any deployed environment, or every
    # restart with a different key would sign customers out.
    auth_secret: str | None = None
    auth_token_ttl_hours: int = 24 * 30
    # Serve the seeded phone/PIN pairs from GET /api/auth/demo-accounts and show them
    # on the sign-in screen. Intended for testing; turn off for a public deployment.
    expose_demo_credentials: bool = True
    # Accept the legacy `X-User-Id` header as identity when no bearer token is sent.
    # Keeps pre-login clients and curl-driven demos working; disable to require login.
    allow_header_user_override: bool = True

    # ── LLM ────────────────────────────────────────────────────────────────────
    openai_api_key: str | None = None
    # Legacy single-model setting. Still honoured as the fallback for both tiers so
    # an existing .env keeps working unchanged.
    llm_model: str = "gpt-5.5"
    # Tiered models (see services/model_policy). Routine work — the negotiator's
    # in-call lines on an unescalated case — runs on the fast model; a confirmed scam
    # or a hard-block-level risk promotes to the deep one, as do the written outputs.
    # NB: this must be a model id the configured key can actually reach. A wrong id 404s
    # on every routine call, and because the failure path returns None the callers quietly
    # fall back to their scripted lines — the swarm looks up (`capabilities.llm` stays
    # true) while the customer hears templates. `_call` now retries such a failure on the
    # deep tier so a bad id degrades to expensive rather than to silent.
    llm_model_fast: str = "gpt-5-mini"
    llm_model_deep: str | None = None  # falls back to llm_model
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 30.0
    # Optional USD per 1M tokens, used only to turn recorded token counts into a cost
    # estimate. Left unset, the API reports tokens and latency but never dollars —
    # a guessed price is worse than no price.
    llm_price_fast_input: float = 0.0
    llm_price_fast_output: float = 0.0
    llm_price_deep_input: float = 0.0
    llm_price_deep_output: float = 0.0

    # ── Voice / telephony ──────────────────────────────────────────────────────
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None
    # When set, every intervention call is routed to this number instead of the
    # customer's profile phone — used for demos so the call reaches a real, verified
    # handset. Keep it in .env (not committed) rather than hard-coded in source.
    intervention_call_number: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # ── Persistence & transport ────────────────────────────────────────────────
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    redis_url: str | None = None

    # Public HTTPS base (e.g. an ngrok URL) that Twilio can reach for interactive
    # voice webhooks. When unset, the call degrades to the single-line spoken warning.
    public_base_url: str | None = None

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
    def auth_signing_key(self) -> str:
        """The key session tokens are signed with.

        Falls back to a fixed development key so the app runs out of the box; the
        warning is the nudge to set AUTH_SECRET before anything ships.
        """
        if self.auth_secret:
            return self.auth_secret
        if self.environment.lower() not in {"development", "test", "local"}:
            logging.getLogger("hyperguard.auth").warning(
                "AUTH_SECRET is unset in environment=%s — session tokens are signed "
                "with the public development key.",
                self.environment,
            )
        return "hyperguard-dev-signing-key-do-not-use-in-production"

    def model_for(self, tier: str) -> str:
        """Resolve a policy tier to a concrete model id."""
        if tier == "deep":
            return self.llm_model_deep or self.llm_model
        return self.llm_model_fast or self.llm_model

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
