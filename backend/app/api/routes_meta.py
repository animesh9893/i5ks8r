import secrets
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Header, HTTPException, Request

from app.api.deps import SettingsDep, StoreDep, delivery_range
from app.data.store import DataStore
from app.schemas import (
    ActualsCoverage,
    DeliveryRange,
    ForecastsCoverage,
    HealthResponse,
    MetaResponse,
    Window,
)

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    store = getattr(request.app.state, "store", None)
    return HealthResponse(status="ok", data_loaded=bool(store and store.is_loaded))


def _meta(store: DataStore, settings) -> MetaResponse:
    a, f = store.actuals, store.forecasts
    publish_times = f["publish_time"].drop_duplicates()
    first, last = delivery_range(settings)
    return MetaResponse(
        source=store.source,
        loaded_at=store.loaded_at,
        actuals=ActualsCoverage(
            from_=a["start_time"].min() if len(a) else None,
            to=a["start_time"].max() if len(a) else None,
            rows=len(a),
        ),
        forecasts=ForecastsCoverage(
            publish_from=publish_times.min() if len(f) else None,
            publish_to=publish_times.max() if len(f) else None,
            rows=len(f),
            publishes=len(publish_times),
            publish_times_per_day_utc=sorted(publish_times.dt.strftime("%H:%M").unique()),
        ),
        max_horizon_hours=settings.max_horizon_hours,
        day_ahead_gate_local=settings.day_ahead_gate_local,
        default_window=Window(
            start=pd.Timestamp(settings.window_from), end=pd.Timestamp(settings.window_to)
        ),
        delivery_dates=DeliveryRange(first=first, last=last),
    )


@router.get(
    "/meta",
    response_model=MetaResponse,
    response_model_by_alias=True,
    summary="Data coverage, source and defaults",
)
def meta(store: StoreDep, settings: SettingsDep) -> MetaResponse:
    return _meta(store, settings)


@router.post(
    "/admin/refresh",
    response_model=MetaResponse,
    response_model_by_alias=True,
    summary="Reload data from Elexon (requires X-Admin-Token)",
)
async def refresh(
    request: Request,
    settings: SettingsDep,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> MetaResponse:
    if not settings.admin_token:
        raise HTTPException(404, "refresh is disabled")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "invalid admin token")
    store: DataStore = request.app.state.store
    await store.load()
    return _meta(store, settings)
