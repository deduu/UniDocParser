from typing import Dict, Any

from backend.core.interfaces import PipelineStep
from backend.services.output_formatter import format_extracted_text


class FormatExtractedTextStep(PipelineStep):
    """
    Cleans and combines extracted text into page-level text/markdown fields.

    Expects:
        context["pages"] = List[Dict]
    """

    def __init__(self):
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pages = context.get("pages", [])

        if not pages:
            raise RuntimeError(
                "FormatExtractedTextStep: pages are missing – run previous steps first"
            )

        updated_pages = format_extracted_text(pages)
        context["pages"] = updated_pages
        return context
