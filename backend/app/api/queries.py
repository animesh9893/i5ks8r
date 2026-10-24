"""Compose the pure services into the datasets each endpoint needs, memoised per data load."""

from datetime import date, timedelta

import pandas as pd

from app.api.deps import TimeWindow
from app.data.store import DataStore
from app.services import forecast_selection as fs
from app.services import metrics


def paired(
    store: DataStore,
    window: TimeWindow,
    horizon_hours: float | None,
    gate_local: str,
    delivery: tuple[date, date],
) -> pd.DataFrame:
    """Paired forecast/actual rows for the window.

    horizon_hours set → latest forecast at that horizon for every hourly target.
    horizon_hours None → day-ahead mode: each target uses the run available at its D−1 gate,
    restricted to the in-scope delivery days `delivery` = (first, last).
    """
    if horizon_hours is not None:
        key = ("series", window.start, window.end, horizon_hours)
        return store.cached(
            key,
            lambda: fs.series_at_horizon(
                store.forecasts, store.actuals, window.start, window.end, horizon_hours
            ),
        )

    def day_ahead_window() -> pd.DataFrame:
        first = max(window.start.tz_convert(fs.UK_TZ).date(), delivery[0])
        last = min(
            (window.end - pd.Timedelta(microseconds=1)).tz_convert(fs.UK_TZ).date(), delivery[1]
        )
        rows = fs.day_ahead_series(store.forecasts, store.actuals, first, last, gate_local)
        in_window = (rows["start_time"] >= window.start) & (rows["start_time"] < window.end)
        return rows[in_window].reset_index(drop=True)

    return store.cached(
        ("day_ahead_series", window.start, window.end, gate_local, delivery), day_ahead_window
    )


def quantile_table(store: DataStore, known_before: pd.Timestamp | None = None) -> pd.DataFrame:
    """Residual quantiles per horizon bucket.

    known_before=None uses all of January (in-sample). Otherwise only pairs whose actual was
    already settled by `known_before` are used, so a band never uses information from the future.
    """
    pairs = store.cached("all_pairs", lambda: fs.all_pairs(store.forecasts, store.actuals))
    if known_before is None:
        return store.cached(
            "quantiles_in_sample", lambda: metrics.error_quantiles_by_horizon_bucket(pairs)
        )
    settled = pairs["start_time"] + pd.Timedelta(minutes=30) <= known_before
    return store.cached(
        ("quantiles_before", known_before),
        lambda: metrics.error_quantiles_by_horizon_bucket(pairs[settled]),
    )


def day_ahead(
    store: DataStore, delivery_date: date, gate_local: str, leakage_free: bool
) -> tuple[pd.Timestamp, pd.Timestamp | None, pd.DataFrame]:
    """(gate_utc, publish_time, rows with p10/p50/p90 and actual) for one delivery day."""
    gate = fs.day_ahead_gate_utc(delivery_date, gate_local)
    publish_time, rows = fs.day_ahead_forecast(store.forecasts, delivery_date, gate_local)
    rows = fs.pair_with_actuals(rows, store.actuals)
    table = quantile_table(store, gate if leakage_free else None)
    return gate, publish_time, metrics.apply_band(rows, table)


def delivery_dates(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]
