from typing import Annotated

from fastapi import APIRouter, Query

from app.api import queries
from app.api.deps import (
    SettingsDep,
    StoreDep,
    WindowDep,
    delivery_range,
    metrics_window,
    validate_horizon,
)
from app.schemas import DistributionResponse, HorizonMetrics, HourMetrics, MetricsSummary
from app.services import metrics

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

HorizonQuery = Annotated[
    float | None,
    Query(
        description="Forecast horizon in hours. Omit for day-ahead mode (forecast at the D−1 gate)."
    ),
]


@router.get("", response_model=MetricsSummary, summary="Headline accuracy metrics")
def summary(
    store: StoreDep, settings: SettingsDep, window: WindowDep, horizon_hours: HorizonQuery = None
) -> MetricsSummary:
    validate_horizon(horizon_hours, settings)
    window = metrics_window(window, horizon_hours, settings)
    rows = queries.paired(
        store, window, horizon_hours, settings.day_ahead_gate_local, delivery_range(settings)
    )
    return MetricsSummary(
        mode="day_ahead" if horizon_hours is None else "horizon",
        horizon_hours=horizon_hours,
        start=window.start,
        end=window.end,
        **metrics.summary(rows),
    )


@router.get("/by-horizon", response_model=list[HorizonMetrics], summary="Error vs forecast horizon")
def by_horizon(
    store: StoreDep,
    settings: SettingsDep,
    window: WindowDep,
    max_h: Annotated[int | None, Query(ge=0, description="Largest horizon (default 48)")] = None,
    step: Annotated[int, Query(ge=1, le=24)] = 1,
) -> list[HorizonMetrics]:
    top = settings.max_horizon_hours if max_h is None else max_h
    validate_horizon(top, settings)
    horizons = list(range(0, top + 1, step))
    rows = store.cached(
        ("by_horizon", window.start, window.end, tuple(horizons)),
        lambda: metrics.by_horizon(
            store.forecasts, store.actuals, window.start, window.end, horizons
        ),
    )
    return [HorizonMetrics(**r) for r in rows]


@router.get("/by-hour", response_model=list[HourMetrics], summary="Error by UK-local hour of day")
def by_hour(
    store: StoreDep, settings: SettingsDep, window: WindowDep, horizon_hours: HorizonQuery = None
) -> list[HourMetrics]:
    validate_horizon(horizon_hours, settings)
    window = metrics_window(window, horizon_hours, settings)
    rows = queries.paired(
        store, window, horizon_hours, settings.day_ahead_gate_local, delivery_range(settings)
    )
    return [HourMetrics(**r) for r in metrics.by_hour(rows)]


@router.get(
    "/distribution", response_model=DistributionResponse, summary="Histogram of forecast errors"
)
def distribution(
    store: StoreDep,
    settings: SettingsDep,
    window: WindowDep,
    horizon_hours: HorizonQuery = None,
    bins: Annotated[int, Query(ge=5, le=200)] = 40,
) -> DistributionResponse:
    validate_horizon(horizon_hours, settings)
    window = metrics_window(window, horizon_hours, settings)
    rows = queries.paired(
        store, window, horizon_hours, settings.day_ahead_gate_local, delivery_range(settings)
    )
    return DistributionResponse(**metrics.distribution(rows, bins))
