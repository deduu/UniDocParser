# backend/pipeline/steps/extract_images_step.py
from backend.pipeline.steps.step import PipelineStep
from backend.pipeline.context import PDFContext, Page
from backend.services.image_extractor import extract_images


class ExtractImagesStep(PipelineStep):
    """Replace figure placeholders with real images + DL metadata."""

    def __init__(self):
        super().__init__(name="Extract Images")

    def run(self, ctx: PDFContext) -> PDFContext:
        if not ctx.pages:
            raise ValueError(
                "ExtractImagesStep: ctx.pages is empty – did you run Split & ExtractElements?")

        if not ctx.figure_list:
            # Often fine – maybe the PDF had no figures – but warn so you notice in logs
            print(
                "ExtractImagesStep: ctx.figure_list is empty, skipping image enrichment")

        # Convert to the raw structure your helper expects
        raw_pages = [p.dict() for p in ctx.pages]
        figure_list_raw = [f.dict() for f in ctx.figure_list]

        # Run the (blocking) extraction
        updated_pages_raw = extract_images(raw_pages, figure_list_raw)

        # Wrap back into Page models and store
        ctx.pages = [Page(**page_data) for page_data in updated_pages_raw]

        return ctx
