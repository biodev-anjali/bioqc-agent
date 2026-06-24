from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from models import AnalysisJob, JobStatus
from schemas import AnalysisJobResponse, UploadResponse
from services.file_storage import FileStorageError, FileStorageService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_file_storage_service() -> FileStorageService:
    return FileStorageService()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_job_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: FileStorageService = Depends(get_file_storage_service),
) -> UploadResponse:
    job = AnalysisJob(
        original_filename=file.filename or "unknown",
        stored_filename="",
        file_path="",
        file_size=0,
        content_type=file.content_type,
        file_type="other",
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        stored_filename, file_path, file_size = storage.save_upload(job.id, file)
        job.stored_filename = stored_filename
        job.file_path = file_path
        job.file_size = file_size
        job.file_type = storage.detect_file_type(file.filename or stored_filename)
        job.status = JobStatus.UPLOADED
        job.error_message = None
        db.commit()
        db.refresh(job)
    except FileStorageError as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        db.commit()
        storage.delete_job_files(job.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error_message = "Failed to store uploaded file."
        db.commit()
        storage.delete_job_files(job.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded file.",
        ) from exc

    return UploadResponse(
        message="File uploaded successfully.",
        job=AnalysisJobResponse.model_validate(job),
    )


@router.get("/{job_id}", response_model=AnalysisJobResponse)
def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> AnalysisJobResponse:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return AnalysisJobResponse.model_validate(job)
