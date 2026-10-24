from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:5173"
    cors_origin_regex: str | None = r"https://.*\.vercel\.app"

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    data_source: str = "live"  # "live" (Elexon, snapshot fallback) or "snapshot"

    forecast_publish_from: str = "2025-12-29T00:00:00Z"
    forecast_publish_to: str = "2026-02-01T00:00:00Z"
    actuals_date_from: str = "2026-01-01"
    actuals_date_to: str = "2026-02-02"

    day_ahead_gate_local: str = "11:00"
    max_horizon_hours: int = 48

    admin_token: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
