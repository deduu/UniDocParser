"""create extractor tables

Revision ID: a715cd083d0f
Revises: 
Create Date: 2025-09-01 13:36:21.994126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = 'a715cd083d0f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # extract_jobs
    op.create_table(
        "extract_jobs",
        sa.Column("id", sa.String(), primary_key=True,
                  default=lambda: str(uuid.uuid4())),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column("created_by_user_id", sa.String(),
                  nullable=False, index=True),
        sa.Column("source_file_name", sa.String(), nullable=True),
        sa.Column("source_file_url", sa.Text(), nullable=True),
        sa.Column("options_json", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(), nullable=False,
                  server_default="queued"),
        sa.Column("page_count_est", sa.Integer(), nullable=True),
        sa.Column("page_count_actual", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(
        ), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed','canceled')", name="ck_extract_jobs_status"),
    )
    op.create_index(
        "ix_jobs_tenant_status_created",
        "extract_jobs",
        ["tenant_id", "status", "created_at"],
    )

    # extract_results
    op.create_table(
        "extract_results",
        sa.Column("job_id", sa.String(), sa.ForeignKey(
            "extract_jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("json_url", sa.Text(), nullable=True),
        sa.Column("markdown_url", sa.Text(), nullable=True),
        sa.Column("preview_png_url", sa.Text(), nullable=True),
        sa.Column("bytes_stored", sa.Integer(), nullable=True),
        sa.Column("processing_time", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # extract_pages
    op.create_table(
        "extract_pages",
        sa.Column("id", sa.String(), primary_key=True,
                  default=lambda: str(uuid.uuid4())),
        sa.Column("job_id", sa.String(), sa.ForeignKey(
            "extract_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=True),
        sa.Column("elements", postgresql.JSONB(
            astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pages_jobidx", "extract_pages", [
                    "job_id", "page_index"], unique=True)


def downgrade():
    op.drop_index("ix_pages_jobidx", table_name="extract_pages")
    op.drop_table("extract_pages")

    op.drop_table("extract_results")

    op.drop_index("ix_jobs_tenant_status_created", table_name="extract_jobs")
    op.drop_table("extract_jobs")
