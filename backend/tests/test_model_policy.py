"""Model tiering: which model a call runs on, and what it cost."""

from __future__ import annotations

from app.config import Settings
from app.services.model_policy import (
    DEEP,
    FAST,
    ModelCall,
    ModelUsage,
    get_usage,
    peek_usage,
    reset_usage,
    tier_for,
)


def _settings(**kwargs) -> Settings:
    return Settings(openai_api_key="test-key", **kwargs)


def _classification(archetype: str, confidence: float) -> dict:
    return {"archetype": archetype, "confidence": confidence}


# ── Tier selection ─────────────────────────────────────────────────────────────
def test_routine_traffic_stays_on_the_cheap_model() -> None:
    s = _settings()
    assert tier_for(risk_score=0.06, classification=None, settings=s) == FAST
    assert tier_for(risk_score=0.52, classification=None, settings=s) == FAST
    # An intervention is under way but nothing is confirmed — still exploratory.
    assert tier_for(risk_score=0.74, classification=None, settings=s) == FAST


def test_confirmed_scam_promotes_to_the_deep_model() -> None:
    s = _settings()
    assert (
        tier_for(
            risk_score=0.74,
            classification=_classification("romance_scam", 0.92),
            settings=s,
        )
        == DEEP
    )


def test_hard_block_risk_promotes_even_without_a_classification() -> None:
    s = _settings()
    assert tier_for(risk_score=0.97, classification=None, settings=s) == DEEP
    # Exactly at the threshold counts as crossing it.
    assert tier_for(risk_score=s.hard_block_threshold, classification=None, settings=s) == DEEP


def test_a_weak_hunch_is_not_a_confirmation() -> None:
    """Below the graph's 0.6 confirmation bar we keep paying the cheap rate."""
    s = _settings()
    assert (
        tier_for(
            risk_score=0.74,
            classification=_classification("romance_scam", 0.45),
            settings=s,
        )
        == FAST
    )


def test_none_and_unknown_archetypes_do_not_promote() -> None:
    s = _settings()
    for archetype in ("none", "unknown"):
        assert (
            tier_for(
                risk_score=0.5,
                classification=_classification(archetype, 0.99),
                settings=s,
            )
            == FAST
        )


def test_explicit_escalation_overrides_everything() -> None:
    s = _settings()
    assert tier_for(risk_score=0.01, classification=None, settings=s, escalated=True) == DEEP


def test_malformed_classification_does_not_raise() -> None:
    s = _settings()
    assert tier_for(risk_score=0.1, classification={"archetype": "romance_scam"}, settings=s) == FAST
    assert (
        tier_for(
            risk_score=0.1,
            classification={"archetype": "romance_scam", "confidence": "high"},
            settings=s,
        )
        == FAST
    )


# ── Model resolution ───────────────────────────────────────────────────────────
def test_tiers_resolve_to_the_configured_models() -> None:
    s = _settings(llm_model_fast="gpt-5.5-mini", llm_model_deep="gpt-5.5")
    assert s.model_for(FAST) == "gpt-5.5-mini"
    assert s.model_for(DEEP) == "gpt-5.5"


def test_deep_falls_back_to_the_legacy_single_model_setting() -> None:
    """An existing .env that only sets LLM_MODEL keeps working."""
    s = _settings(llm_model="my-model", llm_model_deep=None)
    assert s.model_for(DEEP) == "my-model"


# ── Usage accounting ───────────────────────────────────────────────────────────
def _usage() -> ModelUsage:
    usage = ModelUsage()
    usage.record(ModelCall("negotiator.opening", FAST, "fast-model", 300, 400, 50))
    usage.record(ModelCall("assessment", DEEP, "deep-model", 1200, 800, 200))
    return usage


def test_summary_splits_spend_by_tier() -> None:
    summary = _usage().summary(_settings())
    assert summary["total_calls"] == 2
    assert summary["by_tier"][FAST]["calls"] == 1
    assert summary["by_tier"][DEEP]["prompt_tokens"] == 800
    assert summary["total_latency_ms"] == 1500
    assert summary["promoted"] is True


def test_a_case_that_never_promoted_is_marked_as_such() -> None:
    usage = ModelUsage()
    usage.record(ModelCall("negotiator.opening", FAST, "fast-model", 300, 400, 50))
    assert usage.summary(_settings())["promoted"] is False


def test_cost_is_omitted_when_no_prices_are_configured() -> None:
    """Better to report nothing than to invent a rate."""
    assert "estimated_cost_usd" not in _usage().summary(_settings())


def test_cost_is_reported_against_an_all_deep_baseline() -> None:
    priced = _settings(
        llm_price_fast_input=0.15, llm_price_fast_output=0.60,
        llm_price_deep_input=1.25, llm_price_deep_output=10.0,
    )
    cost = _usage().summary(priced)["estimated_cost_usd"]
    # fast call: 400 in @0.15 + 50 out @0.60 per 1M
    # deep call: 800 in @1.25 + 200 out @10.0 per 1M
    assert cost["actual"] == round((400 * 0.15 + 50 * 0.60) / 1e6 + (800 * 1.25 + 200 * 10.0) / 1e6, 6)
    assert cost["if_all_deep"] > cost["actual"]
    assert cost["saved"] == round(cost["if_all_deep"] - cost["actual"], 6)


def test_failed_calls_are_still_recorded() -> None:
    """A model that errored still cost latency, and hiding it would flatter the numbers."""
    usage = ModelUsage()
    usage.record(ModelCall("assessment", DEEP, "deep-model", 900, 0, 0, ok=False))
    summary = usage.summary(_settings())
    assert summary["total_calls"] == 1
    assert summary["calls"][0]["ok"] is False


# ── Per-case ledgers ───────────────────────────────────────────────────────────
def test_ledgers_are_per_case_and_shared_across_stages() -> None:
    reset_usage()
    first = get_usage("HG-1")
    first.record(ModelCall("negotiator.opening", FAST, "fast-model", 100))
    # The follow-up stage fetches the same ledger later and appends to it.
    get_usage("HG-1").record(ModelCall("assessment", DEEP, "deep-model", 900))

    assert len(get_usage("HG-1").calls) == 2
    assert get_usage("HG-2").calls == []


def test_peek_does_not_create_a_ledger() -> None:
    reset_usage()
    assert peek_usage("HG-never-seen") is None
