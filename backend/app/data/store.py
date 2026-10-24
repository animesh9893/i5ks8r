"""In-memory data store for wind actuals and forecasts.

The January 2026 dataset is small (~1.6k actual rows, ~16k forecast rows) and historical, so it
is loaded once at startup into pandas DataFrames. If Elexon is unreachable, a committed
snapshot is used.

Normalised frames (all timestamps tz-aware UTC):
- actuals:   start_time, actual_mw                                (30-min resolution)
- forecasts: publish_time, start_time, forecast_mw, horizon_h     (hourly targets, horizon_h >= 0)
"""

import asyncio
import gzip
import json
import logging
from collections.abc import Callable, Hashable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypeVar

import pandas as pd

from app.clients.elexon import ElexonClient, Record
from app.config import Settings

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path(__file__).parent / "snapshot"
ACTUALS_FILE = "fuelhh_wind.json.gz"
FORECASTS_FILE = "windfor.json.gz"

DataSource = Literal["live", "snapshot"]
T = TypeVar("T")


def normalise_actuals(records: list[Record]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            {
                "start_time": pd.Series(dtype="datetime64[ns, UTC]"),
                "actual_mw": pd.Series(dtype="float64"),
            }
        )
    df = pd.DataFrame.from_records(records)
    if "fuelType" in df:
        df = df[df["fuelType"] == "WIND"]
    df = pd.DataFrame(
        {
            "publish_time": pd.to_datetime(df["publishTime"], utc=True),
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "actual_mw": df["generation"].astype("float64"),
        }
    )
    # Keep the latest published value per settlement period.
    df = df.sort_values("publish_time").drop_duplicates("start_time", keep="last")
    return df[["start_time", "actual_mw"]].sort_values("start_time").reset_index(drop=True)


def normalise_forecasts(records: list[Record]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            {
                "publish_time": pd.Series(dtype="datetime64[ns, UTC]"),
                "start_time": pd.Series(dtype="datetime64[ns, UTC]"),
                "forecast_mw": pd.Series(dtype="float64"),
                "horizon_h": pd.Series(dtype="float64"),
            }
        )
    df = pd.DataFrame.from_records(records)
    df = pd.DataFrame(
        {
            "publish_time": pd.to_datetime(df["publishTime"], utc=True),
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "forecast_mw": df["generation"].astype("float64"),
        }
    )
    df["horizon_h"] = (df["start_time"] - df["publish_time"]).dt.total_seconds() / 3600
    # WINDFOR runs also carry rows for hours before their publish time; those are not forecasts.
    df = df[df["horizon_h"] >= 0]
    df = df.drop_duplicates(["publish_time", "start_time"], keep="last")
    return df.sort_values(["publish_time", "start_time"]).reset_index(drop=True)


def read_snapshot(directory: Path = SNAPSHOT_DIR) -> tuple[list[Record], list[Record]]:
    with gzip.open(directory / ACTUALS_FILE, "rt") as f:
        actuals = json.load(f)
    with gzip.open(directory / FORECASTS_FILE, "rt") as f:
        forecasts = json.load(f)
    return actuals, forecasts


def write_snapshot(
    actuals: list[Record], forecasts: list[Record], directory: Path = SNAPSHOT_DIR
) -> None:
    """Write raw records (only the fields we use) as gzipped JSON."""
    directory.mkdir(parents=True, exist_ok=True)
    slim_actuals = [
        {k: r[k] for k in ("publishTime", "startTime", "fuelType", "generation")} for r in actuals
    ]
    slim_forecasts = [
        {k: r[k] for k in ("publishTime", "startTime", "generation")} for r in forecasts
    ]
    for name, rows in ((ACTUALS_FILE, slim_actuals), (FORECASTS_FILE, slim_forecasts)):
        with gzip.open(directory / name, "wt") as f:
            json.dump(rows, f, separators=(",", ":"))


class DataStore:
    def __init__(
        self,
        settings: Settings,
        client: ElexonClient | None = None,
        snapshot_dir: Path = SNAPSHOT_DIR,
    ) -> None:
        self._settings = settings
        self._client = client or ElexonClient(settings.elexon_base_url)
        self._snapshot_dir = snapshot_dir
        self._lock = asyncio.Lock()
        self.actuals: pd.DataFrame | None = None
        self.forecasts: pd.DataFrame | None = None
        self.source: DataSource | None = None
        self.loaded_at: datetime | None = None
        self.last_error: str | None = None
        # Results derived from the current frames (e.g. error quantiles); cleared on every load.
        self.cache: dict[Hashable, Any] = {}

    @property
    def is_loaded(self) -> bool:
        return self.actuals is not None and self.forecasts is not None

    @classmethod
    def from_frames(
        cls,
        settings: Settings,
        actuals: pd.DataFrame,
        forecasts: pd.DataFrame,
        source: DataSource = "snapshot",
    ) -> "DataStore":
        """Build a ready store from already-normalised frames (used by tests and scripts)."""
        store = cls(settings)
        store._set(actuals, forecasts, source)
        return store

    async def load(self) -> None:
        """Load live data (falling back to the snapshot) or the snapshot only, per DATA_SOURCE."""
        async with self._lock:
            if self._settings.data_source == "live":
                try:
                    actuals, forecasts = await self._fetch_live()
                    self._set(normalise_actuals(actuals), normalise_forecasts(forecasts), "live")
                    return
                except Exception as exc:
                    self.last_error = f"{type(exc).__name__}: {exc}"
                    logger.warning("Live load failed (%s); falling back to snapshot", exc)
            actuals, forecasts = await asyncio.to_thread(read_snapshot, self._snapshot_dir)
            self._set(normalise_actuals(actuals), normalise_forecasts(forecasts), "snapshot")

    async def _fetch_live(self) -> tuple[list[Record], list[Record]]:
        s = self._settings
        actuals, forecasts = await asyncio.gather(
            self._client.fetch_actuals(s.actuals_date_from, s.actuals_date_to),
            self._client.fetch_forecasts(s.forecast_publish_from, s.forecast_publish_to),
        )
        if not actuals or not forecasts:
            raise ValueError(f"Empty response: {len(actuals)} actuals, {len(forecasts)} forecasts")
        return actuals, forecasts

    def cached(self, key: Hashable, compute: Callable[[], T]) -> T:
        """Memoise a computation on the current data; invalidated when data is reloaded."""
        if key not in self.cache:
            self.cache[key] = compute()
        return self.cache[key]

    def _set(self, actuals: pd.DataFrame, forecasts: pd.DataFrame, source: DataSource) -> None:
        self.cache = {}
        self.actuals = actuals
        self.forecasts = forecasts
        self.source = source
        self.loaded_at = datetime.now(UTC)
        logger.info(
            "Data loaded from %s: %d actual rows (%s → %s), %d forecast rows from %d publishes",
            source,
            len(actuals),
            actuals["start_time"].min() if len(actuals) else None,
            actuals["start_time"].max() if len(actuals) else None,
            len(forecasts),
            forecasts["publish_time"].nunique(),
        )
