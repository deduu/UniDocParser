# backend/pipeline/steps/extract_elements_step.py

from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext, Page, Figure
# your existing function

from backend.services.element_extractor import extract_elements


class ExtractElementsStep(DocParserStep):
    def __init__(self):
        super().__init__(name="Extract Elements")

    def run(self, ctx: DocParserContext) -> DocParserContext:
        # 1. Convert our Page models into the raw dicts your extractor expects
        raw_pages = [p.dict() for p in ctx.pages]
        # print(f"raw_pages: {raw_pages}")

        # 2. Run extraction, getting back updated pages + a flat list of figures
        updated_pages_data, figure_list_data = extract_elements(raw_pages, ctx.user_id, ctx.folder, ctx.file_path)

        ctx.pages = [Page(**p) for p in updated_pages_data]
        ctx.figure_list = [Figure(**f) for f in figure_list_data]
        return ctx
