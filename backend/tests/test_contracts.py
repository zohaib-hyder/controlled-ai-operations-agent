import json
import logging

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.schemas.system import Status


def test_strict_system_contract():
    with pytest.raises(ValidationError):
        Status(status="ok", unexpected="untrusted")
    with pytest.raises(ValidationError):
        Status(status=1)


def test_mock_only_configuration():
    assert Settings(_env_file=None).ai_provider == "mock"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ai_provider="unconfigured-real-provider")


def test_log_fields_are_machine_readable():
    record = logging.LogRecord(
        "northstar.api", logging.INFO, "", 0, "request_completed", (), None
    )
    record.request_id = "synthetic-request"
    record.status = 200
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "request_completed"
    assert payload["request_id"] == "synthetic-request"
    assert payload["status"] == 200
    assert "timestamp" in payload
