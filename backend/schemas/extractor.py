# backend/schemas/extractor.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any

class ExtractJobCreate(BaseModel):
    tenant_id: str
    created_by_user_id: str
    source_file_name: Optional[str] = None
    source_file_url: Optional[str] = None
    options_json: dict = Field(default_factory=dict)
    page_count_est: Optional[int] = None
    status: str = "queued"

class ExtractJobUpdate(BaseModel):
    status: Optional[str] = None
    page_count_actual: Optional[int] = None
    error_message: Optional[str] = None

class ExtractPageCreate(BaseModel):
    job_id: str
    page_index: int
    image_url: Optional[str] = None
    text: Optional[str] = None
    markdown: Optional[str] = None
    elements: Optional[list] = None  # list[ElementOut] JSON

class ExtractResultUpsert(BaseModel):
    job_id: str
    json_url: Optional[str] = None
    markdown_url: Optional[str] = None
    preview_png_url: Optional[str] = None
    bytes_stored: Optional[int] = None
    processing_time: Optional[int] = None
