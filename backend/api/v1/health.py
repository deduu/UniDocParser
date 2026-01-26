from typing import List, Dict, Any, Optional
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter(tags=["Health"])

@router.get("/", response_class=HTMLResponse)
# Renamed to avoid conflict
async def serve_frontend_root(request: Request):
    """Root route for serving the frontend."""
    # Access templates from app.state
    return request.app.state.templates.TemplateResponse("index.html", {"request": request})

@router.get("/health")
async def health_check_endpoint():  # Renamed to avoid conflict if `create_app` is called
    """Health check endpoint."""
    return {"status": "ok"}