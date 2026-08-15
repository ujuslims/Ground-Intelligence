from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MethodologyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    engineering_domain: str
    description: str | None
    reference: str | None
    status: str


class MethodologyVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    methodology_id: str
    version: str
    status: str
    configuration_options: str | None
    required_inputs: str | None


class MethodologyRequestCreate(BaseModel):
    requested_name: str
    reference: str | None = None
    version: str | None = None
    source_document_file_id: str | None = None
    applicability: str | None = None
    requested_configuration: str | None = None
    supporting_file_ids: str | None = None
    project_id: str | None = None
    reason: str | None = None


class MethodologyRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    requested_name: str
    reference: str | None
    status: str
    requested_by: str
    created_at: datetime


class CalculationCreate(BaseModel):
    project_id: str
    calculation_type: str
    methodology_id: str | None = None
    methodology_version_id: str | None = None
    selected_configuration: str | None = None


class CalculationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    calculation_type: str
    methodology_id: str | None
    methodology_version_id: str | None
    status: str
    created_at: datetime


class CalculationRunRequest(BaseModel):
    inputs: dict
