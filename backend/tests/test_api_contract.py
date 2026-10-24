"""Contract tests for every endpoint, run against the committed January 2026 snapshot."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data.store import DataStore
from app.main import create_app

JAN = {"start": "2026-01-01T00:00:00Z", "end": "2026-02-01T00:00:00Z"}


@pytest.fixture(scope="module")
def snapshot_store() -> DataStore:
    store = DataStore(Settings(data_source="snapshot", _env_file=None))
    asyncio.run(store.load())
    return store


@pytest.fixture
def api(snapshot_store) -> TestClient:
    settings = Settings(data_source="snapshot", admin_token="secret", _env_file=None)
    with TestClient(create_app(settings, snapshot_store)) as c:
        yield c


def test_meta(api):
    body = api.get("/api/meta").json()
    assert body["source"] == "snapshot"
    assert body["actuals"]["from"] == "2026-01-01T00:00:00Z"
    assert body["actuals"]["rows"] == 1584
    assert body["forecasts"]["publishes"] == 272
    assert "09:30" in body["forecasts"]["publish_times_per_day_utc"]
    assert body["delivery_dates"] == {"first": "2026-01-02", "last": "2026-02-01"}
    assert body["default_window"] == {"start": JAN["start"], "end": JAN["end"]}


def test_series_defaults_to_january_at_4h(api):
    body = api.get("/api/series").json()
    assert body["horizon_hours"] == 4
    assert len(body["points"]) == 31 * 24
    assert len(body["actuals_30min"]) == 31 * 48
    p = body["points"][0]
    assert p["target_time"] == "2026-01-01T00:00:00Z"
    assert p["horizon_actual_hours"] >= 4
    assert p["error_mw"] == pytest.approx(p["forecast_mw"] - p["actual_mw"])


def test_series_returns_nulls_when_no_forecast_is_old_enough(api):
    # The data starts with runs published 29 Dec, so a 48 h horizon on 1 Jan 00:00 has none.
    body = api.get("/api/series", params={**JAN, "horizon_hours": 48}).json()
    missing = [p for p in body["points"] if p["forecast_mw"] is None]
    assert missing and all(p["error_mw"] is None for p in missing)
    assert all(p["forecast_publish_time"] is None for p in missing)


def test_day_ahead(api):
    body = api.get("/api/day-ahead", params={"delivery_date": "2026-01-15"}).json()
    assert body["gate_time_utc"] == "2026-01-14T11:00:00Z"
    assert body["forecast_publish_time"] == "2026-01-14T09:30:00Z"
    assert body["band_method"] == "in_sample"
    assert len(body["points"]) == 24
    p = body["points"][0]
    assert p["p10_mw"] <= p["p50_mw"] <= p["p90_mw"]
    assert p["horizon_hours"] == 14.5
    assert body["summary"]["hours_with_actual"] == 24


def test_day_ahead_leakage_free_band_differs(api):
    params = {"delivery_date": "2026-01-20"}
    in_sample = api.get("/api/day-ahead", params=params).json()
    oos = api.get("/api/day-ahead", params={**params, "leakage_free": True}).json()
    assert oos["band_method"] == "leakage_free"
    assert oos["points"][0]["forecast_mw"] == in_sample["points"][0]["forecast_mw"]
    assert oos["points"][0]["p10_mw"] != in_sample["points"][0]["p10_mw"]


def test_day_ahead_custom_gate(api):
    body = api.get("/api/day-ahead", params={"delivery_date": "2026-01-15", "gate_local": "12:00"})
    assert body.json()["forecast_publish_time"] == "2026-01-14T11:30:00Z"


def test_metrics_day_ahead_mode_by_default(api):
    body = api.get("/api/metrics").json()
    assert body["mode"] == "day_ahead" and body["horizon_hours"] is None
    # No dates → every delivery day decided in January: 2 Jan – 1 Feb.
    assert (body["start"], body["end"]) == ("2026-01-02T00:00:00Z", "2026-02-02T00:00:00Z")
    assert body["n"] == 31 * 24
    assert 1000 < body["mae"] < 3000
    assert body["bias"] > 0


def test_metrics_day_ahead_mode_excludes_out_of_scope_delivery_days(api):
    # 1 Jan was bought on 31 Dec, so it is not part of the January decisions.
    body = api.get("/api/metrics", params=JAN).json()
    assert body["n"] == 30 * 24


def test_metrics_at_horizon(api):
    body = api.get("/api/metrics", params={"horizon_hours": 1}).json()
    assert body["mode"] == "horizon" and body["n"] == 744


def test_by_horizon(api):
    rows = api.get("/api/metrics/by-horizon", params={"max_h": 48, "step": 12}).json()
    assert [r["horizon_hours"] for r in rows] == [0, 12, 24, 36, 48]
    assert rows[0]["coverage"] == 1 and rows[-1]["coverage"] < 1
    assert rows[0]["mae"] < rows[-1]["mae"]


def test_by_hour(api):
    rows = api.get("/api/metrics/by-hour", params={"horizon_hours": 4}).json()
    assert [r["hour_local"] for r in rows] == list(range(24))


def test_distribution(api):
    body = api.get("/api/metrics/distribution", params={"bins": 20}).json()
    assert len(body["bins"]) == 20
    assert sum(b["count"] for b in body["bins"]) == 31 * 24
    assert body["quantiles"]["p05"] < body["quantiles"]["p95"]


@pytest.mark.parametrize(
    ("path", "params", "message"),
    [
        ("/api/series", {"start": "2026-01-10", "end": "2026-01-05"}, "start must be before end"),
        ("/api/series", {"start": "2025-06-01"}, "within data coverage"),
        ("/api/series", {"horizon_hours": 72}, "horizon_hours must be between"),
        ("/api/metrics", {"horizon_hours": -1}, "horizon_hours must be between"),
        ("/api/metrics/by-horizon", {"max_h": 100}, "horizon_hours must be between"),
        ("/api/day-ahead", {"delivery_date": "2026-03-01"}, "delivery_date must be between"),
        ("/api/day-ahead", {"delivery_date": "2026-01-15", "gate_local": "noon"}, "HH:MM"),
    ],
)
def test_validation_errors(api, path, params, message):
    resp = api.get(path, params=params)
    assert resp.status_code == 422
    assert message in resp.json()["detail"]


def test_naive_datetimes_are_utc(api):
    body = api.get("/api/series", params={"start": "2026-01-05T00:00", "end": "2026-01-06T00:00"})
    assert body.json()["points"][0]["target_time"] == "2026-01-05T00:00:00Z"


def test_data_endpoints_503_while_loading(settings):
    class StuckStore(DataStore):
        async def load(self) -> None:
            return None

    with TestClient(create_app(settings, StuckStore(settings))) as c:
        for path in ("/api/meta", "/api/series", "/api/metrics"):
            assert c.get(path).status_code == 503


def test_refresh_requires_token(api):
    assert api.post("/api/admin/refresh").status_code == 401
    assert api.post("/api/admin/refresh", headers={"X-Admin-Token": "nope"}).status_code == 401
    resp = api.post("/api/admin/refresh", headers={"X-Admin-Token": "secret"})
    assert resp.status_code == 200 and resp.json()["source"] == "snapshot"


def test_refresh_disabled_without_token(client):
    assert client.post("/api/admin/refresh").status_code == 404


def test_openapi_lists_every_endpoint(api):
    paths = set(api.get("/openapi.json").json()["paths"])
    assert {
        "/api/health",
        "/api/meta",
        "/api/series",
        "/api/day-ahead",
        "/api/metrics",
        "/api/metrics/by-horizon",
        "/api/metrics/by-hour",
        "/api/metrics/distribution",
        "/api/admin/refresh",
    } <= paths


def test_large_responses_are_gzipped(api):
    resp = api.get("/api/series", headers={"Accept-Encoding": "gzip"})
    assert resp.headers["content-encoding"] == "gzip"
