import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from .celery_app import celery
from backend.pipeline.doc_parse_handler import DocParserHandler


def _safe_serialize_dto(dto) -> Dict[str, Any]:
    # Ensure the result is JSON-serializable for Celery backend
    if hasattr(dto, "model_dump"):
        return dto.model_dump()
    if hasattr(dto, "dict"):
        return dto.dict()
    return json.loads(json.dumps(dto, default=str))


@celery.task(bind=True)
def run_extraction(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery worker entrypoint. Because your pipeline is async, we bridge with asyncio.run().
    """
    return asyncio.run(_run_extraction_async(self, file_path, options))


async def _run_extraction_async(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    # no FastAPI Depends here; construct your dependencies inside
    handler = DocParserHandler()

    self.update_state(state="STARTED", meta={"progress": 5, "label": "Queued"})

    try:
        # route by extension
        path = Path(file_path)
        if path.suffix.lower() in (".xls", ".xlsx"):
            self.update_state(state="PROGRESS", meta={
                              "progress": 10, "label": "Parsing workbook"})
            dto = await handler.extract_only(open(file_path, "rb"))
        else:
            self.update_state(state="PROGRESS", meta={
                              "progress": 10, "label": "Running pipeline"})
            dto = await handler.full_pipeline(open(file_path, "rb"))

        self.update_state(state="PROGRESS", meta={
                          "progress": 80, "label": "Saving outputs"})

        json_name, md_name = await handler.save_results(dto, path.name)

        result_payload = {
            "message": "PDF extracted successfully",
            "extraction_result": _safe_serialize_dto(dto),
            "json_output": json_name,
            "markdown_output": md_name,
        }

        self.update_state(state="PROGRESS", meta={
                          "progress": 95, "label": "Finalizing"})

        # Final task result (ends with SUCCESS state)
        return result_payload

    except Exception as e:
        # Celery will mark state FAILURE and put this as result
        raise e
