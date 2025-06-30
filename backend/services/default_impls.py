# services/default_impls.py
import asyncio
from pathlib import Path
from backend.core.interfaces import Splitter, ElementExtractor, ImageEnhancer, Formatter
from backend.utils.trackers import log_processing_time as timeit
from backend.services.file_handler import handle_file    # your existing
from backend.services.element_extractor import extract_elements
from backend.services.image_extractor import extract_images
from backend.services.output_formatter import format_extracted_text, format_markdown


class DefaultSplitter(Splitter):
    @timeit("handle_file")
    async def split(self, pdf_path: Path):
        # wrap sync call in thread
        loop = asyncio.get_event_loop()
        pages = await loop.run_in_executor(None, handle_file, str(pdf_path))
        return pages


class DefaultElementExtractor(ElementExtractor):
    @timeit("extract_elements")
    async def extract(self, page_bytes):
        # returns (processed_pages, figure_list) in your old API,
        # so adapt it per-page
        pages, figures = await asyncio.get_event_loop().run_in_executor(
            None, extract_elements, [page_bytes]
        )
        # extract_elements returns lists, but here we only passed one page.
        text = pages[0]["text"]
        raw_els = pages[0]["elements"]
        return text, raw_els


class DefaultImageEnhancer(ImageEnhancer):
    @timeit("extract_images")
    async def enhance(self, page_bytes, raw_elements):
        # here you’d pass the whole batch; adapt for single page:
        (new_pages, token_lengths), = await asyncio.get_event_loop().run_in_executor(
            None, extract_images, [page_bytes], raw_elements
        )
        return new_pages[0], token_lengths


class DefaultFormatter(Formatter):
    @timeit("format_text")
    async def format_text(self, pages):
        # two‐step formatting: plain text then markdown
        loop = asyncio.get_event_loop()
        pages = await loop.run_in_executor(None, format_extracted_text, pages)
        pages = await loop.run_in_executor(None, format_markdown, pages)
        return pages
