import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_consultant
from app.models.all_models import User, Lead, Client
from app.schemas.all_schemas import LeadCreate, LeadUpdate, LeadOut, ClientOut
from app.core.exceptions import NotFoundError, ConflictError
from app.core.constants import LeadStatus

router = APIRouter(prefix="/leads", tags=["leads"])


async def _get(lid: uuid.UUID, user: User, db: AsyncSession) -> Lead:
    r = await db.execute(select(Lead).where(Lead.id == lid, Lead.consultant_id == user.id))
    l = r.scalar_one_or_none()
    if not l: raise NotFoundError("Lead")
    return l


@router.get("", response_model=list[LeadOut])
async def list_leads(status: LeadStatus | None = Query(None), search: str | None = Query(None),
                     page: int = Query(1, ge=1), per_page: int = Query(20, le=100),
                     user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    q = select(Lead).where(Lead.consultant_id == user.id).order_by(Lead.created_at.desc())
    if status: q = q.where(Lead.status == status)
    if search: q = q.where(Lead.full_name.ilike(f"%{search}%") | Lead.email.ilike(f"%{search}%"))
    r = await db.execute(q.offset((page-1)*per_page).limit(per_page))
    return r.scalars().all()


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(body: LeadCreate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    l = Lead(consultant_id=user.id, **body.model_dump())
    db.add(l); await db.commit(); await db.refresh(l); return l


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    return await _get(lead_id, user, db)


@router.put("/{lead_id}", response_model=LeadOut)
async def update_lead(lead_id: uuid.UUID, body: LeadUpdate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    l = await _get(lead_id, user, db)
    for k, v in body.model_dump(exclude_none=True).items(): setattr(l, k, v)
    await db.commit(); await db.refresh(l); return l


@router.post("/{lead_id}/convert", response_model=ClientOut)
async def convert_lead(lead_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    lead = await _get(lead_id, user, db)
    if lead.client_id: raise ConflictError("Lead already converted.")
    client = Client(consultant_id=user.id, full_name=lead.full_name, email=lead.email, organization=lead.organization)
    db.add(client); await db.flush()
    lead.client_id = client.id; lead.status = LeadStatus.onboarding
    lead.converted_at = datetime.now(timezone.utc)
    await db.commit(); await db.refresh(client); return client


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    l = await _get(lead_id, user, db); await db.delete(l); await db.commit()