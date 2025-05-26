# backend/pipeline/steps/format_extracted_text_step.py
import logging
from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext, Page
from backend.services.output_formatter import format_extracted_text

logger = logging.getLogger(__name__)


class FormatExtractedTextStep(DocParserStep):
    """
    • Receives ctx.pages (List[Page])
    • Calls the blocking helper `format_extracted_text`
    • Stores the cleaned text back into ctx.pages
    """

    def __init__(self):
        super().__init__(name="Format Extracted Text")

    def run(self, ctx: DocParserContext) -> DocParserContext:
        if not ctx.pages:
            raise RuntimeError(
                "FormatExtractedTextStep: pages are missing – run previous steps first")

        # 1. Convert Page models -> plain python dicts (PIL images kept as is)
        raw_pages = [p.model_dump(mode="python") for p in ctx.pages]

        # 2. Run the blocking formatter
        updated_pages_raw = format_extracted_text(raw_pages)

        # 3. Re-wrap into Page models
        ctx.pages = [Page(**page_data) for page_data in updated_pages_raw]

        # logger.info("%s completed (pages=%d)", self.name, len(ctx.pages))
        return ctx
