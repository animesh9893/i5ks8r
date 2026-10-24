import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data.store import DataStore, normalise_actuals, normalise_forecasts
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(data_source="snapshot", _env_file=None)


@pytest.fixture
def raw_actuals() -> list[dict]:
    # Two half-hours; the first has a later revision that should win.
    return [
        {"publishTime": "2026-01-01T00:30:00Z", "startTime": "2026-01-01T00:00:00Z",
         "fuelType": "WIND", "generation": 1000},
        {"publishTime": "2026-01-01T00:45:00Z", "startTime": "2026-01-01T00:00:00Z",
         "fuelType": "WIND", "generation": 1100},
        {"publishTime": "2026-01-01T01:00:00Z", "startTime": "2026-01-01T00:30:00Z",
         "fuelType": "WIND", "generation": 1200},
    ]  # fmt: skip


@pytest.fixture
def raw_forecasts() -> list[dict]:
    # One run published 02:30 covering 01:00 (past, must be dropped), 03:00 and 04:00.
    pub = "2026-01-01T02:30:00Z"
    return [
        {"publishTime": pub, "startTime": "2026-01-01T01:00:00Z", "generation": 900},
        {"publishTime": pub, "startTime": "2026-01-01T03:00:00Z", "generation": 950},
        {"publishTime": pub, "startTime": "2026-01-01T04:00:00Z", "generation": 980},
    ]


@pytest.fixture
def loaded_store(settings, raw_actuals, raw_forecasts) -> DataStore:
    return DataStore.from_frames(
        settings, normalise_actuals(raw_actuals), normalise_forecasts(raw_forecasts)
    )


@pytest.fixture
def client(settings, loaded_store) -> TestClient:
    with TestClient(create_app(settings, loaded_store)) as c:
        yield c


@pytest.fixture
def empty_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    return normalise_actuals([]), normalise_forecasts([])
