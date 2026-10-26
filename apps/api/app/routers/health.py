from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


@router.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Confirm that the API process can receive requests."""

    return HealthResponse(status="ok", timestamp=datetime.now(UTC))


@router.get("/health/ready", response_model=HealthResponse)
def readiness() -> HealthResponse:
    """Confirm readiness for the Phase 1 stateless API workload."""

    return HealthResponse(status="ready", timestamp=datetime.now(UTC))
