import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_user, require_consultant
from app.models.all_models import File, User
from app.schemas.all_schemas import FileRegister, FileOut, UploadURLRequest, UploadURLResponse
from app.services.file_service import generate_storage_key, generate_upload_url, generate_download_url, delete_file, file_exists, guessFileType
from app.core.exceptions import NotFoundError, FileStorageError

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/upload-url", response_model=UploadURLResponse)
async def get_upload_url(body: UploadURLRequest, user: User = Depends(get_current_user)):
    key = generate_storage_key(str(body.project_id), body.file_name)
    url = generate_upload_url(key, body.content_type)
    return UploadURLResponse(upload_url=url, storage_key=key)


@router.post("", response_model=FileOut, status_code=201)
async def register_file(body: FileRegister, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not file_exists(body.storage_key):
        raise FileStorageError("File not found in storage. Upload may have failed.")
    f = File(uploaded_by=user.id, **body.model_dump())
    db.add(f); await db.commit(); await db.refresh(f); return f


@router.get("/{file_id}", response_model=FileOut)
async def get_file(file_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(File).where(File.id == file_id))
    f = r.scalar_one_or_none()
    if not f: raise NotFoundError("File")
    return f


@router.get("/{file_id}/download-url")
async def get_download_url(file_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(File).where(File.id == file_id))
    f = r.scalar_one_or_none()
    if not f: raise NotFoundError("File")
    return {"download_url": generate_download_url(f.storage_key, filename=f.file_name), "file_name": f.file_name}


@router.delete("/{file_id}", status_code=204)
async def delete_file_record(file_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(File).where(File.id == file_id))
    f = r.scalar_one_or_none()
    if not f: raise NotFoundError("File")
    delete_file(f.storage_key)
    await db.delete(f); await db.commit()