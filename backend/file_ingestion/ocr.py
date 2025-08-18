from __future__ import annotations
from pathlib import Path
import logging
import ocrmypdf

from backend.utils.helpers import ensure_dir

logger = logging.getLogger(__name__)

class OCRService:
    def ocr_pdf_to_pdf(self, pdf_path: str | Path, output_dir: str | Path) -> str | None:
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        ensure_dir(output_dir)
        new_pdf_path = output_dir / f"{pdf_path.stem}_ocr.pdf"
        try:
            ocrmypdf.ocr(
                pdf_path.as_posix(),
                new_pdf_path.as_posix(),
                use_threads=True,
                force_ocr=True,
                output_type="pdf",
                skip_big=0,
                optimize=3,
            )
            logger.info("OCR complete: %s", new_pdf_path)
            return new_pdf_path.as_posix()
        except ocrmypdf.exceptions.PriorOcrFoundError:
            logger.info("File already OCR'd: %s", pdf_path)
            return pdf_path.as_posix()
        except Exception as e:
            logger.exception("OCR failed for %s: %s", pdf_path, e)
            return None