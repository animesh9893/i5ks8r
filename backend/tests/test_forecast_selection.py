from datetime import date, time

import pandas as pd
import pytest

from app.data.store import normalise_actuals, normalise_forecasts
from app.services import forecast_selection as fs


def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


@pytest.fixture
def forecasts() -> pd.DataFrame:
    """Three runs on 10 Jan (00:30, 02:30, 04:30) each forecasting 05:00 and 06:00.

    Values encode the run: run 1 → 100/110, run 2 → 200/210, run 3 → 300/310.
    """
    runs = {"00:30": 100, "02:30": 200, "04:30": 300}
    records = [
        {
            "publishTime": f"2026-01-10T{pub}:00Z",
            "startTime": f"2026-01-10T0{5 + i}:00:00Z",
            "generation": base + 10 * i,
        }
        for pub, base in runs.items()
        for i in range(2)
    ]
    return normalise_forecasts(records)


@pytest.fixture
def actuals() -> pd.DataFrame:
    return normalise_actuals(
        [
            {
                "publishTime": "2026-01-15T00:30:00Z",
                "startTime": "2026-01-10T05:00:00Z",
                "generation": 250,
            },
            {
                "publishTime": "2026-01-15T00:30:00Z",
                "startTime": "2026-01-10T05:30:00Z",
                "generation": 999,
            },
            {
                "publishTime": "2026-01-15T00:30:00Z",
                "startTime": "2026-01-10T06:00:00Z",
                "generation": 260,
            },
        ]
    )


TARGETS = pd.DatetimeIndex([ts("2026-01-10T05:00"), ts("2026-01-10T06:00")], name="start_time")


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [
        (0, [300, 310]),  # latest run before each target
        (1, [200, 310]),  # 05:00 cutoff 04:00 → run 2; 06:00 cutoff 05:00 → run 3
        (2.5, [200, 210]),  # 05:00 cutoff 02:30 == run 2 publish time (inclusive)
        (3, [100, 210]),
        (5, [None, 110]),  # nothing published before 00:00 for 05:00
        (10, [None, None]),
    ],
)
def test_forecast_at_horizon_picks_latest_run_before_cutoff(forecasts, horizon, expected):
    out = fs.forecast_at_horizon(forecasts, TARGETS, horizon)
    got = [None if pd.isna(v) else v for v in out["forecast_mw"]]
    assert got == expected
    assert out["start_time"].tolist() == list(TARGETS)


def test_forecast_at_horizon_reports_real_lead_time(forecasts):
    out = fs.forecast_at_horizon(forecasts, TARGETS, 1)
    assert out["publish_time"].tolist() == [ts("2026-01-10T02:30"), ts("2026-01-10T04:30")]
    assert out["horizon_h"].tolist() == [2.5, 1.5]
    assert (out["horizon_h"] >= 1).all()


def test_series_at_horizon_pairs_hourly_actual_and_error(forecasts, actuals):
    out = fs.series_at_horizon(
        forecasts, actuals, ts("2026-01-10T05:00"), ts("2026-01-10T07:00"), 0
    )
    assert list(out.columns) == fs.PAIRED_COLUMNS
    # Only hourly targets; the 05:30 actual is never used.
    assert out["actual_mw"].tolist() == [250, 260]
    assert out["error_mw"].tolist() == [50, 50]  # forecast − actual


def test_hourly_targets_is_half_open_and_rounds_up():
    t = fs.hourly_targets(ts("2026-01-10T04:30"), ts("2026-01-10T07:00"))
    assert [x.hour for x in t] == [5, 6]


def test_all_pairs_keeps_every_run_with_an_actual(forecasts, actuals):
    pairs = fs.all_pairs(forecasts, actuals)
    assert len(pairs) == 6
    assert sorted(pairs["error_mw"].tolist()) == [-150, -150, -50, -50, 50, 50]


# --- day-ahead ---------------------------------------------------------------------------------


def test_gate_in_winter_is_utc():
    assert fs.day_ahead_gate_utc(date(2026, 1, 15), "11:00") == ts("2026-01-14T11:00")


def test_gate_in_summer_converts_from_bst():
    assert fs.day_ahead_gate_utc(date(2026, 7, 15), time(11)) == ts("2026-07-14T10:00")


def test_delivery_day_bounds_handle_clock_change():
    start, end = fs.delivery_day_bounds_utc(date(2026, 3, 29))  # spring forward: 23 h day
    assert start == ts("2026-03-29T00:00") and end == ts("2026-03-29T23:00")
    start, end = fs.delivery_day_bounds_utc(date(2026, 7, 15))
    assert start == ts("2026-07-14T23:00")


@pytest.fixture
def day_ahead_forecasts() -> pd.DataFrame:
    """Runs at 09:30 and 11:30 on 14 Jan, each covering 14 Jan 12:00 → 16 Jan 02:00 hourly."""
    records = []
    for pub, value in (("09:30", 1000), ("11:30", 2000)):
        for t in pd.date_range("2026-01-14T12:00Z", "2026-01-16T02:00Z", freq="h"):
            records.append(
                {
                    "publishTime": f"2026-01-14T{pub}:00Z",
                    "startTime": t.isoformat(),
                    "generation": value,
                }
            )
    return normalise_forecasts(records)


def test_day_ahead_uses_last_run_before_gate_and_only_delivery_day(day_ahead_forecasts):
    pub, rows = fs.day_ahead_forecast(day_ahead_forecasts, date(2026, 1, 15), "11:00")
    assert pub == ts("2026-01-14T09:30")
    assert len(rows) == 24
    assert rows["start_time"].iloc[0] == ts("2026-01-15T00:00")
    assert rows["start_time"].iloc[-1] == ts("2026-01-15T23:00")
    assert set(rows["forecast_mw"]) == {1000}
    assert rows["horizon_h"].iloc[0] == 14.5


def test_day_ahead_later_gate_picks_later_run(day_ahead_forecasts):
    pub, rows = fs.day_ahead_forecast(day_ahead_forecasts, date(2026, 1, 15), "12:00")
    assert pub == ts("2026-01-14T11:30")
    assert set(rows["forecast_mw"]) == {2000}


def test_day_ahead_without_any_earlier_run(day_ahead_forecasts):
    pub, rows = fs.day_ahead_forecast(day_ahead_forecasts, date(2026, 1, 14), "11:00")
    assert pub is None and rows.empty


def test_day_ahead_series_concatenates_days_and_skips_missing(day_ahead_forecasts):
    acts = normalise_actuals(
        [
            {
                "publishTime": "2026-01-15T00:30:00Z",
                "startTime": "2026-01-15T00:00:00Z",
                "generation": 900,
            }
        ]
    )
    out = fs.day_ahead_series(
        day_ahead_forecasts, acts, date(2026, 1, 14), date(2026, 1, 16), "11:00"
    )
    # 14 Jan has no run before its gate; 16 Jan's gate (15 Jan 11:00) sees the 14 Jan 11:30 run,
    # which only reaches 16 Jan 02:00.
    assert len(out) == 24 + 3
    assert out["error_mw"].iloc[0] == 100
    assert out["actual_mw"].isna().sum() == 26


def test_day_ahead_series_empty(day_ahead_forecasts, actuals):
    out = fs.day_ahead_series(
        day_ahead_forecasts, actuals, date(2026, 1, 1), date(2026, 1, 2), "11:00"
    )
    assert out.empty and list(out.columns) == fs.PAIRED_COLUMNS
