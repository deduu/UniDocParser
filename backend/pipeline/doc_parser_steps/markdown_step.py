# backend/pipeline/steps/markdown_step.py
import os
import logging
from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext, Page
from backend.services.output_formatter import format_markdown  # same file as above

logger = logging.getLogger(__name__)


class MarkdownStep(DocParserStep):
    """Turn each page's cleaned text into conversational Markdown."""

    def __init__(self, formatter_model):
        super().__init__(name="Format Markdown")
        self.formatter_model = formatter_model

    def run(self, ctx: DocParserContext) -> DocParserContext:
        if not ctx.pages:
            raise RuntimeError(
                "MarkdownStep: pages are missing - run previous steps first")

        pdf_name = os.path.basename(ctx.file_path)

        raw_pages = [p.model_dump(mode="python") for p in ctx.pages]
        updated_pages_raw = format_markdown(self.formatter_model, raw_pages, pdf_name)

        ctx.pages = [Page(**p) for p in updated_pages_raw]

        # logger.info("%s completed", self.name)
        return ctx
