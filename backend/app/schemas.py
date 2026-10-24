"""Pydantic response models: the API contract (mirrored in frontend/src/api/types.ts)."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    data_loaded: bool
