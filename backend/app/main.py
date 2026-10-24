import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_meta import router as meta_router
from app.config import Settings, get_settings
from app.data.store import DataStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, store: DataStore | None = None) -> FastAPI:
    """Build the app. Pass a pre-loaded `store` (e.g. in tests) to skip loading at startup."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.store = store or DataStore(settings)
        load_task = None
        if not app.state.store.is_loaded:
            # Load in the background so /api/health answers immediately (Railway healthcheck);
            # data endpoints return 503 until loading finishes.
            load_task = asyncio.create_task(app.state.store.load())
            load_task.add_done_callback(_log_load_failure)
        yield
        if load_task and not load_task.done():
            load_task.cancel()

    app = FastAPI(
        title="GB Wind Forecast Monitor API",
        version="0.1.0",
        description="Actual vs forecast national wind generation (Elexon BMRS).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(meta_router)
    return app


def _log_load_failure(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.error("Data load failed", exc_info=task.exception())


app = create_app()
