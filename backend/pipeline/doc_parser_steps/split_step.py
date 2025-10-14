# backend/pipeline/steps/split_step.py
import uuid  #
import logging
from dataclasses import asdict
from typing import Optional
from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext, Page
from backend.services.file_handler import handle_file
from backend.file_ingestion.file_ingest import ingest
from backend.utils.logger import safe_context_dump

logger = logging.getLogger(__name__)


class SplitStep(DocParserStep):
    def __init__(self):
        super().__init__(name="Split")

    def run(self, ctx: DocParserContext, job_id: Optional[str] = None) -> DocParserContext:
        # 1. Split the PDF into raw page metadata
        # raw_pages = handle_file(ctx.pdf_path)
        resolved_job_id = job_id or getattr(
            ctx, "job_id", None) or f"adhoc-{uuid.uuid4().hex[:12]}"

        raw_pages = ingest.handle_file(ctx.file_path, resolved_job_id)

        logger.info(f"raw_pages: {raw_pages}")

        # 2. Convert each dict into a Page model (elements defaults to [])
        # pages = [Page(**asdict(page_data)) for page_data in raw_pages]
        pages = [
            Page(**{**asdict(p), "elements": p.elements or []})
            for p in raw_pages
        ]

        # print(f"pages split: {pages}")
        # 3. Update the context
        ctx.pages = pages
        # logger.info(f"ctx:\n{ctx.model_dump_json(indent=2)}")
        logger.info(f"[{self.name}] ctx summary:\n{safe_context_dump(ctx)}")

        # print(f"handler: {ctx.file_path}")

        # Persist the resolved job_id back to context if not set
        # if not getattr(ctx, "job_id", None):
        #     setattr(ctx, "job_id", resolved_job_id)

        return ctx
