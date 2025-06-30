# backend/pipeline/steps/split_step.py

from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext, Page
from backend.services.file_handler import handle_file


class SplitStep(DocParserStep):
    def __init__(self):
        super().__init__(name="Split")

    def run(self, ctx: DocParserContext) -> DocParserContext:
        # 1. Split the PDF into raw page metadata
        raw_pages = handle_file(ctx.user_id, ctx.folder, ctx.file_path)

        # 2. Convert each dict into a Page model (elements defaults to [])
        pages = [Page(**page_data) for page_data in raw_pages]

        # print(f"pages split: {pages}")
        # 3. Update the context
        ctx.pages = pages

        return ctx
