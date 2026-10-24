def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "data_loaded": False}


def test_cors_allows_vercel_preview(client):
    resp = client.get("/api/health", headers={"Origin": "https://foo-git-main.vercel.app"})
    assert resp.headers["access-control-allow-origin"] == "https://foo-git-main.vercel.app"
