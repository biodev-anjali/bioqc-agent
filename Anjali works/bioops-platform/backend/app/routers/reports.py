import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_consultant
from app.models.all_models import Report, AIGenerationLog, User
from app.schemas.all_schemas import ReportGenerateRequest, ReportUpdate, ReportApprove, ReportOut
from app.services.ai_service import generate_report
from app.core.exceptions import NotFoundError, ForbiddenError

router = APIRouter(prefix="/reports", tags=["reports"])
VALID = {"qc_summary", "methods", "interpretation", "full_report", "client_summary"}


@router.post("/generate", response_model=ReportOut, status_code=201)
async def generate(body: ReportGenerateRequest, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    if body.report_type not in VALID:
        raise ForbiddenError(f"Invalid report_type. Valid: {VALID}")
    draft, model, tokens = await generate_report(body.report_type, body.context)
    r = Report(project_id=body.project_id, created_by=user.id, report_type=body.report_type,
               draft_content=draft, is_approved=False, ai_model=model, ai_tokens_used=tokens,
               inputs_snapshot=body.context)
    db.add(r)
    await db.flush()
    db.add(AIGenerationLog(user_id=user.id, entity_type="report", entity_id=r.id, model=model,
                           tokens_input=tokens//2, tokens_output=tokens//2, success=True))
    await db.commit(); await db.refresh(r); return r


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: uuid.UUID, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Report).where(Report.id == report_id, Report.created_by == user.id))
    r = res.scalar_one_or_none()
    if not r: raise NotFoundError("Report")
    return r


@router.put("/{report_id}", response_model=ReportOut)
async def update_report(report_id: uuid.UUID, body: ReportUpdate, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Report).where(Report.id == report_id, Report.created_by == user.id))
    r = res.scalar_one_or_none()
    if not r: raise NotFoundError("Report")
    if r.is_approved: raise ForbiddenError("Cannot edit approved report.")
    for k, v in body.model_dump(exclude_none=True).items(): setattr(r, k, v)
    await db.commit(); await db.refresh(r); return r


@router.post("/{report_id}/approve", response_model=ReportOut)
async def approve_report(report_id: uuid.UUID, body: ReportApprove, user: User = Depends(require_consultant), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Report).where(Report.id == report_id, Report.created_by == user.id))
    r = res.scalar_one_or_none()
    if not r: raise NotFoundError("Report")
    r.approved_content = body.approved_content
    r.is_approved = True; r.approved_at = datetime.now(timezone.utc)
    await db.commit(); await db.refresh(r); return r