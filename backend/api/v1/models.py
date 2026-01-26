import os
import time
import traceback
import logging
import aiofiles
import asyncio
from PIL.Image import Image
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import io
import base64
import json
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

from backend.core.model_manager import model_manager
router = APIRouter()

class ModelPreferencesIn(BaseModel):
    agent_mode: Optional[bool] = None
    fig2tab_model_type: Optional[str] = None
    formatter_model_type: Optional[str] = None
    fig2tab_model_id: Optional[str] = None
    formatter_model_id: Optional[str] = None


class ModelPreferencesOut(BaseModel):
    agent_mode: bool
    fig2tab_model_type: str
    formatter_model_type: str
    fig2tab_model_id: Optional[str] = None
    formatter_model_id: Optional[str] = None


@router.get("/models", response_model=Dict[str, Any])
async def list_models():
    return {
        "fig2tab": {
            "types": model_manager.list_model_types("fig2tab"),
            "default": model_manager.get_default_model_type("fig2tab"),
        },
        "formatter": {
            "types": model_manager.list_model_types("formatter"),
            "default": model_manager.get_default_model_type("formatter"),
        },
    }


@router.get("/session/preferences", response_model=ModelPreferencesOut)
async def get_model_preferences(request: Request):
    prefs = _resolve_model_preferences(request)
    return ModelPreferencesOut(**prefs)


@router.post("/session/preferences", response_model=ModelPreferencesOut)
async def set_model_preferences(request: Request, prefs_in: ModelPreferencesIn):
    session_prefs = request.session.get("model_preferences", {})
    for key, value in prefs_in.model_dump(exclude_unset=True).items():
        if value is not None:
            session_prefs[key] = value
    request.session["model_preferences"] = session_prefs
    prefs = _resolve_model_preferences(request)
    return ModelPreferencesOut(**prefs)


def _resolve_model_preferences(
    request: Request,
    fig2tab_type: Optional[str] = None,
    formatter_type: Optional[str] = None,
    fig2tab_model_id: Optional[str] = None,
    formatter_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    session_prefs = request.session.get("model_preferences", {})

    resolved_fig2tab_type = (
        fig2tab_type
        or session_prefs.get("fig2tab_model_type")
        or model_manager.get_default_model_type("fig2tab")
    )
    resolved_formatter_type = (
        formatter_type
        or session_prefs.get("formatter_model_type")
        or model_manager.get_default_model_type("formatter")
    )

    resolved = {
        "agent_mode": bool(session_prefs.get("agent_mode", False)),
        "fig2tab_model_type": resolved_fig2tab_type,
        "formatter_model_type": resolved_formatter_type,
        "fig2tab_model_id": fig2tab_model_id or session_prefs.get("fig2tab_model_id"),
        "formatter_model_id": formatter_model_id or session_prefs.get("formatter_model_id"),
    }

    _validate_model_types(resolved["fig2tab_model_type"], resolved["formatter_model_type"])
    return resolved


def _validate_model_types(fig2tab_type: Optional[str], formatter_type: Optional[str]) -> None:
    if fig2tab_type and fig2tab_type not in model_manager.list_model_types("fig2tab"):
        raise HTTPException(
            status_code=400, detail=f"Unknown fig2tab model type: {fig2tab_type}"
        )
    if formatter_type and formatter_type not in model_manager.list_model_types("formatter"):
        raise HTTPException(
            status_code=400, detail=f"Unknown formatter model type: {formatter_type}"
        )
