# backend/extraction/base.py
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List

from .config import ExtractionConfig
from backend.core.config import settings

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for file extractors."""

    def __init__(self, config: ExtractionConfig):
        self.config = config

    @abstractmethod
    def extract(self, file_path: Path) -> List[Any]:
        """Extract elements from file."""
        raise NotImplementedError

    def _get_output_directory(self, file_path: Path) -> str:
        """Generate and ensure output directory for extracted images."""
        file_name = file_path.stem
        out_dir = os.path.join(settings.IMG_FIGURES_DIR, "figures", f"{file_name}_figures")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            logger.warning("Failed to create output directory %s: %s", out_dir, e)
        return out_dir
