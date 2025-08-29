# deps.py
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel
import uuid

class Principal(BaseModel):
    user_id: str
    user_email: str | None = None
    tenant_id: str | None = None

def _validate_uuid(u: str) -> str:
    try:
        uuid.UUID(str(u))
        return str(u)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid X-User-ID")

async def get_principal_from_headers(
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
) -> Principal:
    return Principal(
        user_id=_validate_uuid(x_user_id),
        user_email=x_user_email,
        tenant_id=x_tenant_id,  # optional today; add later when you have orgs
    )
