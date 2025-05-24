# app/handlers/utils.py

import os
import tempfile
from pathlib import Path
from fastapi import UploadFile

import base64
import io
from PIL import Image

from backend.utils.helpers import resize_img


# def pil_to_base64(img: Image.Image) -> str:
#     """PNG-encode a PIL image and return a base64 string (without newlines)."""
#     buffer = io.BytesIO()
#     img.save(buffer, format="PNG")
#     return base64.b64encode(buffer.getvalue()).decode("ascii")

def pil_to_base64(
    img: Image.Image,
    fmt: str = "JPEG",
    size: int = 1440,
    **save_kwargs
) -> str:
    """
    Encode a PIL image into base64.

    Parameters:
    - img:          PIL.Image.Image
    - fmt:          "PNG", "JPEG", etc.
    - save_kwargs:  passed through to `img.save()`, e.g. quality=85 for JPEG.

    Returns:
    A base64 string (no newlines), suitable for embedding as data URIs.
    """
    img = resize_img(img, size=size)
    buffer = io.BytesIO()
    img.save(buffer, format=fmt, **save_kwargs)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/{fmt.lower()};base64,{b64}"


async def _save_to_tmp(file: UploadFile, tmp_dir: str | None = None) -> str:
    """
    Save an UploadFile to a uniquely-named temp file and return its filesystem path.
    If tmp_dir is provided, it'll write there; otherwise it uses the OS default temp dir.
    """
    # preserve the uploaded file's suffix (e.g. .pdf, .png)
    suffix = Path(file.filename).suffix

    # create a NamedTemporaryFile that sticks around after closing
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, dir=tmp_dir
    ) as tmp:
        # read the entire uploaded file into memory (okay for typical PDF sizes)
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    return tmp_path
