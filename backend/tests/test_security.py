"""Auth hardening: admin key, signed user sessions, Twilio signatures, WS guard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.deps import repository
from app.config import Settings, get_settings
from app.main import app
from app.services.auth import mint_session_token, verify_session_token
from app.wallet.repository import InMemoryRepository


def _settings(**overrides) -> Settings:
    # _env_file=None keeps the developer's real .env out of the tests.
    return Settings(_env_file=None, demo_step_delay=0, **overrides)


@pytest.fixture
def client():
    # In-memory repo: the auth paths under test must not depend on Supabase creds
    # that may be present in the developer's .env.
    app.dependency_overrides[repository] = lambda: InMemoryRepository()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _use(settings: Settings) -> None:
    app.dependency_overrides[get_settings] = lambda: settings


# ── Session tokens ─────────────────────────────────────────────────────────────


def test_token_round_trip() -> None:
    token, _ = mint_session_token("acc_alex", "s3cret", ttl_seconds=60)
    assert verify_session_token(token, "s3cret") == "acc_alex"


def test_token_rejects_tamper_wrong_secret_and_expiry() -> None:
    token, _ = mint_session_token("acc_alex", "s3cret", ttl_seconds=60)
    assert verify_session_token(token + "x", "s3cret") is None
    assert verify_session_token(token, "other") is None
    expired, _ = mint_session_token("acc_alex", "s3cret", ttl_seconds=-1)
    assert verify_session_token(expired, "s3cret") is None
    assert verify_session_token("garbage", "s3cret") is None


# ── Admin API ──────────────────────────────────────────────────────────────────


def test_admin_open_in_development_without_key(client: TestClient) -> None:
    _use(_settings())
    assert client.get("/api/admin/overview").status_code == 200


def test_admin_disabled_in_production_without_key(client: TestClient) -> None:
    _use(_settings(environment="production"))
    assert client.get("/api/admin/overview").status_code == 503


def test_admin_requires_key_when_configured(client: TestClient) -> None:
    _use(_settings(admin_api_key="topsecret"))
    assert client.get("/api/admin/overview").status_code == 401
    assert (
        client.get("/api/admin/overview", headers={"X-Admin-Key": "wrong"}).status_code
        == 401
    )
    assert (
        client.get(
            "/api/admin/overview", headers={"X-Admin-Key": "topsecret"}
        ).status_code
        == 200
    )


# ── User identity ──────────────────────────────────────────────────────────────


def test_user_header_trusted_only_without_session_secret(client: TestClient) -> None:
    _use(_settings())
    assert client.get("/api/wallet").status_code == 200

    _use(_settings(session_secret="hmac-secret"))
    # Raw header is no longer enough.
    assert client.get("/api/wallet", headers={"X-User-Id": "acc_alex"}).status_code == 401

    token, _ = mint_session_token("acc_alex", "hmac-secret", 60)
    res = client.get("/api/wallet", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    forged, _ = mint_session_token("acc_alex", "attacker-secret", 60)
    assert (
        client.get("/api/wallet", headers={"Authorization": f"Bearer {forged}"}).status_code
        == 401
    )


def test_session_endpoint_mints_for_existing_user_only(client: TestClient) -> None:
    _use(_settings(session_secret="hmac-secret"))
    assert (
        client.post("/api/users/session", json={"user_id": "nope"}).status_code == 404
    )
    res = client.post("/api/users/session", json={"user_id": "acc_alex"})
    assert res.status_code == 200
    body = res.json()
    assert verify_session_token(body["token"], "hmac-secret") == "acc_alex"


# ── Twilio webhooks ────────────────────────────────────────────────────────────


def test_twilio_webhook_rejects_missing_or_bad_signature(client: TestClient) -> None:
    _use(_settings(twilio_auth_token="twil-token"))
    res = client.post("/twilio/voice/start?case_id=HG-1")
    assert res.status_code == 403
    res = client.post(
        "/twilio/voice/start?case_id=HG-1", headers={"X-Twilio-Signature": "bogus"}
    )
    assert res.status_code == 403


def test_twilio_webhook_accepts_valid_signature(client: TestClient) -> None:
    from twilio.request_validator import RequestValidator

    _use(_settings(twilio_auth_token="twil-token"))
    url = "http://testserver/twilio/voice/start?case_id=HG-1"
    signature = RequestValidator("twil-token").compute_signature(url, {})
    res = client.post(url, headers={"X-Twilio-Signature": signature})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/xml")


def test_twilio_webhook_disabled_in_production_without_token(client: TestClient) -> None:
    _use(_settings(environment="production"))
    assert client.post("/twilio/voice/start?case_id=HG-1").status_code == 503


# ── WebSocket ──────────────────────────────────────────────────────────────────


def test_ws_open_when_no_auth_configured_in_dev(client: TestClient) -> None:
    _use(_settings())
    with client.websocket_connect("/ws/events"):
        pass


def test_ws_rejects_without_token_when_guarded(client: TestClient) -> None:
    _use(_settings(admin_api_key="topsecret"))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/events"):
            pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/events?token=wrong"):
            pass
    with client.websocket_connect("/ws/events?token=topsecret"):
        pass


def test_ws_accepts_user_session_token(client: TestClient) -> None:
    _use(_settings(session_secret="hmac-secret"))
    token, _ = mint_session_token("acc_alex", "hmac-secret", 60)
    with client.websocket_connect(f"/ws/events?token={token}"):
        pass


def test_ws_closed_in_production_without_auth(client: TestClient) -> None:
    _use(_settings(environment="production"))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/events"):
            pass
