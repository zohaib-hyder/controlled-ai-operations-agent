MESSAGES = {
    "unknown_tool": "Tool is not available",
    "unsupported_version": "Tool version is not supported",
    "invalid_arguments": "Arguments do not match the tool contract",
    "arguments_too_large": "Tool arguments exceed the size limit",
    "permission_denied": "Permission denied",
    "authentication_required": "Authentication required",
    "not_found": "Resource not found",
    "timeout": "Tool execution exceeded its time limit",
    "cancelled": "Tool execution was cancelled",
    "output_invalid": "Tool returned an invalid result",
    "result_too_large": "Tool result exceeds the size limit",
    "database_unavailable": "Tool data service is unavailable",
    "audit_unavailable": "Execution audit could not be persisted",
    "rate_limited": "Tool execution limit reached; try again later",
    "capacity_exceeded": "Tool workers are busy; try again later",
    "internal_error": "Tool execution failed",
}
HTTP_STATUS = {
    "unknown_tool": 404,
    "not_found": 404,
    "unsupported_version": 422,
    "invalid_arguments": 422,
    "arguments_too_large": 413,
    "permission_denied": 403,
    "authentication_required": 401,
    "timeout": 504,
    "cancelled": 409,
    "output_invalid": 500,
    "result_too_large": 500,
    "database_unavailable": 503,
    "audit_unavailable": 503,
    "rate_limited": 429,
    "capacity_exceeded": 429,
    "internal_error": 500,
}


class ToolError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(MESSAGES[code])
