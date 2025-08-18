from __future__ import annotations
from pathlib import Path
from typing import List
import logging
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.schemas.ingest import PageMetadata
from backend.utils.helpers import resize_img, save_jpeg
from backend.utils.trackers import log_processing_time

logger = logging.getLogger(__name__)

class ImageHandler:
    def __init__(self, img_pages_dir: Path, max_side: int, jpeg_quality: int):
        self.img_pages_dir = img_pages_dir
        self.max_side = max_side
        self.jpeg_quality = jpeg_quality

    def _target(self, src: Path) -> Path:
        return self.img_pages_dir / f"{src.stem}.jpeg"
    @log_processing_time
    def handle(self, img_path: Path) -> List[PageMetadata]:
        try:
            img = Image.open(img_path)
        except UnidentifiedImageError:
            logger.error("Unsupported or corrupted image: %s", img_path)
            return []

        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        try:
            resized = resize_img(img, size=self.max_side)
        except Exception:
            resized = img.copy()
            resized.thumbnail((self.max_side, self.max_side))

        out_path = self._target(img_path)
        save_jpeg(resized, out_path, quality=self.jpeg_quality)
        return [PageMetadata(index=0, image=out_path.as_posix(), elements=[])]