import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_consultant
from app.models.all_models import Proposal, AIGenerationLog, User
from app.schemas.all_schemas import ProposalGenerateRequest, ProposalUpdate, ProposalOut
from app.services.ai_service import generate_proposal, calculate_pricing
from app.core.exceptions import NotFoundError
from app.core.constants import ProposalStatus

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("", response_model=list[ProposalOut])
async def list_proposals(user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Proposal).where(Proposal.created_by == user.id).order_by(Proposal.created_at.desc()))
    return r.scalars().all()


@router.post("/generate", response_model=ProposalOut, status_code=201)
async def generate(body: ProposalGenerateRequest, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    pricing = calculate_pricing(body.sequencing_type, body.sample_count)
    content, model, tokens = await generate_proposal(
        sequencing_type=body.sequencing_type, sample_count=body.sample_count,
        timeline_days=body.timeline_days, client_goal=body.client_goal,
        consultant_name=body.consultant_name or user.full_name,
        organism=body.organism, pricing=pricing,
    )
    p = Proposal(
        lead_id=body.lead_id, client_id=body.client_id, created_by=user.id,
        title=content.get("title", "Bioinformatics Proposal"),
        sequencing_type=body.sequencing_type, sample_count=body.sample_count,
        timeline_days=body.timeline_days, client_goal=body.client_goal,
        generated_content=content, pricing_basic=pricing["basic"],
        pricing_standard=pricing["standard"], pricing_premium=pricing["premium"],
        recommended_tier=content.get("recommended_tier", "standard"),
        ai_model=model, ai_tokens_used=tokens,
    )
    db.add(p)
    await db.flush()
    db.add(AIGenerationLog(user_id=user.id, entity_type="proposal", entity_id=p.id, model=model,
                           tokens_input=tokens//2, tokens_output=tokens//2, success=True))
    await db.commit(); await db.refresh(p); return p


@router.get("/{proposal_id}", response_model=ProposalOut)
async def get_proposal(proposal_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Proposal).where(Proposal.id == proposal_id, Proposal.created_by == user.id))
    p = r.scalar_one_or_none()
    if not p: raise NotFoundError("Proposal")
    return p


@router.put("/{proposal_id}", response_model=ProposalOut)
async def update_proposal(proposal_id: uuid.UUID, body: ProposalUpdate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Proposal).where(Proposal.id == proposal_id, Proposal.created_by == user.id))
    p = r.scalar_one_or_none()
    if not p: raise NotFoundError("Proposal")
    for k, v in body.model_dump(exclude_none=True).items(): setattr(p, k, v)
    await db.commit(); await db.refresh(p); return p


@router.post("/{proposal_id}/send", response_model=ProposalOut)
async def send_proposal(proposal_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Proposal).where(Proposal.id == proposal_id, Proposal.created_by == user.id))
    p = r.scalar_one_or_none()
    if not p: raise NotFoundError("Proposal")
    p.status = ProposalStatus.sent; p.sent_at = datetime.now(timezone.utc)
    await db.commit(); await db.refresh(p); return p