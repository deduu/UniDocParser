# backend/deps/verify.py
from fastapi import Header, HTTPException, Request
from typing import Optional
from urllib.parse import urlparse
import ipaddress
import os
import logging

logger = logging.getLogger(__name__)

# Put full origins here; we’ll compare by netloc (host[:port])
ALLOWED_ORIGINS = {
    "http://127.0.0.1:8005",
    "http://localhost:8005",
    "https://app.vidavox.ai",
}
ALLOWED_NETLOCS = {urlparse(o).netloc.lower() for o in ALLOWED_ORIGINS}
ENV = os.getenv("APP_ENV", "dev").lower()  # "dev" or "prod"

async def verify_internal_call(
    request: Request,
    x_user_id: str = Header(...),
    x_user_email: Optional[str] = Header(None),
):
    origin_hdr = request.headers.get("origin")
    if origin_hdr:
        netloc = urlparse(origin_hdr).netloc.lower()  # e.g. "127.0.0.1:8005"
        logger.info(f"Origin header: {origin_hdr} -> netloc={netloc}")
        if netloc not in ALLOWED_NETLOCS:
            raise HTTPException(status_code=403, detail="Forbidden origin")
    else:
        # Non-browser call; allow loopback in dev. In prod, require match.
        client_ip = (request.headers.get("x-forwarded-for") or request.client.host or "").split(",")[0].strip()
        logger.info(f"No Origin header. client_ip={client_ip}")
        try:
            ip = ipaddress.ip_address(client_ip)
            is_loopback = ip.is_loopback
        except ValueError:
            is_loopback = False

        if ENV == "dev":
            if not is_loopback:
                raise HTTPException(status_code=403, detail="Forbidden origin (non-loopback in dev)")
        else:
            # In prod, without Origin we fail closed
            raise HTTPException(status_code=403, detail="Forbidden origin (missing Origin)")

    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing user header")

    return {"user_id": x_user_id, "email": x_user_email}
