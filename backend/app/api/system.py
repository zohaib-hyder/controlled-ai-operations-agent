from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.system import ErrorResponse, Status

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=Status)
def health() -> Status:
    return Status(status="ok")


@router.get("/ready", response_model=Status, responses={503: {"model": ErrorResponse}})
def ready(session: Annotated[Session, Depends(get_session)]) -> Status:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return Status(status="ready")
