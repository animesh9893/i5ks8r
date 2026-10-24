"""Pydantic response models: the API contract (mirrored in frontend/src/api/types.ts).

Times are UTC datetimes (serialised as ISO-8601 with Z), power in MW, energy in MWh.
error_mw = forecast − actual (positive = wind over-forecast). Fields are None where a value is
unavailable (no forecast published early enough, no actual, or no rows to aggregate).
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    data_loaded: bool


# --- meta -------------------------------------------------------------------------------------


class ActualsCoverage(BaseModel):
    from_: datetime | None = Field(serialization_alias="from")
    to: datetime | None
    rows: int


class ForecastsCoverage(BaseModel):
    publish_from: datetime | None
    publish_to: datetime | None
    rows: int
    publishes: int
    publish_times_per_day_utc: list[str]


class Window(BaseModel):
    start: datetime
    end: datetime


class DeliveryRange(BaseModel):
    first: date
    last: date


class MetaResponse(BaseModel):
    source: Literal["live", "snapshot"] | None
    loaded_at: datetime | None
    actuals: ActualsCoverage
    forecasts: ForecastsCoverage
    max_horizon_hours: int
    day_ahead_gate_local: str
    default_window: Window
    delivery_dates: DeliveryRange


# --- series -----------------------------------------------------------------------------------


class SeriesPoint(BaseModel):
    target_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    forecast_publish_time: datetime | None
    horizon_actual_hours: float | None = Field(
        description="Real lead time of the forecast used (≥ the requested horizon)."
    )
    error_mw: float | None


class ActualPoint(BaseModel):
    target_time: datetime
    actual_mw: float


class SeriesResponse(BaseModel):
    horizon_hours: float
    start: datetime
    end: datetime
    points: list[SeriesPoint]
    actuals_30min: list[ActualPoint]


# --- day-ahead --------------------------------------------------------------------------------


class DayAheadPoint(BaseModel):
    target_time: datetime
    forecast_mw: float
    p10_mw: float | None
    p50_mw: float | None
    p90_mw: float | None
    actual_mw: float | None
    horizon_hours: float


class DayAheadSummary(BaseModel):
    expected_energy_mwh: float | None
    p10_energy_mwh: float | None
    p90_energy_mwh: float | None
    peak_forecast_mw: float | None
    min_forecast_mw: float | None
    max_ramp_mw_per_h: float | None
    realised_mae_mw: float | None
    hours_in_band: int | None
    hours_with_actual: int | None


class DayAheadResponse(BaseModel):
    delivery_date: date
    gate_time_utc: datetime
    forecast_publish_time: datetime | None
    band_method: Literal["in_sample", "leakage_free"]
    points: list[DayAheadPoint]
    summary: DayAheadSummary


# --- metrics ----------------------------------------------------------------------------------


class MetricsSummary(BaseModel):
    mode: Literal["horizon", "day_ahead"]
    horizon_hours: float | None
    start: datetime
    end: datetime
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None
    nmae: float | None
    mape: float | None
    p50_abs_error: float | None
    p90_abs_error: float | None
    p99_abs_error: float | None
    max_abs_error: float | None
    correlation: float | None


class HorizonMetrics(BaseModel):
    horizon_hours: float
    n: int
    coverage: float | None
    mae: float | None
    rmse: float | None
    bias: float | None
    p90_abs_error: float | None


class HourMetrics(BaseModel):
    hour_local: int
    mae: float | None
    bias: float | None
    n: int


class HistogramBin(BaseModel):
    start: float
    end: float
    count: int


class ErrorQuantiles(BaseModel):
    p05: float | None
    p50: float | None
    p95: float | None


class DistributionResponse(BaseModel):
    bins: list[HistogramBin]
    quantiles: ErrorQuantiles
