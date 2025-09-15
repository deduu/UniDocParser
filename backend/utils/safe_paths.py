# backend/utils/storage_paths.py
from pathlib import Path
from typing import Literal
from fastapi import HTTPException
from backend.core.config import settings


def page_image_key(job_id: str, page_index: int, ext: str = "jpeg") -> str:
    return f"jobs/{job_id}/pages/{page_index:04d}.{ext}"


def fs_path_from_key(storage_key: str) -> Path:
    return Path(settings.STORAGE_BASE_DIR) / storage_key


def output_path_from_key(output_key: str) -> Path:
    return Path(settings.OUTPUT_DIR) / output_key


def public_url_from_key(storage_key: str) -> str:
    # if you use static mount
    return f"{settings.STORAGE_BASE_URL.rstrip('/')}/{storage_key}"


def _safe_join_under(base_dir: Path, key: str) -> Path:
    """
    Resolve `key` under `base_dir` and ensure the final path
    stays within `base_dir` (guards against traversal and symlink escapes).
    """
    base = base_dir.resolve()
    candidate = (base / key).resolve()
    # Python 3.11+: Path.is_relative_to
    if not candidate.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


def safe_join(
    key: str,
    *,
    where: Literal["fs", "output"] = "fs",
) -> Path:
    """
    Safe-join for both storage (fs) and output roots.
    """
    base_dir = Path(settings.STORAGE_BASE_DIR) if where == "fs" else Path(
        settings.OUTPUT_DIR)
    return _safe_join_under(base_dir, key)


def ensure_parent_dir(key: str, *, where: Literal["fs", "output"] = "fs") -> Path:
    """
    Make parent directory under the chosen root, return the full path.
    """
    p = safe_join(key, where=where)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
