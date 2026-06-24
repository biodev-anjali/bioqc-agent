import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_consultant
from app.models.all_models import Task, User
from app.schemas.all_schemas import TaskCreate, TaskUpdate, TaskOut
from app.core.exceptions import NotFoundError
from app.core.constants import TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _get(tid: uuid.UUID, user: User, db: AsyncSession) -> Task:
    r = await db.execute(select(Task).where(Task.id == tid, Task.created_by == user.id))
    t = r.scalar_one_or_none()
    if not t: raise NotFoundError("Task")
    return t


@router.get("", response_model=list[TaskOut])
async def list_tasks(status: TaskStatus | None = Query(None), project_id: uuid.UUID | None = Query(None),
                     page: int = Query(1, ge=1), per_page: int = Query(50, le=200),
                     user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    q = select(Task).where(Task.created_by == user.id).order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
    if status: q = q.where(Task.status == status)
    if project_id: q = q.where(Task.project_id == project_id)
    r = await db.execute(q.offset((page-1)*per_page).limit(per_page))
    return r.scalars().all()


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(body: TaskCreate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    t = Task(created_by=user.id, **body.model_dump())
    db.add(t); await db.commit(); await db.refresh(t); return t


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    return await _get(task_id, user, db)


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(task_id: uuid.UUID, body: TaskUpdate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    t = await _get(task_id, user, db)
    for k, v in body.model_dump(exclude_none=True).items(): setattr(t, k, v)
    if body.status == TaskStatus.done and not t.completed_at:
        t.completed_at = datetime.now(timezone.utc)
    await db.commit(); await db.refresh(t); return t


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    t = await _get(task_id, user, db); await db.delete(t); await db.commit()