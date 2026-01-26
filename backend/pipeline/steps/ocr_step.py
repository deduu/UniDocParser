from typing import Dict, Any
from pathlib import Path

# The runner will be in the 'pipeline' directory, so we can use relative imports
# or absolute ones from the project root.
from backend.services.file_handler import ocr_pdf_to_pdf
from backend.core.interfaces import PipelineStep
from backend.config.settings import get_settings

class OcrStep(PipelineStep):
    """
    Runs OCR on the PDF specified in the context and updates the context
    with the path to the new, OCR'd PDF.
    """
    def __init__(self):
        settings = get_settings()
        self.output_dir = Path(settings.output_dir) / "ocr_files"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the OCR step.
        """
        file_path = context.get("file_path")
        if not file_path:
            raise ValueError("Context for OcrStep must contain 'file_path'.")

        self.output_dir.mkdir(exist_ok=True, parents=True)

        print(f"INFO: Performing OCR on {file_path}...")
        
        ocr_path = ocr_pdf_to_pdf(file_path, self.output_dir)

        print(f"INFO: OCR complete. New file at {ocr_path}")

        context["ocr_file_path"] = str(ocr_path)
        context["file_path"] = str(ocr_path)
        
        return context