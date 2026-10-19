from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.services.authentication import IdentityDependency, require_origin
from app.tools.contracts import Invocation, Result, ToolDescription
from app.tools.errors import HTTP_STATUS
from app.tools.executor import ToolExecutor, get_tool_executor

router = APIRouter(prefix="/api/v1/tools", tags=["read-only tools"])
ExecutorDependency = Annotated[ToolExecutor, Depends(get_tool_executor)]


@router.get("", response_model=list[ToolDescription])
def tools(identity: IdentityDependency, executor: ExecutorDependency):
    return executor.registry.available(identity.permissions)


@router.post("/execute", response_model=Result, dependencies=[Depends(require_origin)])
async def execute(
    body: Invocation,
    request: Request,
    response: Response,
    identity: IdentityDependency,
    executor: ExecutorDependency,
) -> Result:
    result = await executor.execute(
        body, identity=identity, correlation_id=UUID(request.state.request_id)
    )
    if result.error:
        response.status_code = HTTP_STATUS[result.error.code]
    return result
