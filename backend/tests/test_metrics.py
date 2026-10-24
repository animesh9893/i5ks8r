import asyncio
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.config import Settings
from app.data.store import DataStore
from app.services import forecast_selection as fs
from app.services import metrics as m


def paired(forecast, actual, start="2026-01-10T00:00Z", horizon=None) -> pd.DataFrame:
    n = len(forecast)
    df = pd.DataFrame(
        {
            "start_time": pd.date_range(start, periods=n, freq="h"),
            "forecast_mw": np.array(forecast, dtype=float),
            "actual_mw": np.array(actual, dtype=float),
            "horizon_h": np.array(horizon if horizon is not None else [1.0] * n, dtype=float),
        }
    )
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    return df


def test_summary_matches_hand_calculation():
    # errors: +100, −100, 0 ; the NaN-forecast row is ignored
    s = m.summary(paired([1100, 900, 1000, None], [1000, 1000, 1000, 1000]))
    assert s["n"] == 3
    assert s["mae"] == pytest.approx(200 / 3)
    assert s["rmse"] == pytest.approx(math.sqrt(20000 / 3))
    assert s["bias"] == pytest.approx(0)
    assert s["nmae"] == pytest.approx((200 / 3) / 1000)
    assert s["mape"] == pytest.approx((0.1 + 0.1 + 0) / 3)
    assert s["max_abs_error"] == 100
    assert s["p50_abs_error"] == 100


def test_summary_bias_sign_is_forecast_minus_actual():
    assert m.summary(paired([120, 130], [100, 100]))["bias"] == 25


def test_summary_mape_skips_low_output_hours():
    s = m.summary(paired([200, 1100], [100, 1000]))
    assert s["mape"] == pytest.approx(0.1)  # the 100 MW hour (100 % error) is excluded


def test_summary_empty_is_all_none():
    s = m.summary(paired([None], [100]))
    assert s["n"] == 0 and s["mae"] is None and s["correlation"] is None


def test_by_hour_groups_on_uk_local_hour():
    # 24 h in July → UTC 00:00 is 01:00 BST
    df = paired([110] * 24, [100] * 24, start="2026-07-10T00:00Z")
    out = m.by_hour(df)
    assert len(out) == 24
    assert out[1] == {"hour_local": 1, "mae": 10, "bias": 10, "n": 1}
    assert m.by_hour(paired([None], [1])) == []


def test_distribution_counts_and_quantiles():
    d = m.distribution(paired([110, 90, 100, 100], [100] * 4), bins=2)
    assert sum(b["count"] for b in d["bins"]) == 4
    assert d["bins"][0]["start"] == -10 and d["bins"][-1]["end"] == 10
    assert d["quantiles"]["p50"] == 0
    assert m.distribution(paired([None], [1]))["bins"] == []


def test_by_horizon_uses_latest_forecast_and_reports_coverage():
    fc = pd.DataFrame(
        {
            "publish_time": pd.to_datetime(["2026-01-10T00:00Z", "2026-01-10T04:00Z"]),
            "start_time": pd.to_datetime(["2026-01-10T05:00Z", "2026-01-10T05:00Z"]),
            "forecast_mw": [150.0, 110.0],
        }
    )
    fc["horizon_h"] = (fc["start_time"] - fc["publish_time"]).dt.total_seconds() / 3600
    acts = pd.DataFrame({"start_time": pd.to_datetime(["2026-01-10T05:00Z"]), "actual_mw": [100.0]})
    start, end = pd.Timestamp("2026-01-10T05:00Z"), pd.Timestamp("2026-01-10T07:00Z")
    rows = m.by_horizon(fc, acts, start, end, [1, 3, 6])
    assert [r["mae"] for r in rows] == [10, 50, None]
    assert [r["coverage"] for r in rows] == [0.5, 0.5, 0]


def test_error_quantiles_bucket_residuals_by_horizon():
    # residual = actual − forecast; horizons 1 h → bucket [0,6), 7 h → [6,12)
    df = paired([100, 100, 100, 100], [90, 110, 130, 70], horizon=[1, 1, 7, 7])
    qt = m.error_quantiles_by_horizon_bucket(df, buckets=(0, 6, 12), quantiles=(0.5,))
    assert qt["n"].tolist() == [2, 2]
    assert qt["q50"].tolist() == [0, 0]
    qt = m.error_quantiles_by_horizon_bucket(df, buckets=(0, 6, 12), quantiles=(0.0, 1.0))
    assert qt[["q00", "q100"]].values.tolist() == [[-10, 10], [-30, 30]]


def test_apply_band_offsets_forecast_by_bucket_and_clips_at_zero():
    qt = pd.DataFrame(
        {
            "bucket_lo": [0.0, 6.0],
            "bucket_hi": [6.0, 12.0],
            "n": [10, 10],
            "q10": [-50.0, -200.0],
            "q50": [0.0, 0.0],
            "q90": [50.0, 200.0],
        }
    )
    rows = pd.DataFrame({"forecast_mw": [100.0, 100.0, 100.0], "horizon_h": [1.0, 7.0, 99.0]})
    out = m.apply_band(rows, qt)
    assert out["p10_mw"].tolist()[:2] == [50, 0]  # 100 − 200 clipped to 0
    assert out["p90_mw"].tolist()[:2] == [150, 300]
    assert math.isnan(out["p90_mw"].iloc[2])  # horizon outside every bucket → no band


def test_day_ahead_summary():
    rows = pd.DataFrame(
        {
            "forecast_mw": [100.0, 300.0, 200.0],
            "p10_mw": [50.0, 250.0, 150.0],
            "p90_mw": [150.0, 350.0, 250.0],
            "actual_mw": [120.0, 400.0, None],
        }
    )
    s = m.day_ahead_summary(rows)
    assert s["expected_energy_mwh"] == 600
    assert s["p10_energy_mwh"] == 450
    assert s["max_ramp_mw_per_h"] == 200
    assert s["realised_mae_mw"] == 60  # (20 + 100) / 2
    assert s["hours_in_band"] == 1 and s["hours_with_actual"] == 2
    assert m.day_ahead_summary(rows.iloc[0:0])["expected_energy_mwh"] is None


# --- sanity checks on the committed January snapshot ---------------------------------------------


@pytest.fixture(scope="module")
def january():
    store = DataStore(Settings(data_source="snapshot", _env_file=None))
    asyncio.run(store.load())
    return store.forecasts, store.actuals


def test_january_error_grows_with_horizon(january):
    forecasts, actuals = january
    start, end = pd.Timestamp("2026-01-01T00:00Z"), pd.Timestamp("2026-02-01T00:00Z")
    rows = m.by_horizon(forecasts, actuals, start, end, [1, 12, 24, 36])
    maes = [r["mae"] for r in rows]
    assert maes == sorted(maes)
    assert all(r["coverage"] == 1 for r in rows)


def test_january_day_ahead_covers_every_delivery_hour(january):
    forecasts, actuals = january
    da = fs.day_ahead_series(forecasts, actuals, date(2026, 1, 2), date(2026, 2, 1), "11:00")
    assert len(da) == 31 * 24
    assert da["actual_mw"].notna().all()
    assert da["horizon_h"].between(12, 38).all()
