

from pathlib import Path, PurePath
import asyncio
import logging
import os
import time                                  # ← NEW
from typing import List
from backend.core.config import settings

logger = logging.getLogger("unlinker")


async def unlink_paths(
    paths: List[str],
    *,
    files_root: PurePath = PurePath(
        settings.BASE_DIR),  # ← made it a parameter
    retries: int = 3,
    delay: float = 1.0,
) -> None:
    """
    Try to unlink each file up to `retries` times.
    """
    def _unlink(p: str) -> None:
        logger.info(f"Attempting to unlink: {p}")

        for attempt in range(retries):
            try:
                Path(p).unlink(missing_ok=True)
                break
            except PermissionError as e:
                if attempt == retries - 1:
                    logger.warning(
                        "unlink failed path=%s err=%s after %d attempts", p, e, retries)
                else:
                    time.sleep(delay)
            except Exception as e:
                logger.warning("unlink failed path=%s err=%s", p, e)
                break

        # -------- prune empty parent dirs -------------
        try:
            parent = Path(p).parent
            while parent != files_root and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
        except Exception:
            pass

    await asyncio.gather(*[asyncio.to_thread(_unlink, p) for p in paths])
