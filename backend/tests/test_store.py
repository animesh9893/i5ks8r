import pandas as pd
import pytest

from app.data.store import (
    DataStore,
    normalise_actuals,
    normalise_forecasts,
    read_snapshot,
    write_snapshot,
)


def test_normalise_actuals_keeps_latest_revision(raw_actuals):
    df = normalise_actuals(raw_actuals)
    assert list(df.columns) == ["start_time", "actual_mw"]
    assert df["actual_mw"].tolist() == [1100.0, 1200.0]
    assert str(df["start_time"].dt.tz) == "UTC"


def test_normalise_actuals_ignores_other_fuels(raw_actuals):
    raw = raw_actuals + [
        {"publishTime": "2026-01-01T01:00:00Z", "startTime": "2026-01-01T00:30:00Z",
         "fuelType": "CCGT", "generation": 9999}
    ]  # fmt: skip
    assert 9999 not in normalise_actuals(raw)["actual_mw"].tolist()


def test_normalise_forecasts_drops_negative_horizons_and_computes_horizon(raw_forecasts):
    df = normalise_forecasts(raw_forecasts)
    assert df["start_time"].dt.hour.tolist() == [3, 4]
    assert df["horizon_h"].tolist() == [0.5, 1.5]


def test_normalise_empty(empty_frames):
    actuals, forecasts = empty_frames
    assert actuals.empty and forecasts.empty
    assert "horizon_h" in forecasts.columns


def test_snapshot_round_trip(tmp_path, raw_actuals, raw_forecasts):
    write_snapshot(raw_actuals, raw_forecasts, tmp_path)
    actuals, forecasts = read_snapshot(tmp_path)
    pd.testing.assert_frame_equal(normalise_actuals(actuals), normalise_actuals(raw_actuals))
    pd.testing.assert_frame_equal(
        normalise_forecasts(forecasts), normalise_forecasts(raw_forecasts)
    )


class FailingClient:
    async def fetch_actuals(self, *_):
        raise ConnectionError("elexon down")

    async def fetch_forecasts(self, *_):
        return []


class FakeClient:
    def __init__(self, actuals, forecasts):
        self._a, self._f = actuals, forecasts

    async def fetch_actuals(self, *_):
        return self._a

    async def fetch_forecasts(self, *_):
        return self._f


async def test_live_load(settings, raw_actuals, raw_forecasts, tmp_path):
    settings.data_source = "live"
    store = DataStore(settings, FakeClient(raw_actuals, raw_forecasts), snapshot_dir=tmp_path)
    await store.load()
    assert store.is_loaded and store.source == "live"
    assert len(store.forecasts) == 2


async def test_live_failure_falls_back_to_snapshot(settings, raw_actuals, raw_forecasts, tmp_path):
    write_snapshot(raw_actuals, raw_forecasts, tmp_path)
    settings.data_source = "live"
    store = DataStore(settings, FailingClient(), snapshot_dir=tmp_path)
    await store.load()
    assert store.source == "snapshot"
    assert "elexon down" in store.last_error
    assert len(store.actuals) == 2


async def test_live_empty_response_falls_back_to_snapshot(settings, raw_actuals, tmp_path):
    write_snapshot(raw_actuals, [], tmp_path)
    settings.data_source = "live"
    store = DataStore(settings, FakeClient(raw_actuals, []), snapshot_dir=tmp_path)
    await store.load()
    assert store.source == "snapshot"


async def test_snapshot_mode_never_calls_client(settings, raw_actuals, raw_forecasts, tmp_path):
    write_snapshot(raw_actuals, raw_forecasts, tmp_path)
    store = DataStore(settings, FailingClient(), snapshot_dir=tmp_path)
    await store.load()
    assert store.source == "snapshot" and store.last_error is None


async def test_committed_snapshot_is_loadable(settings):
    store = DataStore(settings)
    await store.load()
    assert store.source == "snapshot"
    assert len(store.actuals) >= 1488  # 31 days × 48 periods
    assert (store.forecasts["horizon_h"] >= 0).all()


@pytest.mark.parametrize("missing", ["fuelhh_wind.json.gz", "windfor.json.gz"])
async def test_missing_snapshot_raises(settings, raw_actuals, raw_forecasts, tmp_path, missing):
    write_snapshot(raw_actuals, raw_forecasts, tmp_path)
    (tmp_path / missing).unlink()
    store = DataStore(settings, FailingClient(), snapshot_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        await store.load()
    assert not store.is_loaded
