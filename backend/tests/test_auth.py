"""Operator auth: login, the REST guard, and websocket first-message auth."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.auth import create_admin_token, verify_admin_token
from app.config import get_settings
from app.main import create_app
from app.wallet.repository import get_repository

PASSWORD = "operator-secret"


def _make_client(monkeypatch, password: str | None) -> TestClient:
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_password", password)
    monkeypatch.setattr(settings, "demo_step_delay", 0.0)
    # Hermetic: force the in-memory repository even when .env carries Supabase creds.
    monkeypatch.setattr(settings, "supabase_url", None)
    monkeypatch.setattr(settings, "supabase_service_key", None)
    get_repository.cache_clear()
    return TestClient(create_app())


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    with _make_client(monkeypatch, PASSWORD) as c:
        yield c
    get_repository.cache_clear()


@pytest.fixture()
def open_client(monkeypatch) -> TestClient:
    with _make_client(monkeypatch, None) as c:
        yield c
    get_repository.cache_clear()


def _login(client: TestClient) -> str:
    res = client.post("/api/admin/login", json={"password": PASSWORD})
    assert res.status_code == 200
    return res.json()["token"]


# ── Login ──────────────────────────────────────────────────────────────────────
def test_login_issues_token(client: TestClient) -> None:
    res = client.post("/api/admin/login", json={"password": PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert verify_admin_token(body["token"], get_settings())


def test_login_rejects_wrong_password(client: TestClient) -> None:
    assert client.post("/api/admin/login", json={"password": "nope"}).status_code == 401


def test_login_unavailable_when_not_configured(open_client: TestClient) -> None:
    res = open_client.post("/api/admin/login", json={"password": "anything"})
    assert res.status_code == 503


# ── REST guard ─────────────────────────────────────────────────────────────────
def test_admin_routes_require_token(client: TestClient) -> None:
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/users").status_code == 401
    assert client.post("/api/interventions/run", json={"scenario_id": "x"}).status_code == 401


def test_admin_routes_accept_valid_token(client: TestClient) -> None:
    token = _login(client)
    res = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "customers" in res.json()


def test_admin_routes_reject_garbage_token(client: TestClient) -> None:
    res = client.get("/api/admin/overview", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401


def test_expired_token_is_rejected(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_token_ttl_seconds", -1)
    token, _ = create_admin_token(settings)
    assert not verify_admin_token(token, settings)


def test_admin_routes_open_when_auth_disabled(open_client: TestClient) -> None:
    assert open_client.get("/api/admin/overview").status_code == 200


def test_unguarded_routes_stay_open(client: TestClient) -> None:
    # The wallet app and health check are customer-side; the operator guard
    # must not leak onto them.
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/scenarios").status_code == 200


# ── WebSocket guard ────────────────────────────────────────────────────────────
def test_ws_rejects_bad_token(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        ws.send_json({"token": "bogus"})
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4401


def test_ws_accepts_valid_token(client: TestClient) -> None:
    token = _login(client)
    with client.websocket_connect("/ws/events") as ws:
        ws.send_json({"token": token})
        assert ws.receive_json() == {"type": "auth.ok"}


def test_ws_open_when_auth_disabled(open_client: TestClient) -> None:
    # No handshake required; the socket goes straight to replay/live-tail mode.
    with open_client.websocket_connect("/ws/events"):
        pass
