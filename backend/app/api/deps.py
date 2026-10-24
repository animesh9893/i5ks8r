from fastapi import HTTPException, Request

from app.data.store import DataStore


def get_store(request: Request) -> DataStore:
    """Return the loaded DataStore, or 503 while data is still loading."""
    store: DataStore | None = getattr(request.app.state, "store", None)
    if store is None or not store.is_loaded:
        raise HTTPException(status_code=503, detail="data loading")
    return store
