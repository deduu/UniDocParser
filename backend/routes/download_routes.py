# backend/routes/download_routes.py
from fastapi import APIRouter, Depends, Request
# from app.services.db_service import DatabaseService
# from app.auth.deps import get_current_user_flexible
# from app.utils.models import User
# from app.utils.files import resolve_safe_path, build_download_response
# from app.api.deps.files import get_record_or_404, require_owner_or_403
# from app.utils.audit import audit_download

# files_router = APIRouter()

# def get_db_service(request: Request) -> DatabaseService:
#     return request.app.state.db_service

# @files_router.get("/download/{file_id}")
# async def send_file_by_id(
#     file_id: str,
#     current_user: User = Depends(get_current_user_flexible),
#     db: DatabaseService = Depends(get_db_service),
# ):
#     # 1) Resolve DB record or 404
#     record = await get_record_or_404(file_id=file_id, db=db)

#     # 2) Authorization (owner check; extend to admin/role if needed)
#     require_owner_or_403(record, current_user)

#     # 3) Safe path resolution under STORAGE_ROOT
#     file_path = resolve_safe_path(record.path)

#     # 4) (Optional) audit trail
#     audit_download(user_id=str(current_user.id), file_id=file_id, path_str=str(file_path))

#     # 5) Build and return the response (Nginx offload or FileResponse)
#     return build_download_response(file_path, download_name=file_path.name)
