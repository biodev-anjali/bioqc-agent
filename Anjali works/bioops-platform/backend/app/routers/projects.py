import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.dependencies import require_consultant, get_current_user
from app.models.all_models import User, Project, PipelineStageLog, Task, File, Report
from app.schemas.all_schemas import (ProjectCreate, ProjectUpdate, ProjectStatusUpdate,
                                      ProjectOut, PipelineStageLogOut, TaskOut, FileOut, ReportOut)
from app.core.exceptions import NotFoundError, ForbiddenError
from app.core.constants import ProjectStatus

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get(pid: uuid.UUID, user: User, db: AsyncSession) -> Project:
    r = await db.execute(select(Project).options(selectinload(Project.client)).where(Project.id == pid))
    p = r.scalar_one_or_none()
    if not p: raise NotFoundError("Project")
    if p.consultant_id != user.id and user.role != "admin": raise ForbiddenError()
    return p


async def _next_code(db: AsyncSession) -> str:
    year = datetime.now().year
    r = await db.execute(select(func.count(Project.id)).where(Project.project_code.like(f"BIO-{year}-%")))
    return f"BIO-{year}-{(r.scalar() or 0) + 1:03d}"


@router.get("", response_model=list[ProjectOut])
async def list_projects(status: ProjectStatus | None = Query(None), client_id: uuid.UUID | None = Query(None),
                        search: str | None = Query(None), page: int = Query(1, ge=1), per_page: int = Query(20, le=100),
                        user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    q = select(Project).options(selectinload(Project.client)).where(Project.consultant_id == user.id).order_by(Project.created_at.desc())
    if status: q = q.where(Project.status == status)
    if client_id: q = q.where(Project.client_id == client_id)
    if search: q = q.where(Project.title.ilike(f"%{search}%"))
    r = await db.execute(q.offset((page-1)*per_page).limit(per_page))
    return r.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    code = await _next_code(db)
    p = Project(project_code=code, consultant_id=user.id, **body.model_dump())
    db.add(p)
    await db.flush()
    db.add(PipelineStageLog(project_id=p.id, stage=ProjectStatus.draft, started_at=datetime.now(timezone.utc), created_by=user.id))
    await db.commit(); await db.refresh(p); return p


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _get(project_id, user, db)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: uuid.UUID, body: ProjectUpdate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    p = await _get(project_id, user, db)
    for k, v in body.model_dump(exclude_none=True).items(): setattr(p, k, v)
    await db.commit(); await db.refresh(p); return p


@router.put("/{project_id}/status", response_model=ProjectOut)
async def advance_status(project_id: uuid.UUID, body: ProjectStatusUpdate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    p = await _get(project_id, user, db)
    now = datetime.now(timezone.utc)
    r = await db.execute(select(PipelineStageLog).where(PipelineStageLog.project_id == project_id, PipelineStageLog.stage == p.status, PipelineStageLog.completed_at.is_(None)).order_by(PipelineStageLog.started_at.desc()))
    log = r.scalar_one_or_none()
    if log: log.completed_at = now
    p.status = body.status
    if body.status == ProjectStatus.delivered: p.delivered_at = now
    db.add(PipelineStageLog(project_id=project_id, stage=body.status, started_at=now, notes=body.notes, created_by=user.id))
    await db.commit(); await db.refresh(p); return p


@router.get("/{project_id}/timeline", response_model=list[PipelineStageLogOut])
async def get_timeline(project_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get(project_id, user, db)
    r = await db.execute(select(PipelineStageLog).where(PipelineStageLog.project_id == project_id).order_by(PipelineStageLog.started_at))
    return r.scalars().all()


@router.get("/{project_id}/tasks", response_model=list[TaskOut])
async def get_tasks(project_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get(project_id, user, db)
    r = await db.execute(select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc()))
    return r.scalars().all()


@router.get("/{project_id}/files", response_model=list[FileOut])
async def get_files(project_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get(project_id, user, db)
    r = await db.execute(select(File).where(File.project_id == project_id).order_by(File.created_at.desc()))
    return r.scalars().all()


@router.get("/{project_id}/reports", response_model=list[ReportOut])
async def get_reports(project_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get(project_id, user, db)
    r = await db.execute(select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc()))
    return r.scalars().all()


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    p = await _get(project_id, user, db); await db.delete(p); await db.commit()