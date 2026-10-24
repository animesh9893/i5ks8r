from datetime import date, time
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.api import queries
from app.api.deps import SettingsDep, StoreDep, WindowDep, delivery_range, validate_horizon
from app.schemas import (
    ActualPoint,
    DayAheadPoint,
    DayAheadResponse,
    DayAheadSummary,
    SeriesPoint,
    SeriesResponse,
)
from app.services import metrics
from app.services.metrics import clean_float

router = APIRouter(prefix="/api", tags=["series"])


@router.get(
    "/series",
    response_model=SeriesResponse,
    summary="Actual vs latest forecast at a horizon",
)
def series(
    store: StoreDep,
    settings: SettingsDep,
    window: WindowDep,
    horizon_hours: Annotated[
        float, Query(description="Use the latest forecast published ≥ this many hours ahead.")
    ] = 4,
) -> SeriesResponse:
    validate_horizon(horizon_hours, settings)
    rows = queries.paired(
        store, window, horizon_hours, settings.day_ahead_gate_local, delivery_range(settings)
    )
    a = store.actuals
    actuals = a[(a["start_time"] >= window.start) & (a["start_time"] < window.end)]
    return SeriesResponse(
        horizon_hours=horizon_hours,
        start=window.start,
        end=window.end,
        points=[
            SeriesPoint(
                target_time=r.start_time,
                actual_mw=clean_float(r.actual_mw),
                forecast_mw=clean_float(r.forecast_mw),
                forecast_publish_time=None if pd.isna(r.publish_time) else r.publish_time,
                horizon_actual_hours=clean_float(r.horizon_h),
                error_mw=clean_float(r.error_mw),
            )
            for r in rows.itertuples(index=False)
        ],
        actuals_30min=[
            ActualPoint(target_time=t, actual_mw=v)
            for t, v in zip(actuals["start_time"], actuals["actual_mw"], strict=True)
        ],
    )


@router.get(
    "/day-ahead",
    response_model=DayAheadResponse,
    summary="Forecast for a delivery day as known at the D−1 gate, with P10–P90 band",
)
def day_ahead(
    store: StoreDep,
    settings: SettingsDep,
    delivery_date: Annotated[date, Query(description="UK-local delivery day, e.g. 2026-01-15")],
    gate_local: Annotated[
        str | None, Query(description="Decision time on D−1, UK local HH:MM. Default 11:00.")
    ] = None,
    leakage_free: Annotated[
        bool,
        Query(description="Fit the band only on errors already known at the gate (out-of-sample)."),
    ] = False,
) -> DayAheadResponse:
    first, last = delivery_range(settings)
    if not first <= delivery_date <= last:
        raise HTTPException(422, f"delivery_date must be between {first} and {last}")
    gate = gate_local or settings.day_ahead_gate_local
    try:
        time.fromisoformat(gate)
    except ValueError:
        raise HTTPException(422, "gate_local must be HH:MM") from None

    gate_utc, publish_time, rows = queries.day_ahead(store, delivery_date, gate, leakage_free)
    return DayAheadResponse(
        delivery_date=delivery_date,
        gate_time_utc=gate_utc,
        forecast_publish_time=publish_time,
        band_method="leakage_free" if leakage_free else "in_sample",
        points=[
            DayAheadPoint(
                target_time=r.start_time,
                forecast_mw=r.forecast_mw,
                p10_mw=clean_float(r.p10_mw),
                p50_mw=clean_float(r.p50_mw),
                p90_mw=clean_float(r.p90_mw),
                actual_mw=clean_float(r.actual_mw),
                horizon_hours=r.horizon_h,
            )
            for r in rows.itertuples(index=False)
        ],
        summary=DayAheadSummary(**metrics.day_ahead_summary(rows)),
    )
