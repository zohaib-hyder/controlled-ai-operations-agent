from uuid import uuid4

from starlette.responses import JSONResponse


class ToolBodyLimit:
    """Bound tool and investigation bodies before framework JSON parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        control = path.startswith("/api/v1/investigations/") and path.endswith(
            ("/cancel", "/resume", "/action-proposal")
        )
        if (
            path not in {"/api/v1/tools/execute", "/api/v1/investigations"}
            and not path.startswith("/api/v1/action-proposals")
            and not path.startswith("/api/v1/approvals")
            and not path.startswith("/api/v1/execution-jobs")
            and not path.startswith("/api/v1/operations")
            and not path.startswith("/api/v1/incidents")
            and not control
        ):
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 8192:
                correlation = scope.get("state", {}).get("request_id", str(uuid4()))
                response = JSONResponse(
                    {
                        "error": {
                            "code": "request_too_large",
                            "message": "Request exceeds the size limit",
                            "request_id": correlation,
                        }
                    },
                    status_code=413,
                    headers={"Cache-Control": "no-store", "X-Request-ID": correlation},
                )
                return await response(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
