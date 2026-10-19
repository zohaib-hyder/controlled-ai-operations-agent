from uuid import UUID

from pydantic import Field

from app.schemas.system import StrictModel


class Login(StrictModel):
    email: str = Field(
        min_length=3, max_length=200, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=1, max_length=256, repr=False)


class CurrentUser(StrictModel):
    user_id: UUID
    tenant_id: UUID
    session_id: UUID
    email: str
    role: str
    permissions: list[str]
