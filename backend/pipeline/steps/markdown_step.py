import os
from typing import Dict, Any

from backend.core.interfaces import PipelineStep
from backend.core.model_manager import model_manager
from backend.services.output_formatter import format_markdown


class MarkdownStep(PipelineStep):
    """Turn each page's cleaned text into Markdown using a formatter model."""

    def __init__(self):
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pages = context.get("pages", [])
        file_path = context.get("file_path", "")

        if not pages:
            raise RuntimeError(
                "MarkdownStep: pages are missing - run previous steps first"
            )

        formatter_model_type = context.get("formatter_model_type", "openai_formatter")
        formatter_model_id = context.get("formatter_model_id")
        formatter_model = model_manager.get_model(
            model_family="formatter",
            model_type=formatter_model_type,
            model_id_override=formatter_model_id,
        )

        pdf_name = os.path.basename(file_path) if file_path else "document"

        updated_pages = format_markdown(formatter_model, pages, pdf_name)
        context["pages"] = updated_pages
        return context
