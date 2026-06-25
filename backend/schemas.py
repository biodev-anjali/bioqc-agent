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


class QCResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    total_sequences: int
    sequence_length: str
    gc_percent: float
    per_base_quality_status: str
    per_sequence_quality_status: str
    adapter_content_status: str
    overrepresented_sequences_status: str
    created_at: datetime


class ParseResponse(BaseModel):
    message: str
    job: AnalysisJobResponse
    result: QCResultResponse
