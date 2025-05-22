# backend/pipeline/steps/split_step.py

from backend.pipeline.steps.step import PipelineStep
from backend.pipeline.context import PDFContext, Page
from backend.services.file_handler import split_pdf


class SplitStep(PipelineStep):
    def __init__(self):
        super().__init__(name="Split")

    def run(self, ctx: PDFContext) -> PDFContext:
        # 1. Split the PDF into raw page metadata
        raw_pages = split_pdf(ctx.pdf_path)

        # 2. Convert each dict into a Page model (elements defaults to [])
        pages = [Page(**page_data) for page_data in raw_pages]

        # 3. Update the context
        ctx.pages = pages

        return ctx
