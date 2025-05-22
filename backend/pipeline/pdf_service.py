from backend.pipeline.extractor import PDFExtractionPipeline

from backend.pipeline.context import PDFContext

from backend.pipeline.steps.ocr_step import OCRStep
from backend.pipeline.steps.split_step import SplitStep
from backend.pipeline.steps.extract_elements_step import ExtractElementsStep
from backend.pipeline.steps.extract_images_step import ExtractImagesStep
from backend.pipeline.steps.format_extracted_step import FormatExtractedTextStep
from backend.pipeline.steps.markdown_step import MarkdownStep


# app/services/pdf_service.py
class PDFService:
    def __init__(self):
        self.ocr_pipeline = PDFExtractionPipeline([
            OCRStep(output_dir="./tmp/ocr")
        ])
        self.split_pipeline = PDFExtractionPipeline([
            SplitStep()
        ])
        self.full_pipeline = PDFExtractionPipeline([
            SplitStep(),
            ExtractElementsStep(),
            ExtractImagesStep(),
            FormatExtractedTextStep(),
            MarkdownStep()
        ])

    async def ocr(self, pdf_path: str) -> PDFContext:
        return await self.ocr_pipeline.process(pdf_path)

    async def split(self, pdf_path: str) -> PDFContext:
        return await self.split_pipeline.process(pdf_path)

    async def full(self, pdf_path: str) -> PDFContext:
        return await self.full_pipeline.process(pdf_path)
