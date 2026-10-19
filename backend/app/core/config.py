from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env", extra="ignore", hide_input_in_errors=True
    )
    database_url: str = (
        "postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ai_provider: Literal["mock", "openai_compatible"] = "mock"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    llm_model: str | None = Field(default=None, max_length=100)
    llm_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    llm_max_output_tokens: int = Field(default=1024, ge=128, le=4096)
    llm_max_requests: int = Field(default=8, ge=1, le=20)
    llm_total_output_tokens: int = Field(default=8192, ge=128, le=65536)
    llm_max_cost_microusd: int = Field(default=100000, ge=1, le=100000000)
    llm_input_usd_per_million: float = Field(default=0, ge=0, le=1000)
    llm_output_usd_per_million: float = Field(default=0, ge=0, le=1000)
    planner_context_bytes: int = Field(default=65536, ge=4096, le=131072)

    app_env: Literal["development", "test", "production"] = "development"
    cookie_secure: bool = False
    trusted_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    session_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    login_window_seconds: int = Field(default=300, ge=60, le=3600)
    login_max_failures: int = Field(default=5, ge=2, le=20)
    demo_password: str | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="after")
    def validate_security(self):
        if self.ai_provider == "openai_compatible":
            if not all(
                (
                    self.llm_base_url,
                    self.llm_api_key.get_secret_value().strip()
                    if self.llm_api_key
                    else None,
                    self.llm_model.strip() if self.llm_model else None,
                    self.llm_input_usd_per_million,
                    self.llm_output_usd_per_million,
                )
            ):
                raise ValueError(
                    "Explicit provider mode requires endpoint, key, model and positive configured cost rates"
                )
            parsed_provider = urlsplit(self.llm_base_url)
            if (
                parsed_provider.scheme != "https"
                or not parsed_provider.hostname
                or parsed_provider.username
                or parsed_provider.password
                or parsed_provider.query
                or parsed_provider.fragment
            ):
                raise ValueError(
                    "Provider endpoint must be a fixed HTTPS base URL without credentials/query/fragment"
                )
        if not self.trusted_origins:
            raise ValueError("At least one trusted origin is required")
        for origin in self.trusted_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or "*" in origin
            ):
                raise ValueError("Trusted origins must be exact HTTP(S) origins")
        if self.app_env == "production":
            if not self.cookie_secure or any(
                not origin.startswith("https://") for origin in self.trusted_origins
            ):
                raise ValueError("Production requires Secure cookies and HTTPS origins")
            if self.demo_password:
                raise ValueError("Demo credentials are prohibited in production")
        return self

    agent_max_steps: int = Field(default=8, ge=1, le=20)
    agent_max_tool_calls: int = Field(default=8, ge=1, le=20)
    agent_wall_seconds: float = Field(default=8.0, gt=0, le=30)
    agent_max_repeats: int = Field(default=1, ge=1, le=2)
    agent_observation_bytes: int = Field(default=48000, ge=128, le=100000)
    agent_planning_iterations: int = Field(default=8, ge=1, le=20)

    evidence_freshness_seconds: int = Field(default=86400, ge=60, le=31536000)

    database_timeout_seconds: int = Field(default=3, ge=1, le=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()
