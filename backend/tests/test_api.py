from fastapi.testclient import TestClient

from app.data.store import DataStore
from app.main import create_app


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "data_loaded": True}


def test_health_reports_not_loaded(settings):
    # A store that never finishes loading: health still answers, data_loaded is false.
    class StuckStore(DataStore):
        async def load(self) -> None:
            return None

    with TestClient(create_app(settings, StuckStore(settings))) as c:
        assert c.get("/api/health").json() == {"status": "ok", "data_loaded": False}


def test_cors_allows_netlify_preview(client):
    resp = client.get(
        "/api/health", headers={"Origin": "https://deploy-preview-1--foo.netlify.app"}
    )
    assert (
        resp.headers["access-control-allow-origin"] == "https://deploy-preview-1--foo.netlify.app"
    )
