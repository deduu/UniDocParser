# backend/utils/storage_paths.py
from pathlib import Path
from typing import Tuple
# ensure it has STORAGE_BASE_DIR="outputs", STORAGE_BASE_URL="/outputs"
from backend.core.config import settings


def page_image_key(job_id: str, page_index: int, ext: str = "jpeg") -> str:
    return f"jobs/{job_id}/pages/{page_index:04d}.{ext}"


def fs_path_from_key(storage_key: str) -> Path:
    return Path(settings.STORAGE_BASE_DIR) / storage_key


def public_url_from_key(storage_key: str) -> str:
    # if you use static mount
    return f"{settings.STORAGE_BASE_URL.rstrip('/')}/{storage_key}"


def ensure_parent_dir(storage_key: str) -> Path:
    p = fs_path_from_key(storage_key)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
