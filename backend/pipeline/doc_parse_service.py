from backend.pipeline.doc_parser_pipeline import DocParserPipeline

from backend.pipeline.doc_parser_steps.context import DocParserContext

from backend.pipeline.doc_parser_steps.ocr_step import OCRStep
from backend.pipeline.doc_parser_steps.split_step import SplitStep
from backend.pipeline.doc_parser_steps.extract_elements_step import ExtractElementsStep
from backend.pipeline.doc_parser_steps.extract_images_step import ExtractImagesStep
from backend.pipeline.doc_parser_steps.format_extracted_step import FormatExtractedTextStep
from backend.pipeline.doc_parser_steps.markdown_step import MarkdownStep


# app/services/pdf_service.py
class DocParserService:
    def __init__(self):
        self.ocr_pipeline = DocParserPipeline([
            OCRStep(output_dir="./tmp/ocr")
        ])
        self.split_pipeline = DocParserPipeline([
            SplitStep()
        ])
        self.extract_only_pipeline = DocParserPipeline([    
            SplitStep(),
            ExtractElementsStep(),
            ExtractImagesStep(),
            FormatExtractedTextStep(),])
        
        self.full_pipeline = DocParserPipeline([
            SplitStep(),
            ExtractElementsStep(),
            ExtractImagesStep(),
            FormatExtractedTextStep(),
            MarkdownStep()
        ])

    async def ocr(self, user_id: str, folder: str, file_path: str) -> DocParserContext:
        return await self.ocr_pipeline.process(user_id=user_id, folder=folder, file_path=file_path)

    async def split(self, user_id: str, folder: str, file_path: str) -> DocParserContext:
        return await self.split_pipeline.process(user_id=user_id, folder=folder, file_path=file_path)

    async def extract_only(self, user_id: str, folder: str, file_path: str) -> DocParserContext:
        return await self.extract_only_pipeline.process(user_id=user_id, folder=folder, file_path=file_path)

    async def full(self, user_id: str, folder: str, file_path: str) -> DocParserContext:
        return await self.full_pipeline.process(user_id=user_id, folder=folder, file_path=file_path)
