"""Tests for GET /api/worker/health — see server.py's worker_health() and
worker.py's _heartbeat(). DATABASE_URL isolation lives in the project's
root conftest.py (see that file / test_chat.py's docstring for why).

Run: pytest test_worker_health.py -v
"""

from datetime import datetime, timedelta, timezone

import pytest

import server
from server import WorkerHeartbeat


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clean_heartbeat(db):
    db.query(WorkerHeartbeat).delete()
    db.commit()
    yield
    db.query(WorkerHeartbeat).delete()
    db.commit()


@pytest.fixture
def client():
    return server.app.test_client()


def test_no_heartbeat_row_reports_unknown(client):
    resp = client.get("/api/worker/health")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "unknown"


def test_fresh_heartbeat_reports_ok(client, db):
    db.add(WorkerHeartbeat(id=1, last_seen_at=datetime.now(timezone.utc)))
    db.commit()

    resp = client.get("/api/worker/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["age_seconds"] < 5


def test_stale_heartbeat_reports_down(client, db):
    stale = datetime.now(timezone.utc) - timedelta(seconds=server.WORKER_HEALTH_THRESHOLD_SECONDS + 30)
    db.add(WorkerHeartbeat(id=1, last_seen_at=stale))
    db.commit()

    resp = client.get("/api/worker/health")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "down"


def test_worker_heartbeat_write_is_read_back_by_the_health_route(client, db):
    """Closes the loop end-to-end: worker.py's own write function (not a
    hand-crafted row) produces a row the health route reads as fresh.
    Doesn't call worker.main() — that requires real Postgres — just the
    heartbeat helper, which has no such requirement."""
    import worker

    worker._heartbeat()

    resp = client.get("/api/worker/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
