import uuid

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    project_code: str
    name: str
    client_id: uuid.UUID
    project_type: str | None = None
    description: str | None = None
    location: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    project_code: str
    name: str
    client_id: uuid.UUID
    project_type: str | None
    description: str | None
    location: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class ClientCreate(BaseModel):
    name: str
    organization_id: uuid.UUID


class ClientOut(BaseModel):
    id: uuid.UUID
    name: str
    organization_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(BaseModel):
    name: str


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)
