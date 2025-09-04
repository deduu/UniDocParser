"""Add composite index for user deletes; ensure CASCADE FKs

Revision ID: f5751eab9034
Revises: a715cd083d0f
Create Date: 2025-09-04 15:23:57.053822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5751eab9034'
down_revision: Union[str, Sequence[str], None] = 'a715cd083d0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.execute("SET lock_timeout TO '5s'")
    op.execute("SET statement_timeout TO '5min'")

    # 1) Composite index for (tenant_id, created_by_user_id)
    op.create_index(
        "ix_jobs_tenant_user",
        "extract_jobs",
        ["tenant_id", "created_by_user_id"],
        unique=False,
    )
    # 2) Ensure ON DELETE CASCADE on child FKs
    # Drop + recreate FK for extract_pages.job_id
    # drop old constraints (adjust names if needed)
    op.drop_constraint("extract_pages_job_id_fkey",
                       "extract_pages", type_="foreignkey")
    op.drop_constraint("extract_results_job_id_fkey",
                       "extract_results", type_="foreignkey")

    # add CASCADE with NOT VALID (acquires lighter locks)
    op.execute("""
        ALTER TABLE extract_pages
        ADD CONSTRAINT extract_pages_job_id_fkey
        FOREIGN KEY (job_id) REFERENCES extract_jobs(id) ON DELETE CASCADE NOT VALID
    """)
    op.execute("""
        ALTER TABLE extract_results
        ADD CONSTRAINT extract_results_job_id_fkey
        FOREIGN KEY (job_id) REFERENCES extract_jobs(id) ON DELETE CASCADE NOT VALID
    """)

    # validate separately, still safe to do with autocommit+timeouts
    with op.get_context().autocommit_block():
        op.execute("SET lock_timeout TO '5s'")
        op.execute(
            "ALTER TABLE extract_pages VALIDATE CONSTRAINT extract_pages_job_id_fkey")
        op.execute(
            "ALTER TABLE extract_results VALIDATE CONSTRAINT extract_results_job_id_fkey")

    # 3) OPTIONAL: add FK from extract_jobs.created_by_user_id -> users.id
    #    Uncomment if you have a users table and types match.
    # op.create_foreign_key(
    #     "fk_extract_jobs_user",
    #     source_table="extract_jobs",
    #     referent_table="users",
    #     local_cols=["created_by_user_id"],
    #     remote_cols=["id"],
    #     ondelete="CASCADE",  # or "SET NULL" (and make column nullable=True)
    # )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index("ix_jobs_tenant_user",
                      table_name="extract_jobs", postgresql_concurrently=True)

    # (recreate your previous FKs if you had them without CASCADE)
    op.drop_constraint("extract_results_job_id_fkey",
                       "extract_results", type_="foreignkey")
    op.drop_constraint("extract_pages_job_id_fkey",
                       "extract_pages", type_="foreignkey")
    op.create_foreign_key(
        "extract_results_job_id_fkey",
        "extract_results", "extract_jobs", ["job_id"], ["id"], ondelete=None
    )
    op.create_foreign_key(
        "extract_pages_job_id_fkey",
        "extract_pages", "extract_jobs", ["job_id"], ["id"], ondelete=None
    )
