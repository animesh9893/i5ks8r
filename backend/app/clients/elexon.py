"""Thin async client for the Elexon BMRS Insights API stream endpoints."""

import logging
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import wait_base

logger = logging.getLogger(__name__)

Record = dict[str, Any]


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


class ElexonClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        attempts: int = 3,
        wait: wait_base | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._attempts = attempts
        self._wait = wait or wait_exponential(multiplier=1, min=1, max=8)
        self._transport = transport

    async def fetch_actuals(self, date_from: str, date_to: str) -> list[Record]:
        """Half-hourly outturn generation for WIND (FUELHH), by settlement date (inclusive)."""
        return await self._get(
            "/datasets/FUELHH/stream",
            {"settlementDateFrom": date_from, "settlementDateTo": date_to, "fuelType": "WIND"},
        )

    async def fetch_forecasts(self, publish_from: str, publish_to: str) -> list[Record]:
        """Hourly national wind forecasts (WINDFOR) published in the given window."""
        return await self._get(
            "/datasets/WINDFOR/stream",
            {"publishDateTimeFrom": publish_from, "publishDateTimeTo": publish_to},
        )

    async def _get(self, path: str, params: dict[str, str]) -> list[Record]:
        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=self._timeout, transport=self._transport
        ) as client:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._attempts),
                wait=self._wait,
                retry=retry_if_exception(_is_retryable),
                reraise=True,
            ):
                with attempt:
                    n = attempt.retry_state.attempt_number
                    logger.info("GET %s %s (attempt %d)", path, params, n)
                    resp = await client.get(path, params=params)
                    resp.raise_for_status()
                    data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected response shape from {path}: {type(data).__name__}")
        return data
