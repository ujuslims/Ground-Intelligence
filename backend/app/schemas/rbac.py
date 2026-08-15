import uuid

from pydantic import BaseModel, ConfigDict


class RoleOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class PermissionOut(BaseModel):
    id: uuid.UUID
    code: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class ProjectMembershipCreate(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID


class ProjectMembershipOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
