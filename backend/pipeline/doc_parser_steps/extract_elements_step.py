# backend/pipeline/steps/extract_elements_step.py
from typing import Optional
from backend.pipeline.doc_parser_steps.doc_parser_step import DocParserStep
from backend.pipeline.doc_parser_steps.context import DocParserContext, Page, Figure
# your existing function

# from backend.services.element_extractor import extract_elements
from backend.extraction.services.element_extractor import extract_elements
from dataclasses import asdict


def to_builtin(obj):
    try:
        import numpy as np
    except Exception:
        np = None

    if np is not None and isinstance(obj, np.generic):
        return obj.item()
    if np is not None and isinstance(obj, np.ndarray):
        return [to_builtin(v) for v in obj.tolist()]  # small arrays like bbox

    if isinstance(obj, dict):
        return {k: to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_builtin(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(to_builtin(v) for v in obj)  # <- preserve tuple
    return obj


class ExtractElementsStep(DocParserStep):
    def __init__(self):
        super().__init__(name="Extract Elements")

    def run(self, ctx: DocParserContext, job_id: Optional[str] = None) -> DocParserContext:
        # 1. Convert our Page models into the raw dicts your extractor expects
        raw_pages = [p.dict() for p in ctx.pages]
        # print(f"raw_pages: {raw_pages}")
        # print(f"ctx.path: {ctx.pdf_path}")

        # 2. Run extraction, getting back updated pages + a flat list of figures
        updated_pages_data, figure_list_data = extract_elements(
            raw_pages, ctx.file_path)

        # for i, page in enumerate(updated_pages_data):
        # print(f"page {i}: {page}")
        # print(f"page {i}: {page["coord_width"]}x{page["coord_height"]}")
        # print(f"page {i}: {page['markdown']}")

        # 2) Normalize numpy → builtins (deep-walk)
        updated_pages_data = to_builtin(updated_pages_data)
        figure_list_data = to_builtin(figure_list_data)

        # 3) Build models (Pydantic BaseModel assumed)
        ctx.pages = [Page(**p) for p in updated_pages_data]  # p is dictionary
        ctx.figure_list = [Figure.model_validate(
            f) for f in figure_list_data]  # f is object

        return ctx
