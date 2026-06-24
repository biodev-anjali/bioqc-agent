import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_consultant
from app.models.all_models import User, Client, Project, Invoice
from app.schemas.all_schemas import ClientCreate, ClientUpdate, ClientOut, ProjectOut, InvoiceOut
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/clients", tags=["clients"])


async def _get(cid: uuid.UUID, user: User, db: AsyncSession) -> Client:
    r = await db.execute(select(Client).where(Client.id == cid, Client.consultant_id == user.id))
    c = r.scalar_one_or_none()
    if not c: raise NotFoundError("Client")
    return c


@router.get("", response_model=list[ClientOut])
async def list_clients(search: str | None = Query(None), page: int = Query(1, ge=1), per_page: int = Query(20, le=100),
                       user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    q = select(Client).where(Client.consultant_id == user.id).order_by(Client.full_name)
    if search:
        q = q.where(Client.full_name.ilike(f"%{search}%") | Client.organization.ilike(f"%{search}%"))
    r = await db.execute(q.offset((page-1)*per_page).limit(per_page))
    return r.scalars().all()


@router.post("", response_model=ClientOut, status_code=201)
async def create_client(body: ClientCreate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    c = Client(consultant_id=user.id, **body.model_dump())
    db.add(c); await db.commit(); await db.refresh(c); return c


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(client_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    return await _get(client_id, user, db)


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(client_id: uuid.UUID, body: ClientUpdate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    c = await _get(client_id, user, db)
    for k, v in body.model_dump(exclude_none=True).items(): setattr(c, k, v)
    await db.commit(); await db.refresh(c); return c


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    c = await _get(client_id, user, db); await db.delete(c); await db.commit()


@router.get("/{client_id}/projects", response_model=list[ProjectOut])
async def client_projects(client_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    await _get(client_id, user, db)
    r = await db.execute(select(Project).where(Project.client_id == client_id, Project.consultant_id == user.id).order_by(Project.created_at.desc()))
    return r.scalars().all()


@router.get("/{client_id}/invoices", response_model=list[InvoiceOut])
async def client_invoices(client_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    await _get(client_id, user, db)
    r = await db.execute(select(Invoice).where(Invoice.client_id == client_id, Invoice.created_by == user.id).order_by(Invoice.created_at.desc()))
    return r.scalars().all()