"""Credentials, session tokens, and the seeded customer book."""

from __future__ import annotations

import time

from app.services.auth import (
    LoginThrottle,
    hash_pin,
    is_valid_pin,
    issue_token,
    normalize_phone,
    verify_pin,
    verify_token,
)
from app.wallet.repository import InMemoryRepository
from app.wallet.seed_profiles import SEED_PERSONAS, build_ledger
from app.wallet.store import Bank

_SECRET = "test-secret"


# ── Phone normalisation ────────────────────────────────────────────────────────
def test_phone_forms_collapse_to_one_key() -> None:
    for typed in ("+65 8000 0001", "6580000001", "80000001", "+6580000001", "8000-0001"):
        assert normalize_phone(typed) == "+6580000001"


def test_overseas_number_keeps_its_country_code() -> None:
    assert normalize_phone("+60 12 399 8877") == "+60123998877"


def test_blank_phone_normalises_to_empty() -> None:
    assert normalize_phone(None) == "" and normalize_phone("  ") == ""


# ── PIN hashing ────────────────────────────────────────────────────────────────
def test_pin_round_trips_and_rejects_the_wrong_one() -> None:
    encoded = hash_pin("112233")
    assert verify_pin("112233", encoded)
    assert not verify_pin("112234", encoded)


def test_hash_never_contains_the_pin_and_is_salted() -> None:
    first, second = hash_pin("445566"), hash_pin("445566")
    assert "445566" not in first
    assert first != second  # distinct salts
    assert verify_pin("445566", first) and verify_pin("445566", second)


def test_verify_is_false_rather_than_raising_on_junk() -> None:
    assert not verify_pin("112233", None)
    assert not verify_pin("112233", "not-a-hash")
    assert not verify_pin(None, hash_pin("112233"))


def test_pin_must_be_six_digits() -> None:
    assert is_valid_pin("000000")
    assert not is_valid_pin("12345")
    assert not is_valid_pin("1234567")
    assert not is_valid_pin("12a456")


# ── Session tokens ─────────────────────────────────────────────────────────────
def test_token_round_trips_to_its_subject() -> None:
    token = issue_token("acc_may", secret=_SECRET, ttl_seconds=60)
    assert verify_token(token, secret=_SECRET) == "acc_may"


def test_token_signed_with_another_key_is_rejected() -> None:
    token = issue_token("acc_may", secret=_SECRET, ttl_seconds=60)
    assert verify_token(token, secret="other-secret") is None


def test_tampered_payload_is_rejected() -> None:
    token = issue_token("acc_may", secret=_SECRET, ttl_seconds=60)
    payload, _, signature = token.partition(".")
    forged = issue_token("acc_robert", secret="attacker", ttl_seconds=60).partition(".")[0]
    assert verify_token(f"{forged}.{signature}", secret=_SECRET) is None
    assert verify_token(f"{payload}.", secret=_SECRET) is None


def test_expired_token_is_rejected() -> None:
    assert verify_token(issue_token("acc_may", secret=_SECRET, ttl_seconds=-1), secret=_SECRET) is None


def test_garbage_token_is_rejected_not_raised() -> None:
    for junk in (None, "", "no-dot", "!!!.???"):
        assert verify_token(junk, secret=_SECRET) is None


# ── Throttle ───────────────────────────────────────────────────────────────────
def test_throttle_locks_after_the_limit_and_clears_on_success() -> None:
    throttle = LoginThrottle(max_attempts=3, lock_seconds=30)
    assert throttle.retry_after("+6580000001") == 0
    for _ in range(3):
        throttle.record_failure("+6580000001")
    assert throttle.retry_after("+6580000001") > 0
    assert throttle.retry_after("+6580000002") == 0  # scoped per phone number

    throttle.record_success("+6580000001")
    assert throttle.retry_after("+6580000001") == 0


def test_throttle_lock_expires() -> None:
    throttle = LoginThrottle(max_attempts=1, lock_seconds=0.01)
    throttle.record_failure("+6580000001")
    time.sleep(0.02)
    assert throttle.retry_after("+6580000001") == 0


# ── Seeded customer book ───────────────────────────────────────────────────────
def test_every_seeded_customer_can_be_signed_into() -> None:
    bank = Bank()
    for persona in SEED_PERSONAS:
        account = bank.account(persona.id)
        assert account is not None, persona.id
        assert verify_pin(persona.pin, account.pin_hash), persona.id


def test_seeded_pins_and_phones_are_unique() -> None:
    assert len({p.pin for p in SEED_PERSONAS}) == len(SEED_PERSONAS)
    assert len({normalize_phone(p.phone) for p in SEED_PERSONAS}) == len(SEED_PERSONAS)


def test_lookup_by_phone_is_forgiving_about_formatting() -> None:
    assert Bank().account_by_phone("8000 0001").owner.id == "acc_may"
    assert Bank().account_by_phone("+6599999999") is None


def test_each_customer_has_a_distinct_transaction_history() -> None:
    bank = Bank()
    for persona in SEED_PERSONAS:
        ledger = bank.account(persona.id).ledger
        assert len(ledger) >= 15, f"{persona.id} has a thin file: {len(ledger)}"
        assert any(e.direction == "in" for e in ledger), persona.id
        assert any(e.direction == "out" for e in ledger), persona.id

    # No two customers share a counterparty mix — the point of the seed is that the
    # risk engine sees genuinely different behaviour per account.
    signatures = {
        persona.id: frozenset(e.counterparty for e in bank.account(persona.id).ledger)
        for persona in SEED_PERSONAS
    }
    assert len(set(signatures.values())) == len(SEED_PERSONAS)


def test_baselines_differ_enough_to_change_a_verdict() -> None:
    """The same 8k transfer must read very differently for Wong and for Robert."""
    bank = Bank()
    wong = bank.account("acc_wong")
    robert = bank.account("acc_robert")
    wong_avg = sum(e.amount for e in wong.ledger if e.direction == "out") / max(
        1, len([e for e in wong.ledger if e.direction == "out"])
    )
    robert_avg = sum(e.amount for e in robert.ledger if e.direction == "out") / max(
        1, len([e for e in robert.ledger if e.direction == "out"])
    )
    assert robert_avg > wong_avg * 10


def test_seed_is_deterministic_across_builds() -> None:
    """Stable ids and amounts, so re-seeding a database updates rather than duplicates."""
    first, second = build_ledger(SEED_PERSONAS[0]), build_ledger(SEED_PERSONAS[0])
    assert [row.id for row in first] == [row.id for row in second]
    assert [row.amount for row in first] == [row.amount for row in second]
    assert len({row.id for row in first}) == len(first)  # ids unique within a persona


def test_seeded_case_ids_are_stable() -> None:
    assert {c for c in Bank().cases} == {c for c in Bank().cases}


# ── Repository credential surface ──────────────────────────────────────────────
async def test_repository_returns_credentials_by_phone() -> None:
    repo = InMemoryRepository(Bank())
    found = await repo.get_credentials("8000 0001")
    assert found is not None and found["id"] == "acc_may"
    assert verify_pin("445566", found["pin_hash"])
    assert await repo.get_credentials("+6599999999") is None


async def test_created_profile_can_sign_in_and_change_its_pin() -> None:
    repo = InMemoryRepository(Bank())
    profile = await repo.create_profile(
        name="Test Lim", phone="+6591112222", pin_hash=hash_pin("556677")
    )
    credentials = await repo.get_credentials("+6591112222")
    assert credentials["id"] == profile["id"]
    assert verify_pin("556677", credentials["pin_hash"])

    assert await repo.set_pin(profile["id"], hash_pin("667788"))
    refreshed = await repo.get_credentials("+6591112222")
    assert verify_pin("667788", refreshed["pin_hash"])
    assert not verify_pin("556677", refreshed["pin_hash"])


async def test_pin_hash_is_never_serialised_to_a_client() -> None:
    """The console renders profiles wholesale — the credential must not ride along."""
    bank = Bank()
    repo = InMemoryRepository(bank)
    for payload in await repo.list_profiles():
        assert "pin" not in str(payload).lower()
    profile = await repo.get_profile("acc_may")
    assert "pin" not in str(profile).lower()
    assert "pin_hash" not in bank.account("acc_may").summary()
