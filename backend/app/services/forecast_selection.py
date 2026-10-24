"""Pick which forecast was available at decision time, and pair it with the actual.

Conventions (shared with metrics.py):
- All timestamps are tz-aware UTC; `Europe/London` is used only for day boundaries and the gate.
- error_mw = forecast_mw − actual_mw  (positive = wind over-forecast → utility ends up short).
- Forecasts are hourly; each hourly target is compared with the half-hourly actual starting at the
  same instant (no averaging).
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

UK_TZ = ZoneInfo("Europe/London")

PAIRED_COLUMNS = [
    "start_time",
    "forecast_mw",
    "publish_time",
    "horizon_h",
    "actual_mw",
    "error_mw",
]


def hourly_targets(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Hourly UTC target times in [start, end)."""
    start, end = pd.Timestamp(start).tz_convert("UTC"), pd.Timestamp(end).tz_convert("UTC")
    return pd.date_range(start.ceil("h"), end, freq="h", inclusive="left", name="start_time")


def forecast_at_horizon(
    forecasts: pd.DataFrame, targets: pd.DatetimeIndex, horizon_h: float
) -> pd.DataFrame:
    """For each target t, the latest forecast for t published at or before t − horizon_h.

    Returns one row per target: start_time, forecast_mw, publish_time, horizon_h (the real lead
    time of the chosen forecast, ≥ the requested horizon). Forecast columns are NaN/NaT when no
    forecast for t had been published that early.
    """
    left = pd.DataFrame({"start_time": targets})
    left["cutoff"] = left["start_time"] - pd.Timedelta(hours=horizon_h)
    left = left.sort_values("cutoff")
    right = forecasts[["publish_time", "start_time", "forecast_mw", "horizon_h"]].sort_values(
        "publish_time"
    )
    out = pd.merge_asof(
        left,
        right,
        left_on="cutoff",
        right_on="publish_time",
        by="start_time",
        direction="backward",
        allow_exact_matches=True,
    )
    return (
        out.drop(columns="cutoff")
        .sort_values("start_time")
        .reset_index(drop=True)[["start_time", "forecast_mw", "publish_time", "horizon_h"]]
    )


def pair_with_actuals(selected: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Attach actual_mw and error_mw (forecast − actual) on start_time."""
    out = selected.merge(actuals, on="start_time", how="left")
    out["error_mw"] = out["forecast_mw"] - out["actual_mw"]
    return out


def series_at_horizon(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    horizon_h: float,
) -> pd.DataFrame:
    """Paired actual vs forecast-at-horizon for every hourly target in [start, end)."""
    selected = forecast_at_horizon(forecasts, hourly_targets(start, end), horizon_h)
    return pair_with_actuals(selected, actuals)[PAIRED_COLUMNS]


def all_pairs(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Every (publish, target) forecast row that has an actual. Used to fit error quantiles."""
    out = forecasts.merge(actuals, on="start_time", how="inner")
    out["error_mw"] = out["forecast_mw"] - out["actual_mw"]
    return out


# ---------------------------------------------------------------------------------------------
# Day-ahead
# ---------------------------------------------------------------------------------------------


def parse_gate(gate_local: str | time) -> time:
    return gate_local if isinstance(gate_local, time) else time.fromisoformat(gate_local)


def delivery_day_bounds_utc(delivery_date: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """[start, end) of the UK-local delivery day, in UTC (23/24/25 h long)."""
    start = datetime.combine(delivery_date, time(0), tzinfo=UK_TZ)
    end = datetime.combine(delivery_date + timedelta(days=1), time(0), tzinfo=UK_TZ)
    return pd.Timestamp(start).tz_convert("UTC"), pd.Timestamp(end).tz_convert("UTC")


def day_ahead_gate_utc(delivery_date: date, gate_local: str | time) -> pd.Timestamp:
    """Decision time for delivery day D: gate_local on D−1, UK local time, as UTC."""
    gate = datetime.combine(delivery_date - timedelta(days=1), parse_gate(gate_local), tzinfo=UK_TZ)
    return pd.Timestamp(gate).tz_convert("UTC")


def day_ahead_forecast(
    forecasts: pd.DataFrame, delivery_date: date, gate_local: str | time
) -> tuple[pd.Timestamp | None, pd.DataFrame]:
    """The single forecast run a trader would have had at the D−1 gate, cut to delivery day D.

    Returns (publish_time of that run or None, rows[start_time, forecast_mw, publish_time,
    horizon_h]). Rows are empty when no run was published before the gate.
    """
    gate = day_ahead_gate_utc(delivery_date, gate_local)
    published = forecasts.loc[forecasts["publish_time"] <= gate, "publish_time"]
    if published.empty:
        return None, forecasts.iloc[0:0][["start_time", "forecast_mw", "publish_time", "horizon_h"]]
    latest = published.max()
    day_start, day_end = delivery_day_bounds_utc(delivery_date)
    rows = forecasts[
        (forecasts["publish_time"] == latest)
        & (forecasts["start_time"] >= day_start)
        & (forecasts["start_time"] < day_end)
    ]
    rows = rows[["start_time", "forecast_mw", "publish_time", "horizon_h"]]
    return latest, rows.sort_values("start_time").reset_index(drop=True)


def day_ahead_series(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    first_delivery: date,
    last_delivery: date,
    gate_local: str | time,
) -> pd.DataFrame:
    """Paired day-ahead forecasts for every delivery day in [first_delivery, last_delivery]."""
    frames = []
    day = first_delivery
    while day <= last_delivery:
        _, rows = day_ahead_forecast(forecasts, day, gate_local)
        if not rows.empty:
            frames.append(rows)
        day += timedelta(days=1)
    if not frames:
        empty = forecasts.iloc[0:0][["start_time", "forecast_mw", "publish_time", "horizon_h"]]
        return pair_with_actuals(empty, actuals)[PAIRED_COLUMNS]
    return pair_with_actuals(pd.concat(frames, ignore_index=True), actuals)[PAIRED_COLUMNS]
