from __future__ import annotations
from pathlib import Path
from typing import List
import logging
from PIL import Image

from backend.schemas.ingest import PageMetadata
from backend.utils.helpers import save_jpeg
from backend.utils.trackers import log_processing_time

logger = logging.getLogger(__name__)

class ExcelHandler:
    def __init__(self, img_pages_dir: Path, max_side: int, jpeg_quality: int):
        self.img_pages_dir = img_pages_dir
        self.max_side = max_side
        self.jpeg_quality = jpeg_quality

    @log_processing_time
    def handle(self, xls_path: Path) -> List[PageMetadata]:
        pages: List[PageMetadata] = []
        try:
            import openpyxl
        except Exception as e:
            logger.error("openpyxl required for Excel parsing: %s", e)
            return []

        try:
            wb = openpyxl.load_workbook(xls_path, read_only=True, data_only=True)
        except Exception as e:
            logger.error("Failed to load workbook: %s", e)
            return []

        excel_to_img_ok = True
        try:
            import excel2img  # type: ignore
        except Exception:
            excel_to_img_ok = False
            logger.warning("excel2img not installed — will create placeholders.")

        base = xls_path.stem
        for i, sheet_name in enumerate(wb.sheetnames):
            out_path = self.img_pages_dir / f"{base}_sheet{i+1}_{sheet_name}.jpeg"
            if excel_to_img_ok:
                try:
                    tmp_png = out_path.with_suffix(".png")
                    excel2img.export_img(xls_path.as_posix(), tmp_png.as_posix(), sheet_name)
                    img = Image.open(tmp_png)
                    img.thumbnail((self.max_side, self.max_side))
                    save_jpeg(img, out_path, quality=self.jpeg_quality)
                    try:
                        tmp_png.unlink(missing_ok=True)
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning("excel2img failed for %s: %s", sheet_name, e)
                    with Image.new("RGB", (1200, 675), (245, 245, 245)) as ph:
                        save_jpeg(ph, out_path, quality=70)
            else:
                with Image.new("RGB", (1200, 675), (245, 245, 245)) as ph:
                    save_jpeg(ph, out_path, quality=70)

            pages.append(PageMetadata(index=i, image=out_path.as_posix(), elements=[]))
        logger.info("Excel sheets processed: %d", len(pages))
        return pages