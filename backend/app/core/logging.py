import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "event": record.getMessage(),
                **{
                    key: getattr(record, key)
                    for key in (
                        "request_id",
                        "method",
                        "status",
                        "duration_ms",
                        "job_id",
                        "tenant_id",
                        "state",
                        "category",
                        "correlation_id",
                        "worker_id",
                        "metrics",
                    )
                    if hasattr(record, key)
                },
            }
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)

    for name in ("uvicorn", "uvicorn.error"):
        server_logger = logging.getLogger(name)
        server_logger.handlers.clear()
        server_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True

    # Provider headers/bodies are never logged; suppress client URL/debug diagnostics.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
