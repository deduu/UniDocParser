from pydantic import BaseModel
from typing import Optional
from backend.pipeline.model.schemas_dto import DocParserContextOut


class ResponseModel(BaseModel):
    message: str
    job_id: Optional[str]
    extraction_result: Optional[DocParserContextOut] = None
    json_output: Optional[str] = None
    markdown_output: Optional[str] = None
