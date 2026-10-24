from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated

import pandas as pd
from fastapi import Depends, HTTPException, Query, Request

from app.config import Settings, get_settings
from app.data.store import DataStore
from app.services.forecast_selection import delivery_day_bounds_utc


def get_store(request: Request) -> DataStore:
    """Return the loaded DataStore, or 503 while data is still loading."""
    store: DataStore | None = getattr(request.app.state, "store", None)
    if store is None or not store.is_loaded:
        raise HTTPException(status_code=503, detail="data loading")
    return store


def app_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


StoreDep = Annotated[DataStore, Depends(get_store)]
SettingsDep = Annotated[Settings, Depends(app_settings)]


def _utc(value: datetime | str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def coverage(store: DataStore) -> tuple[pd.Timestamp, pd.Timestamp]:
    """[start, end) of target times that have actuals."""
    starts = store.actuals["start_time"]
    return starts.min(), starts.max() + pd.Timedelta(minutes=30)


@dataclass(frozen=True)
class TimeWindow:
    start: pd.Timestamp
    end: pd.Timestamp
    explicit: bool = True  # False when both bounds came from the defaults


def time_window(
    store: StoreDep,
    settings: SettingsDep,
    start: Annotated[
        datetime | None,
        Query(description="Window start (inclusive), ISO-8601; naive = UTC. Default 2026-01-01."),
    ] = None,
    end: Annotated[
        datetime | None,
        Query(description="Window end (exclusive), ISO-8601; naive = UTC. Default 2026-02-01."),
    ] = None,
) -> TimeWindow:
    s = _utc(start) if start else _utc(settings.window_from)
    e = _utc(end) if end else _utc(settings.window_to)
    if s >= e:
        raise HTTPException(422, "start must be before end")
    lo, hi = coverage(store)
    if s < lo or e > hi:
        raise HTTPException(
            422, f"window must be within data coverage {lo.isoformat()} – {hi.isoformat()}"
        )
    return TimeWindow(s, e, explicit=start is not None or end is not None)


WindowDep = Annotated[TimeWindow, Depends(time_window)]


def validate_horizon(horizon_hours: float | None, settings: Settings) -> None:
    if horizon_hours is not None and not 0 <= horizon_hours <= settings.max_horizon_hours:
        raise HTTPException(
            422, f"horizon_hours must be between 0 and {settings.max_horizon_hours}"
        )


def delivery_window(settings: Settings) -> TimeWindow:
    """Hourly targets of all delivery days in scope (UK-local days, as UTC)."""
    first, last = delivery_range(settings)
    start, _ = delivery_day_bounds_utc(first)
    _, end = delivery_day_bounds_utc(last)
    return TimeWindow(start, end, explicit=False)


def metrics_window(
    window: TimeWindow, horizon_hours: float | None, settings: Settings
) -> TimeWindow:
    """Day-ahead mode without explicit dates analyses exactly the in-scope delivery days."""
    if horizon_hours is None and not window.explicit:
        return delivery_window(settings)
    return window


def delivery_range(settings: Settings) -> tuple[date, date]:
    return (
        date.fromisoformat(settings.delivery_date_from),
        date.fromisoformat(settings.delivery_date_to),
    )
