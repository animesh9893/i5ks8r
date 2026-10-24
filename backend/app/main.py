import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_meta import router as meta_router
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # The DataStore is wired in by T2; until then the API reports data_loaded=false.
    app.state.store = None
    logger.info("API started")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
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


app = create_app()
