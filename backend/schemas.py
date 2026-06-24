from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models import JobStatus


class HealthResponse(BaseModel):
    status: str
    service: str


class AnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    content_type: str | None
    file_type: str
    status: JobStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    message: str
    job: AnalysisJobResponse
