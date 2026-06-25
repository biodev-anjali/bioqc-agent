import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PARSED = "parsed"
    FAILED = "failed"


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False),
        nullable=False,
        default=JobStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    qc_result: Mapped["QCResult | None"] = relationship(
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )


class QCResult(Base):
    __tablename__ = "qc_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    total_sequences: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_length: Mapped[str] = mapped_column(String(64), nullable=False)
    gc_percent: Mapped[float] = mapped_column(Float, nullable=False)
    per_base_quality_status: Mapped[str] = mapped_column(String(16), nullable=False)
    per_sequence_quality_status: Mapped[str] = mapped_column(String(16), nullable=False)
    adapter_content_status: Mapped[str] = mapped_column(String(16), nullable=False)
    overrepresented_sequences_status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job: Mapped["AnalysisJob"] = relationship(back_populates="qc_result")
