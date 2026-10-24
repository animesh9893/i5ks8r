"""Refresh the committed offline snapshot from Elexon.

Usage (from backend/):  python -m scripts.fetch_snapshot
"""

import asyncio
import logging

from app.clients.elexon import ElexonClient
from app.config import get_settings
from app.data.store import (
    SNAPSHOT_DIR,
    normalise_actuals,
    normalise_forecasts,
    write_snapshot,
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    s = get_settings()
    client = ElexonClient(s.elexon_base_url)
    actuals, forecasts = await asyncio.gather(
        client.fetch_actuals(s.actuals_date_from, s.actuals_date_to),
        client.fetch_forecasts(s.forecast_publish_from, s.forecast_publish_to),
    )
    write_snapshot(actuals, forecasts)
    a, f = normalise_actuals(actuals), normalise_forecasts(forecasts)
    print(f"Wrote snapshot to {SNAPSHOT_DIR}")
    print(
        f"  actuals:   {len(actuals)} raw → {len(a)} rows, "
        f"{a.start_time.min()} → {a.start_time.max()}"
    )
    print(
        f"  forecasts: {len(forecasts)} raw → {len(f)} rows (horizon ≥ 0), "
        f"{f.publish_time.nunique()} publishes, {f.publish_time.min()} → {f.publish_time.max()}, "
        f"max horizon {f.horizon_h.max():.1f} h"
    )


if __name__ == "__main__":
    asyncio.run(main())
