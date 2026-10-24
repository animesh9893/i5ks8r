from fastapi import APIRouter, Request

from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    store = getattr(request.app.state, "store", None)
    return HealthResponse(status="ok", data_loaded=bool(store and store.is_loaded))
