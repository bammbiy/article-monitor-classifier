"""Basic API contract tests. Doesn't hit Claude or the network — only
checks routes that don't require an API key."""

from fastapi.testclient import TestClient

from article_judge.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_criteria_returns_file_content():
    resp = client.get("/api/criteria")
    assert resp.status_code == 200
    assert "Collect" in resp.json()["content"]


def test_update_and_restore_criteria():
    original = client.get("/api/criteria").json()["content"]
    try:
        resp = client.put("/api/criteria", json={"content": "# Test criteria"})
        assert resp.status_code == 200
        assert client.get("/api/criteria").json()["content"] == "# Test criteria"
    finally:
        client.put("/api/criteria", json={"content": original})
