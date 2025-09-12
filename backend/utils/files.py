# app/utils/files.py
import json
import mimetypes
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from backend.core.config import settings

from backend.pipeline.model.schemas_dto import DocParserContextOut


def resolve_safe_path(raw_path: str | Path) -> Path:
    """
    Resolve to an absolute path and ensure it stays under STORAGE_ROOT.
    Prevents path traversal and 'poisoned' DB paths.
    """
    root = settings.STORAGE_ROOT.resolve()
    p = Path(raw_path).expanduser().resolve()
    if not str(p).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not p.is_file():
        raise HTTPException(status_code=400, detail="Not a file")
    return p


def guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(path.name)
    return mt or "application/octet-stream"


def build_download_response(
    path: Path,
    download_name: str | None = None,
):
    """
    Return a Response that triggers a safe download.
    If USE_X_ACCEL is True, offload the file to Nginx via X-Accel-Redirect.
    Otherwise, use Starlette FileResponse (streams efficiently, supports ranges).
    """
    download_name = download_name or path.name
    # RFC 5987 filename* for unicode-safe names
    content_disp = f"attachment; filename*=UTF-8''{download_name}"

    if settings.USE_X_ACCEL:
        # Nginx internal redirect: map real path -> /protected/<relative>
        rel = path.relative_to(settings.STORAGE_ROOT.resolve())
        print(f"rel: {rel}")
        accel_target = f"{settings.X_ACCEL_PREFIX}/{rel.as_posix()}"
        resp = Response(status_code=200)
        resp.headers["Content-Type"] = guess_mime(path)
        resp.headers["Content-Disposition"] = content_disp
        resp.headers["X-Accel-Redirect"] = accel_target
        return resp

    # Fallback: stream via ASGI server
    return FileResponse(
        path=path,
        media_type=guess_mime(path),
        filename=download_name,              # sets Content-Disposition for you
        # headers={"Content-Disposition": content_disp},  # (optional explicit)
    )


def load_extraction_result_from_file(json_path: str) -> DocParserContextOut:
    """
    Load DocParserContextOut from saved JSON file (from result.json_url).
    Raises FileNotFoundError if missing.
    """

    path = Path(settings.OUTPUT_DIR) / json_path

    if not path.exists():
        raise FileNotFoundError(
            f"Extraction result file not found: {json_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return DocParserContextOut.model_validate(data)
