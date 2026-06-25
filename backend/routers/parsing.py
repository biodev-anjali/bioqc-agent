from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import AnalysisJob, JobStatus, QCResult
from schemas import AnalysisJobResponse, ParseResponse, QCResultResponse
from services.fastqc_parser import FastQCParseError, parse_fastqc_zip

router = APIRouter(prefix="/jobs", tags=["parsing"])


def _resolve_upload_path(job: AnalysisJob) -> Path:
    settings = get_settings()
    return settings.upload_dir.parent / job.file_path


@router.post("/{job_id}/parse", response_model=ParseResponse)
def parse_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> ParseResponse:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if job.status not in {JobStatus.UPLOADED, JobStatus.FAILED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be parsed in status '{job.status.value}'.",
        )

    zip_path = _resolve_upload_path(job)
    if not zip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload file not found on disk.",
        )

    try:
        metrics = parse_fastqc_zip(zip_path)
    except FastQCParseError as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        db.commit()
        db.refresh(job)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if job.qc_result is not None:
        db.delete(job.qc_result)
        db.flush()

    result = QCResult(
        job_id=job.id,
        total_sequences=metrics.total_sequences,
        sequence_length=metrics.sequence_length,
        gc_percent=metrics.gc_percent,
        per_base_quality_status=metrics.per_base_quality_status,
        per_sequence_quality_status=metrics.per_sequence_quality_status,
        adapter_content_status=metrics.adapter_content_status,
        overrepresented_sequences_status=metrics.overrepresented_sequences_status,
    )
    db.add(result)
    job.status = JobStatus.PARSED
    job.error_message = None
    db.commit()
    db.refresh(job)
    db.refresh(result)

    return ParseResponse(
        message="FastQC report parsed successfully.",
        job=AnalysisJobResponse.model_validate(job),
        result=QCResultResponse.model_validate(result),
    )


@router.get("/{job_id}/results", response_model=QCResultResponse)
def get_job_results(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> QCResultResponse:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if job.qc_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No QC results found for this job.",
        )

    return QCResultResponse.model_validate(job.qc_result)
