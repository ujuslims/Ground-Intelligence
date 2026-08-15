from pydantic import BaseModel


class InspectResponse(BaseModel):
    file_id: str
    columns: list[str]
    preview_rows: list[dict]
    proposed_mapping: dict[str, str | None]
    row_count: int


class ConfirmImportRequest(BaseModel):
    file_id: str
    mapping: dict[str, str | None]


class ImportResultResponse(BaseModel):
    imported: int
    errors: list[str]
    dataset_id: str | None = None
