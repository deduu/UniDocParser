# core/types.py
from pathlib import Path
from typing import List, Any
from pydantic import BaseModel


class ElementResult(BaseModel):
    type: str
    bbox: Any
    text: str
    metadata: dict = {}


class PageResult(BaseModel):
    index: int
    text: str
    markdown: str
    elements: List[ElementResult]


class ExtractionResult(BaseModel):
    source: str
    pages: List[PageResult]
    timings: dict
