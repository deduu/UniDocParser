from fastapi import Header, HTTPException, Request
from typing import Optional

ALLOWED_ORIGINS = {"http://localhost:5173", "https://your-prod-domain"}

async def verify_internal_call(
    request: Request,
    x_user_id: str = Header(...),
    x_user_email: Optional[str] = Header(None),
):
    # Optional origin/IP-based validation
    origin = request.headers.get("origin") or request.client.host
    if origin not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Forbidden origin")

    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing user header")

    return {"user_id": x_user_id, "email": x_user_email}
