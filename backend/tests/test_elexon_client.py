import httpx
import pytest
import respx
from tenacity import wait_none

from app.clients.elexon import ElexonClient

BASE = "https://elexon.test/bmrs/api/v1"


def make_client(attempts: int = 3) -> ElexonClient:
    return ElexonClient(BASE, attempts=attempts, wait=wait_none())


@respx.mock
async def test_fetch_actuals_sends_wind_filter():
    route = respx.get(f"{BASE}/datasets/FUELHH/stream").mock(
        return_value=httpx.Response(200, json=[{"generation": 1}])
    )
    rows = await make_client().fetch_actuals("2026-01-01", "2026-01-02")
    assert rows == [{"generation": 1}]
    params = route.calls.last.request.url.params
    assert params["fuelType"] == "WIND"
    assert params["settlementDateFrom"] == "2026-01-01"


@respx.mock
async def test_retries_on_server_error_then_succeeds():
    route = respx.get(f"{BASE}/datasets/WINDFOR/stream").mock(
        side_effect=[httpx.Response(503), httpx.ConnectError("boom"), httpx.Response(200, json=[])]
    )
    assert await make_client().fetch_forecasts("a", "b") == []
    assert route.call_count == 3


@respx.mock
async def test_does_not_retry_client_error():
    route = respx.get(f"{BASE}/datasets/WINDFOR/stream").mock(return_value=httpx.Response(400))
    with pytest.raises(httpx.HTTPStatusError):
        await make_client().fetch_forecasts("a", "b")
    assert route.call_count == 1


@respx.mock
async def test_gives_up_after_max_attempts():
    route = respx.get(f"{BASE}/datasets/WINDFOR/stream").mock(return_value=httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        await make_client(attempts=2).fetch_forecasts("a", "b")
    assert route.call_count == 2


@respx.mock
async def test_rejects_non_list_payload():
    respx.get(f"{BASE}/datasets/WINDFOR/stream").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    with pytest.raises(ValueError, match="Unexpected response shape"):
        await make_client().fetch_forecasts("a", "b")
