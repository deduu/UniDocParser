# backend/pipeline/steps/extract_elements_step.py

from backend.pipeline.steps.step import PipelineStep
from backend.pipeline.context import PDFContext, Page, Figure
# your existing function

from backend.services.element_extractor import extract_elements


class ExtractElementsStep(PipelineStep):
    def __init__(self):
        super().__init__(name="Extract Elements")

    def run(self, ctx: PDFContext) -> PDFContext:
        # 1. Convert our Page models into the raw dicts your extractor expects
        raw_pages = [p.dict() for p in ctx.pages]
        print(raw_pages[0]["image"])

        # 2. Run extraction, getting back updated pages + a flat list of figures
        updated_pages_data, figure_list_data = extract_elements(raw_pages)

        ctx.pages = [Page(**p) for p in updated_pages_data]
        ctx.figure_list = [Figure(**f) for f in figure_list_data]
        return ctx
