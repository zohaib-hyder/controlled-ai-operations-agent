import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.agents.orchestrator import get_orchestrator
from app.api.actions import router as actions_router
from app.api.auth import router as auth_router
from app.api.business import router as business_router
from app.api.execution import router as execution_router
from app.api.investigations import router as investigations_router
from app.api.jobs import router as jobs_router
from app.api.operations import router as operations_router
from app.api.system import router
from app.api.tools import router as tools_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.tool_body_limit import ToolBodyLimit
from app.db.session import get_engine
from app.schemas.system import ErrorDetail, ErrorResponse
from app.tools.executor import get_tool_executor

configure_logging(get_settings().log_level)
logger = logging.getLogger("northstar.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    if get_tool_executor.cache_info().currsize:
        get_tool_executor().close()
        get_tool_executor.cache_clear()
    get_orchestrator.cache_clear()
    get_engine().dispose()


app = FastAPI(
    title="Northstar Controlled Operations", version="0.1.0", lifespan=lifespan
)
app.include_router(router)
app.include_router(auth_router)
app.include_router(actions_router)
app.include_router(execution_router)
app.include_router(jobs_router)
app.include_router(operations_router)
app.include_router(business_router)
app.include_router(tools_router)
app.include_router(investigations_router)
app.add_middleware(ToolBodyLimit)


def error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=ErrorDetail(
                code=code, message=message, request_id=request.state.request_id
            )
        ).model_dump(),
    )


@app.middleware("http")
async def request_context(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    request.state.request_id = str(uuid4())
    start = monotonic()
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request.state.request_id,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": round((monotonic() - start) * 1000, 2),
        },
    )
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    response = error(
        request,
        exc.status_code,
        "database_unavailable" if exc.status_code == 503 else "http_error",
        str(exc.detail),
    )
    if exc.headers:
        response.headers.update(exc.headers)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error(request, 422, "validation_error", "Request validation failed")


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unexpected_error request_id=%s exception_type=%s",
        request.state.request_id,
        type(exc).__name__,
    )
    return error(request, 500, "internal_error", "An unexpected error occurred")


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database_unavailable", extra={"request_id": request.state.request_id})
    return error(request, 503, "database_unavailable", "Database is unavailable")
