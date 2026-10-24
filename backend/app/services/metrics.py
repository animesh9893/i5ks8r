"""Forecast accuracy metrics. See docs/plan/08-analysis.md for definitions.

Inputs are "paired" frames from forecast_selection (start_time, forecast_mw, actual_mw, error_mw,
horizon_h). Rows missing either a forecast or an actual are ignored; `n` always reports how many
rows were used. Outputs are plain dicts / frames with None instead of NaN so they serialise to JSON.
"""

import math
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
import pandas as pd

from app.services.forecast_selection import UK_TZ, forecast_at_horizon, hourly_targets

# Below this output, percentage errors are meaningless (division by a near-zero actual).
MAPE_MIN_ACTUAL_MW = 500.0

# Horizon buckets (hours) used to fit error quantiles for uncertainty bands.
DEFAULT_HORIZON_BUCKETS: tuple[float, ...] = (0, 6, 12, 18, 24, 30, 36, 42, 48, 72)
DEFAULT_QUANTILES: tuple[float, ...] = (0.1, 0.5, 0.9)


def _num(x: Any) -> float | None:
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else x


def _valid(paired: pd.DataFrame) -> pd.DataFrame:
    return paired.dropna(subset=["forecast_mw", "actual_mw"])


def summary(paired: pd.DataFrame) -> dict[str, float | int | None]:
    """Headline accuracy metrics over all valid rows."""
    v = _valid(paired)
    n = len(v)
    keys = (
        "mae rmse bias nmae mape p50_abs_error p90_abs_error p99_abs_error max_abs_error "
        "correlation"
    ).split()
    if n == 0:
        return {"n": 0, **dict.fromkeys(keys)}

    err = v["forecast_mw"] - v["actual_mw"]
    abs_err = err.abs()
    mean_actual = v["actual_mw"].mean()
    mape_rows = v[v["actual_mw"] >= MAPE_MIN_ACTUAL_MW]
    mape = (
        ((mape_rows["forecast_mw"] - mape_rows["actual_mw"]).abs() / mape_rows["actual_mw"]).mean()
        if len(mape_rows)
        else None
    )
    constant = v["forecast_mw"].nunique() < 2 or v["actual_mw"].nunique() < 2
    corr = None if constant else v["forecast_mw"].corr(v["actual_mw"])
    return {
        "n": n,
        "mae": _num(abs_err.mean()),
        "rmse": _num(math.sqrt((err**2).mean())),
        "bias": _num(err.mean()),
        "nmae": _num(abs_err.mean() / mean_actual) if mean_actual else None,
        "mape": _num(mape),
        "p50_abs_error": _num(abs_err.quantile(0.5)),
        "p90_abs_error": _num(abs_err.quantile(0.9)),
        "p99_abs_error": _num(abs_err.quantile(0.99)),
        "max_abs_error": _num(abs_err.max()),
        "correlation": _num(corr),
    }


def by_horizon(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    horizons: Iterable[float],
) -> list[dict[str, float | int | None]]:
    """Accuracy of the latest-forecast-at-horizon, for each requested horizon."""
    targets = hourly_targets(start, end)
    rows = []
    for h in horizons:
        selected = forecast_at_horizon(forecasts, targets, h)
        paired = selected.merge(actuals, on="start_time", how="left")
        s = summary(paired)
        rows.append(
            {
                "horizon_hours": h,
                "n": s["n"],
                "coverage": s["n"] / len(targets) if len(targets) else None,
                "mae": s["mae"],
                "rmse": s["rmse"],
                "bias": s["bias"],
                "p90_abs_error": s["p90_abs_error"],
            }
        )
    return rows


def by_hour(paired: pd.DataFrame) -> list[dict[str, float | int | None]]:
    """MAE and bias by UK-local hour of the target time (0–23)."""
    v = _valid(paired)
    if v.empty:
        return []
    err = v["forecast_mw"] - v["actual_mw"]
    hour = v["start_time"].dt.tz_convert(UK_TZ).dt.hour
    grouped = pd.DataFrame({"hour_local": hour, "err": err, "abs": err.abs()}).groupby("hour_local")
    stats = grouped.agg(mae=("abs", "mean"), bias=("err", "mean"), n=("err", "size"))
    return [
        {"hour_local": int(h), "mae": _num(r.mae), "bias": _num(r.bias), "n": int(r.n)}
        for h, r in stats.iterrows()
    ]


def distribution(paired: pd.DataFrame, bins: int = 40) -> dict[str, Any]:
    """Histogram of error_mw (forecast − actual) plus P5/P50/P95."""
    v = _valid(paired)
    if v.empty:
        return {"bins": [], "quantiles": {"p05": None, "p50": None, "p95": None}}
    err = (v["forecast_mw"] - v["actual_mw"]).to_numpy()
    counts, edges = np.histogram(err, bins=bins)
    return {
        "bins": [
            {"start": float(edges[i]), "end": float(edges[i + 1]), "count": int(counts[i])}
            for i in range(len(counts))
        ],
        "quantiles": {
            "p05": _num(np.quantile(err, 0.05)),
            "p50": _num(np.quantile(err, 0.5)),
            "p95": _num(np.quantile(err, 0.95)),
        },
    }


# ---------------------------------------------------------------------------------------------
# Uncertainty bands
# ---------------------------------------------------------------------------------------------


def _q_col(q: float) -> str:
    return f"q{round(q * 100):02d}"


def error_quantiles_by_horizon_bucket(
    pairs: pd.DataFrame,
    buckets: Sequence[float] = DEFAULT_HORIZON_BUCKETS,
    quantiles: Sequence[float] = DEFAULT_QUANTILES,
) -> pd.DataFrame:
    """Quantiles of the residual (actual − forecast) per horizon bucket [lo, hi).

    `pairs` should hold every (publish, target) forecast with its actual (forecast_selection.
    all_pairs). Adding a quantile of the residual to a forecast gives that quantile of the outcome.
    Returns columns: bucket_lo, bucket_hi, n, q10, q50, q90 (for the default quantiles).
    """
    v = _valid(pairs)
    residual = v["actual_mw"] - v["forecast_mw"]
    bucket = pd.cut(v["horizon_h"], bins=list(buckets), right=False)
    rows = []
    for interval in bucket.cat.categories:
        r = residual[bucket == interval]
        row: dict[str, Any] = {
            "bucket_lo": float(interval.left),
            "bucket_hi": float(interval.right),
            "n": len(r),
        }
        for q in quantiles:
            row[_q_col(q)] = float(r.quantile(q)) if len(r) else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def apply_band(
    rows: pd.DataFrame,
    quantile_table: pd.DataFrame,
    quantiles: Sequence[float] = DEFAULT_QUANTILES,
) -> pd.DataFrame:
    """Add p10_mw/p50_mw/p90_mw = forecast + residual quantile for the row's horizon (≥ 0)."""
    out = rows.copy()
    edges = [*quantile_table["bucket_lo"], quantile_table["bucket_hi"].iloc[-1]]
    idx = pd.cut(out["horizon_h"], bins=edges, right=False, labels=False)
    for q in quantiles:
        offsets = quantile_table[_q_col(q)].to_numpy()
        offset = idx.map(lambda i, o=offsets: o[int(i)] if pd.notna(i) else math.nan)
        out[f"p{round(q * 100)}_mw"] = (out["forecast_mw"] + offset.astype(float)).clip(lower=0)
    return out


def day_ahead_summary(rows: pd.DataFrame) -> dict[str, float | int | None]:
    """KPIs for one delivery day. `rows` are hourly, with forecast/p10/p90 and maybe actual_mw."""
    if rows.empty:
        return dict.fromkeys(
            "expected_energy_mwh p10_energy_mwh p90_energy_mwh peak_forecast_mw min_forecast_mw "
            "max_ramp_mw_per_h realised_mae_mw hours_in_band hours_with_actual".split()
        )
    # Hourly MW values → MWh per hour.
    forecast = rows["forecast_mw"]
    ramp = forecast.diff().abs().max() if len(rows) > 1 else 0.0
    has_actual = rows.dropna(subset=["actual_mw"]) if "actual_mw" in rows else rows.iloc[0:0]
    in_band = None
    if len(has_actual) and {"p10_mw", "p90_mw"} <= set(rows.columns):
        in_band = int(
            (
                (has_actual["actual_mw"] >= has_actual["p10_mw"])
                & (has_actual["actual_mw"] <= has_actual["p90_mw"])
            ).sum()
        )
    return {
        "expected_energy_mwh": _num(forecast.sum()),
        "p10_energy_mwh": _num(rows["p10_mw"].sum(min_count=1)) if "p10_mw" in rows else None,
        "p90_energy_mwh": _num(rows["p90_mw"].sum(min_count=1)) if "p90_mw" in rows else None,
        "peak_forecast_mw": _num(forecast.max()),
        "min_forecast_mw": _num(forecast.min()),
        "max_ramp_mw_per_h": _num(ramp),
        "realised_mae_mw": _num((has_actual["forecast_mw"] - has_actual["actual_mw"]).abs().mean())
        if len(has_actual)
        else None,
        "hours_in_band": in_band,
        "hours_with_actual": len(has_actual),
    }
