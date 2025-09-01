# backend/db/doc_parser.py
import uuid
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, backref
from sqlalchemy.sql import func

Base = declarative_base()

class ExtractJob(Base):
    __tablename__ = "extract_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    created_by_user_id = Column(String, nullable=False, index=True)

    source_file_name = Column(String)
    source_file_url  = Column(Text)
    options_json     = Column(JSONB, nullable=False, default=dict)

    status = Column(String, nullable=False, default="queued")
    page_count_est    = Column(Integer)
    page_count_actual = Column(Integer)
    error_message     = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pages  = relationship("ExtractPage", back_populates="job", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','canceled')",
            name="ck_extract_jobs_status"
        ),
        Index("ix_jobs_tenant_status_created", "tenant_id", "status", "created_at"),
    )


class ExtractResult(Base):
    __tablename__ = "extract_results"

    job_id = Column(String, ForeignKey("extract_jobs.id", ondelete="CASCADE"), primary_key=True)
    # Store artifacts in object storage; keep only URLs/keys here
    json_url      = Column(Text, nullable=True)     # DocParserContextOut as JSON file
    markdown_url  = Column(Text, nullable=True)
    preview_png_url = Column(Text, nullable=True)   # optional combined preview
    bytes_stored  = Column(Integer, nullable=True)

    processing_time = Column(Integer, nullable=True)  # seconds (rounded)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    job = relationship("ExtractJob", backref=backref("result", uselist=False, cascade="all, delete-orphan"))
    
class ExtractPage(Base):
    __tablename__ = "extract_pages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("extract_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    page_index = Column(Integer, nullable=False)
    image_url  = Column(Text)
    text       = Column(Text)
    markdown   = Column(Text)
    elements   = Column(JSONB, nullable=True)  # or default=list if you prefer

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("ExtractJob", back_populates="pages")

    __table_args__ = (
        Index("ix_pages_jobidx", "job_id", "page_index", unique=True),
    )
