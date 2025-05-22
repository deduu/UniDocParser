# core/pipeline.py
import asyncio
from pathlib import Path
from typing import List
from backend.core.interfaces import Splitter, ElementExtractor, ImageEnhancer, Formatter
from backend.core.types import ExtractionResult, PageResult, ElementResult
from backend.utils.trackers import timeit
import logging

logger = logging.getLogger("pipeline")


class PDFExtractionPipeline:
    def __init__(
        self,
        splitter: Splitter,
        elem_extractor: ElementExtractor,
        img_enhancer: ImageEnhancer,
        formatter: Formatter,
    ):
        self.splitter = splitter
        self.elem_extractor = elem_extractor
        self.img_enhancer = img_enhancer
        self.formatter = formatter

    async def process(self, pdf_path: Path) -> ExtractionResult:
        timings = {}
        # 1) Split
        (pages_bytes, t), = await self.splitter.split(pdf_path)
        timings["split"] = t

        # 2) Per‐page extract + enhance in parallel
        async def handle_page(idx, page_b):
            # text + raw elements
            (text, raw_elements), t1 = await self.elem_extractor.extract(page_b)
            timings.setdefault("extract_elements", []).append(t1)

            # image‐based enhancements
            (new_page_b, token_lens), t2 = await self.img_enhancer.enhance(page_b, raw_elements)
            timings.setdefault("extract_images", []).append(t2)

            # build PageResult placeholder
            els = [
                ElementResult(
                    type=e["type"],
                    bbox=e["bbox"],
                    text=e["text"],
                    metadata={k: v for k, v in e.items() if k not in (
                        "type", "bbox", "text")}
                )
                for e in raw_elements
            ]
            return PageResult(index=idx, text=text, markdown="", elements=els)

        pages_tasks = [
            handle_page(i, b) for i, b in enumerate(pages_bytes)
        ]
        pages: List[PageResult] = await asyncio.gather(*pages_tasks)

        # 3) Format into markdown (or other formats)
        (pages, t3) = await self.formatter.format_text(pages)
        timings["format"] = t3

        return ExtractionResult(
            source=pdf_path.name,
            pages=pages,
            timings=timings
        )
