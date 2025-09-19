# backend/pipeline/steps/markdown_step.py
import os
import logging
from typing import Optional
from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext, Page
from backend.services.output_formatter import format_markdown  # same file as above
from backend.services.vlm_extractor import vlm_extract

logger = logging.getLogger(__name__)


class VLMExtractorStep(DocParserStep):
    """Turn each page's cleaned text into conversational Markdown."""

    def __init__(self):
        super().__init__(name="Format Markdown")

    def run(self, ctx: DocParserContext, job_id: Optional[str] = None) -> DocParserContext:
        if not ctx.pages:
            raise RuntimeError(
                "MarkdownStep: pages are missing - run previous steps first")

        pdf_name = os.path.basename(ctx.file_path)

        raw_pages = [p.model_dump(mode="python") for p in ctx.pages]
        updated_pages_raw = vlm_extract(raw_pages, pdf_name)

        ctx.pages = [Page(**p) for p in updated_pages_raw]

        logger.info("%s completed", self.name)
        return ctx
