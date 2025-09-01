# backend/deps/security.py
from __future__ import annotations

import ipaddress
import os
from typing import Optional, List
from urllib.parse import urlparse
import uuid
import logging

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Config (tweak for your env)
# ------------------------------------------------------------------------------
# Put full origins here (scheme+host[:port]); we'll compare by netloc (host[:port])
ALLOWED_ORIGINS = {
    "http://127.0.0.1:8005",   # chat app (dev)
    "http://localhost:8005",   # chat app (dev)
    "http://127.0.0.1:8010",   # extractor swagger (dev)
    "http://localhost:8010",   # extractor swagger (dev)
    "https://app.vidavox.ai",  # prod app
}
ALLOWED_NETLOCS = {urlparse(o).netloc.lower() for o in ALLOWED_ORIGINS}

ENV = os.getenv("APP_ENV", "dev").lower()  # "dev" or "prod"
STRICT_UUID = os.getenv("STRICT_UUID", "1") not in {
    "0", "false", "False"}  # allow loosening in dev if needed


# ------------------------------------------------------------------------------
# Model
# ------------------------------------------------------------------------------
class Principal(BaseModel):
    user_id: str
    user_email: Optional[str] = None
    tenant_id: Optional[str] = None


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _first_value(v: Optional[str | List[str]]) -> Optional[str]:
    """
    Handle duplicate/merged headers:
    - If FastAPI collected multiple: List[str] -> first
    - If ASGI merged them: "value1, value2" -> take first
    """
    if v is None:
        return None
    if isinstance(v, list):
        v = v[0] if v else None
    if v is None:
        return None
    return v.split(",")[0].strip()


def _validate_uuid(u: str) -> str:
    if not STRICT_UUID:
        return str(u)
    try:
        uuid.UUID(str(u))
        return str(u)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid X-User-ID")


def _verify_origin_or_ip(request: Request) -> None:
    origin_hdr = request.headers.get("origin")
    if origin_hdr:
        netloc = urlparse(origin_hdr).netloc.lower()  # e.g. "127.0.0.1:8010"
        logger.info("Origin header: %s -> netloc=%s", origin_hdr, netloc)
        if netloc not in ALLOWED_NETLOCS:
            raise HTTPException(status_code=403, detail="Forbidden origin")
        return

    # No Origin => likely non-browser or proxied request.
    client_ip = (request.headers.get("x-forwarded-for")
                 or request.client.host or "").split(",")[0].strip()
    logger.info("No Origin header. client_ip=%s", client_ip)

    try:
        ip = ipaddress.ip_address(client_ip)
        is_loopback = ip.is_loopback
    except ValueError:
        is_loopback = False

    if ENV == "dev":
        if not is_loopback:
            raise HTTPException(
                status_code=403, detail="Forbidden origin (non-loopback in dev)")
    else:
        # In prod, without Origin we fail closed
        raise HTTPException(
            status_code=403, detail="Forbidden origin (missing Origin)")


# ------------------------------------------------------------------------------
# Unified dependency
# ------------------------------------------------------------------------------
async def get_verified_principal(
    request: Request,
    # Use aliases so callers send standard header spelling once
    x_user_id: str | List[str] = Header(..., alias="X-User-ID"),
    x_user_email: Optional[str | List[str]] = Header(
        None, alias="X-User-Email"),
    x_tenant_id: Optional[str | List[str]] = Header(None, alias="X-Tenant-ID"),
) -> Principal:
    """
    Single dependency that:
      1) Verifies the request origin (or loopback in dev)
      2) Parses & validates user/tenant headers
      3) Returns a Principal you can pass to services
    """
    _verify_origin_or_ip(request)

    uid = _first_value(x_user_id)
    email = _first_value(x_user_email)
    tid = _first_value(x_tenant_id)

    if not uid:
        raise HTTPException(status_code=401, detail="Missing X-User-ID")

    return Principal(
        user_id=_validate_uuid(uid),
        user_email=email,
        tenant_id=tid,
    )
