# backend/pipeline/extractor.py
import asyncio
from typing import List
import time
from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocParserPipeline:
    def __init__(self, steps: List[DocParserStep]):
        self.steps = steps

    async def process(self, pdf_path: str) -> DocParserContext:
        ctx = DocParserContext(pdf_path=pdf_path)

        start = time.time()

        for step in self.steps:
            t0 = time.time()
            # offload blocking run() into a thread
            ctx = await asyncio.to_thread(step.run, ctx)
            logger.info(
                f"{step.name} took {time.time() - t0:.2f}s")

        total = time.time() - start
        ctx = ctx.copy(update={"processing_time": total})
        logger.info(f"Total pipeline time: {total:.2f}s")
        return ctx
