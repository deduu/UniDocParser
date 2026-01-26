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
import yaml
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

from backend.core.model_manager import model_manager
from backend.config.settings import get_settings
router = APIRouter(tags=["Models"])
settings = get_settings()

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


class ModelAvailabilityIn(BaseModel):
    model_config = {
        "protected_namespaces": (),
    }
    family: str
    model_type: str
    model_ids: List[str]
    mode: Optional[str] = "replace"  # replace | append


class OpenAISettingsIn(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@router.get("/models", response_model=Dict[str, Any])
async def list_models():
    return {
        "fig2tab": {
            "types": model_manager.list_model_types_with_ids("fig2tab"),
            "default": model_manager.get_default_model_type("fig2tab"),
        },
        "formatter": {
            "types": model_manager.list_model_types_with_ids("formatter"),
            "default": model_manager.get_default_model_type("formatter"),
        },
    }


@router.get("/models/available", response_model=Dict[str, Any])
async def list_available_models(
    family: Optional[str] = None,
    model_type: Optional[str] = None,
):
    if model_type and not family:
        raise HTTPException(status_code=400, detail="model_type requires family")

    if family and family not in {"fig2tab", "formatter"}:
        raise HTTPException(status_code=400, detail="family must be 'fig2tab' or 'formatter'")

    if family and model_type:
        if model_type not in model_manager.list_model_types(family):
            raise HTTPException(status_code=400, detail="Unknown model_type for the specified family")
        return {
            "model_ids": model_manager.get_available_model_ids(family, model_type)
        }

    if family:
        return {
            "family": family,
            "types": model_manager.list_model_types_with_ids(family),
        }

    return {
        "fig2tab": model_manager.list_model_types_with_ids("fig2tab"),
        "formatter": model_manager.list_model_types_with_ids("formatter"),
    }


@router.post("/models/available", response_model=Dict[str, Any])
async def update_available_models(payload: ModelAvailabilityIn):
    if payload.family not in {"fig2tab", "formatter"}:
        raise HTTPException(status_code=400, detail="family must be 'fig2tab' or 'formatter'")
    if payload.model_type not in model_manager.list_model_types(payload.family):
        raise HTTPException(status_code=400, detail="Unknown model_type for the specified family")

    _update_runtime_available_models(
        family=payload.family,
        model_type=payload.model_type,
        model_ids=payload.model_ids,
        mode=payload.mode or "replace",
    )
    model_manager.reload()
    return {
        payload.family: model_manager.list_model_types_with_ids(payload.family)
    }


@router.post("/settings/openai", response_model=Dict[str, Any])
async def update_openai_settings(payload: OpenAISettingsIn):
    if not payload.api_key and not payload.base_url:
        raise HTTPException(status_code=400, detail="Provide api_key and/or base_url")

    _update_runtime_openai_settings(api_key=payload.api_key, base_url=payload.base_url)
    model_manager.reload()
    return {
        "message": "OpenAI settings updated",
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
    _validate_model_ids(
        resolved["fig2tab_model_type"],
        resolved["formatter_model_type"],
        resolved.get("fig2tab_model_id"),
        resolved.get("formatter_model_id"),
    )
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


def _validate_model_ids(
    fig2tab_type: Optional[str],
    formatter_type: Optional[str],
    fig2tab_model_id: Optional[str],
    formatter_model_id: Optional[str],
) -> None:
    if fig2tab_model_id and fig2tab_type:
        available_fig2tab_ids = model_manager.get_available_model_ids("fig2tab", fig2tab_type)
        if available_fig2tab_ids and fig2tab_model_id not in available_fig2tab_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown fig2tab model id '{fig2tab_model_id}' for type '{fig2tab_type}'",
            )

    if formatter_model_id and formatter_type:
        available_formatter_ids = model_manager.get_available_model_ids("formatter", formatter_type)
        if available_formatter_ids and formatter_model_id not in available_formatter_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown formatter model id '{formatter_model_id}' for type '{formatter_type}'",
            )


def _load_runtime_config() -> Dict[str, Any]:
    path = settings.runtime_config_path
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def _write_runtime_config(data: Dict[str, Any]) -> None:
    path = settings.runtime_config_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def _update_runtime_available_models(
    family: str,
    model_type: str,
    model_ids: List[str],
    mode: str,
) -> None:
    data = _load_runtime_config()
    data.setdefault("models", {})
    data["models"].setdefault(family, {})
    data["models"][family].setdefault(model_type, {})

    normalized_mode = (mode or "replace").lower()
    if normalized_mode == "append":
        current = model_manager.get_available_model_ids(family, model_type)
        merged = list(dict.fromkeys([*current, *model_ids]))
        data["models"][family][model_type]["available_model_ids"] = merged
    else:
        data["models"][family][model_type]["available_model_ids"] = list(dict.fromkeys(model_ids))

    _write_runtime_config(data)


def _update_runtime_openai_settings(
    api_key: Optional[str],
    base_url: Optional[str],
) -> None:
    data = _load_runtime_config()
    data.setdefault("settings", {})

    if api_key:
        data["settings"]["openai_api_key"] = api_key
    if base_url:
        data["settings"]["openai_base_url"] = base_url

    data.setdefault("models", {})

    for family, providers in settings.models_config.get("models", {}).items():
        for provider in providers:
            provider_path = (provider.get("provider") or "").lower()
            model_name = provider.get("name")
            if not model_name or "openai" not in provider_path:
                continue
            data["models"].setdefault(family, {})
            data["models"][family].setdefault(model_name, {})
            data["models"][family][model_name].setdefault("args", {})
            if api_key:
                data["models"][family][model_name]["args"]["api_key"] = api_key
            if base_url:
                data["models"][family][model_name]["args"]["base_url"] = base_url

    _write_runtime_config(data)
