"""Tests for GET /api/prompt-usage[/by-prompt|/by-model|/by-user] — real
server.app.test_client(), DATABASE_URL isolation via the project's root
conftest.py (see test_chat.py's docstring for why). Aggregation
correctness itself is backend/ai/test_analytics.py's job (10 tests
against an isolated DB where every source table is easy to control) —
this file is about the route layer: auth/admin gating, date parsing, and
one real end-to-end call to confirm the wiring in server.py actually
works, not a second copy of the aggregation tests.

Run: pytest test_prompt_usage.py -v
"""
import os

import pytest

import server
from server import User
from backend.ai.model_registry import CostLedgerEntry

ROUTES = [
    "/api/prompt-usage",
    "/api/prompt-usage/by-prompt",
    "/api/prompt-usage/by-model",
    "/api/prompt-usage/by-user",
]


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    return server.app.test_client()


@pytest.fixture
def users(db):
    admin = User(email=f"admin-{os.urandom(4).hex()}@example.com", name="Admin", auth_provider="dev", is_admin=True)
    plain = User(email=f"plain-{os.urandom(4).hex()}@example.com", name="Plain", auth_provider="dev", is_admin=False)
    db.add_all([admin, plain])
    db.commit()
    yield {"admin": admin, "plain": plain}
    db.delete(admin)
    db.delete(plain)
    db.commit()


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ------------------------------------------------------------ auth gating, all 4 routes
@pytest.mark.parametrize("route", ROUTES)
def test_requires_login(client, route):
    resp = client.get(route)
    assert resp.status_code == 401


@pytest.mark.parametrize("route", ROUTES)
def test_requires_admin(client, users, route):
    _login(client, users["plain"].id)
    resp = client.get(route)
    assert resp.status_code == 403


@pytest.mark.parametrize("route", ROUTES)
def test_admin_can_access(client, users, route):
    _login(client, users["admin"].id)
    resp = client.get(route)
    assert resp.status_code == 200, resp.get_json()


# ------------------------------------------------------------ date parsing
def test_invalid_date_returns_400(client, users):
    _login(client, users["admin"].id)
    resp = client.get("/api/prompt-usage?start_date=not-a-date")
    assert resp.status_code == 400


def test_defaults_to_trailing_30_days_when_no_dates_given(client, users):
    _login(client, users["admin"].id)
    resp = client.get("/api/prompt-usage")
    body = resp.get_json()
    assert "start_date" in body
    assert "end_date" in body


# ------------------------------------------------------------ end-to-end wiring
def test_by_model_reflects_a_real_cost_ledger_entry(client, db, users):
    _login(client, users["admin"].id)
    entry = CostLedgerEntry(
        user_id=users["admin"].id, model="gpt-4o-mini", action="chat",
        prompt_tokens=10, completion_tokens=5, total_tokens=15, cost=0.001,
    )
    db.add(entry)
    db.commit()

    resp = client.get("/api/prompt-usage/by-model")
    models = {m["model"]: m for m in resp.get_json()["models"]}
    assert "gpt-4o-mini" in models
    assert models["gpt-4o-mini"]["calls"] >= 1

    db.delete(entry)
    db.commit()


def test_summary_totals_match_by_model_breakdown(client, db, users):
    _login(client, users["admin"].id)
    entry = CostLedgerEntry(
        user_id=users["admin"].id, model="gpt-4o-mini", action="chat",
        prompt_tokens=10, completion_tokens=5, total_tokens=15, cost=0.005,
    )
    db.add(entry)
    db.commit()

    summary = client.get("/api/prompt-usage").get_json()
    by_model = client.get("/api/prompt-usage/by-model").get_json()["models"]

    assert summary["calls"] == sum(m["calls"] for m in by_model)
    assert summary["cost_usd"] == pytest.approx(sum(m["cost_usd"] for m in by_model))

    db.delete(entry)
    db.commit()
