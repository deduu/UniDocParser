# core/interfaces.py
import abc
from typing import List, Any
from pathlib import Path
from backend.core.types import PageResult


class Splitter(abc.ABC):
    @abc.abstractmethod
    async def split(self, pdf_path: Path) -> List[bytes]:
        """Return one raw page (e.g. image or bytes) per entry."""


class ElementExtractor(abc.ABC):
    @abc.abstractmethod
    async def extract(self, page: bytes) -> tuple[str, list[dict[str, Any]]]:
        """
        Return (plain_text, list_of_raw_element_dicts)
        where each element dict has at least: type, bbox, text, plus any raw metadata.
        """


class ImageEnhancer(abc.ABC):
    @abc.abstractmethod
    async def enhance(self, page: bytes, elements: List[dict]) -> tuple[bytes, List[int]]:
        """
        Return (optionally_modified_page, [token_counts_per_figure])
        """


class Formatter(abc.ABC):
    @abc.abstractmethod
    async def format_text(self, pages: List[PageResult]) -> List[PageResult]:
        """Populate or enrich the markdown field (or other formats)."""
