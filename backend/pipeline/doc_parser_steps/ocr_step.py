# backend/pipeline/steps/ocr_step.py
import os
from pathlib import Path
from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext
from backend.services.file_handler import ocr_pdf_to_pdf


class OCRStep(DocParserStep):
    """Run Tesseract/Poppler OCR on the PDF and store the new path in ctx."""

    def __init__(self, output_dir: str | Path):
        super().__init__(name="OCR")
        self.output_dir = Path(output_dir)

    def run(self, ctx: DocParserContext) -> DocParserContext:
        # 1. Skip if OCR already done (idempotent pipeline)
        if ctx.ocr_pdf_path:
            return ctx

        # 2. Make sure tmp dir exists
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # 3. Perform blocking OCR
        ocr_path = ocr_pdf_to_pdf(ctx.pdf_path, self.output_dir)

        # 4. Update context (Pydantic v2 -> model_copy)
        return ctx.model_copy(
            update={
                "ocr_pdf_path": str(ocr_path),
                # ← downstream steps now use OCR’d file
                "pdf_path":     str(ocr_path)
            }
        )
