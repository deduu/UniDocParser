# backend/schemas/extractor.py
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class JobStatus(str, Enum):
    """Valid job status values"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

# Base schemas


class ExtractJobBase(BaseModel):
    """Base schema for ExtractJob"""
    tenant_id: str = Field(..., min_length=1, max_length=255)
    source_file_name: Optional[str] = Field(None, max_length=255)
    source_file_url: Optional[str] = Field(None, max_length=2048)
    options_json: Dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = Field(default=JobStatus.QUEUED)
    page_count_est: Optional[int] = Field(None, ge=0)
    page_count_actual: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None


class ExtractPageBase(BaseModel):
    """Base schema for ExtractPage"""
    page_index: int = Field(..., ge=0)
    image_url: Optional[str] = Field(None, max_length=2048)
    text: Optional[str] = None
    markdown: Optional[str] = None
    elements: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class ExtractResultBase(BaseModel):
    """Base schema for ExtractResult"""
    json_url: Optional[str] = Field(None, max_length=2048)
    markdown_url: Optional[str] = Field(None, max_length=2048)
    preview_png_url: Optional[str] = Field(None, max_length=2048)
    bytes_stored: Optional[int] = Field(None, ge=0)
    processing_time: Optional[int] = Field(
        None, ge=0, description="Processing time in seconds")

# Create schemas


class ExtractJobCreate(ExtractJobBase):
    """Schema for creating a new ExtractJob"""
    # tenant_id and other required fields inherited from base
    created_by_user_id: str

    @field_validator("options_json", mode="before")
    @classmethod
    def validate_options_json(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('options_json must be a dictionary')
        return v


class ExtractPageCreate(ExtractPageBase):
    """Schema for creating a new ExtractPage"""
    job_id: Optional[str] = None  # Will be set by service if not provided

    @field_validator("elements", mode="before")
    @classmethod
    def validate_elements(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError('elements must be a list')
        return v


class ExtractResultCreate(ExtractResultBase):
    """Schema for creating a new ExtractResult"""
    job_id: str = Field(..., min_length=1)

# Update schemas


class ExtractJobUpdate(BaseModel):
    """Schema for updating an ExtractJob"""
    source_file_name: Optional[str] = Field(None, max_length=255)
    source_file_url: Optional[str] = Field(None, max_length=2048)
    options_json: Optional[Dict[str, Any]] = None
    status: Optional[JobStatus] = None
    page_count_est: Optional[int] = Field(None, ge=0)
    page_count_actual: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None

    model_config = ConfigDict(extra='forbid')


class ExtractPageUpdate(BaseModel):
    """Schema for updating an ExtractPage"""
    page_index: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = Field(None, max_length=2048)
    text: Optional[str] = None
    markdown: Optional[str] = None
    elements: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(extra='forbid')


class ExtractResultUpdate(ExtractResultBase):
    """Schema for updating an ExtractResult"""
    model_config = ConfigDict(extra='forbid')

# Upsert schemas


class ExtractResultUpsert(ExtractResultBase):
    """Schema for upserting an ExtractResult"""
    job_id: str = Field(..., min_length=1)

# Response schemas


class ExtractJobResponse(ExtractJobBase):
    """Schema for ExtractJob responses"""
    id: str
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractPageResponse(ExtractPageBase):
    """Schema for ExtractPage responses"""
    id: str
    job_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractResultResponse(ExtractResultBase):
    """Schema for ExtractResult responses"""
    job_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Complex response schemas


class ExtractJobWithPages(ExtractJobResponse):
    """Job response with pages included"""
    pages: List[ExtractPageResponse] = Field(default_factory=list)


class ExtractJobWithResult(ExtractJobResponse):
    """Job response with result included"""
    result: Optional[ExtractResultResponse] = None


class ExtractJobComplete(ExtractJobResponse):
    """Complete job response with both pages and result"""
    pages: List[ExtractPageResponse] = Field(default_factory=list)
    result: Optional[ExtractResultResponse] = None
    model_config = ConfigDict(from_attributes=True)

# Filter schemas


class ExtractJobFilter(BaseModel):
    """Filter schema for listing jobs"""
    status: Optional[List[JobStatus]] = None
    created_by_user_id: Optional[str] = None
    source_file_name: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    model_config = ConfigDict(extra='forbid')


class ExtractPageFilter(BaseModel):
    """Filter schema for listing pages"""
    job_id: Optional[str] = None
    page_index_min: Optional[int] = Field(None, ge=0)
    page_index_max: Optional[int] = Field(None, ge=0)
    has_text: Optional[bool] = None
    has_markdown: Optional[bool] = None
    has_image: Optional[bool] = None

    model_config = ConfigDict(extra='forbid')

    @field_validator("page_index_max", mode="before")
    @classmethod
    def validate_page_index_range(cls, v, values):
        if v is not None and 'page_index_min' in values and values['page_index_min'] is not None:
            if v < values['page_index_min']:
                raise ValueError('page_index_max must be >= page_index_min')
        return v

# Statistics schemas


class JobStatusCounts(BaseModel):
    """Job counts by status"""
    queued: int = 0
    running: int = 0
    succeeded: int = 0
    failed: int = 0
    canceled: int = 0


class TenantStatistics(BaseModel):
    """Comprehensive tenant statistics"""
    tenant_id: str
    total_jobs: int
    status_counts: JobStatusCounts
    total_pages_processed: int
    total_bytes_stored: int
    recent_jobs: List[Dict[str, Any]] = Field(default_factory=list)


class JobSummary(BaseModel):
    """Summary information for a job"""
    id: str
    status: JobStatus
    file_name: Optional[str]
    page_count: int
    created_at: datetime
    processing_time: Optional[int] = None


class CompleteJobSummary(BaseModel):
    """Complete job summary with all related data"""
    job: ExtractJobResponse
    page_count: int
    has_result: bool
    result: Optional[ExtractResultResponse]
    summary: JobSummary

# Bulk operation schemas


class BulkJobStatusUpdate(BaseModel):
    """Schema for bulk status updates"""
    job_ids: List[str] = Field(..., min_items=1)
    status: JobStatus


class BulkPageCreate(BaseModel):
    """Schema for bulk page creation"""
    job_id: str
    pages: List[ExtractPageCreate] = Field(..., min_items=1)


class JobProcessingComplete(BaseModel):
    """Schema for completing job processing"""
    pages: List[ExtractPageCreate] = Field(default_factory=list)
    result: ExtractResultUpsert
    final_status: JobStatus = JobStatus.SUCCEEDED

# Validation schemas


class JobValidation(BaseModel):
    """Validation results for a job"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

# Search schemas


class PageSearchRequest(BaseModel):
    """Schema for searching pages by content"""
    job_id: str
    search_term: str = Field(..., min_length=1, max_length=255)
    search_in_text: bool = True
    search_in_markdown: bool = True


class PageSearchResponse(BaseModel):
    """Response for page search"""
    pages: List[ExtractPageResponse]
    total_matches: int
    search_term: str

# Error schemas


class ServiceError(BaseModel):
    """Standard service error response"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Pagination schemas


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool

    @property
    def page_info(self) -> Dict[str, Any]:
        return {
            "current_page": (self.skip // self.limit) + 1,
            "total_pages": (self.total + self.limit - 1) // self.limit,
            "has_next": self.has_more,
            "has_previous": self.skip > 0
        }


# Type aliases for clarity
JobID = str
TenantID = str
UserID = str
PageIndex = int
