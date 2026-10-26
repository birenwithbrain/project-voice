from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db.session import database_is_ready

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
    """Confirm that the API and its required database are ready."""

    if not database_is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        )

    return HealthResponse(status="ready", timestamp=datetime.now(UTC))
