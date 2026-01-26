from typing import Dict, Any

from backend.services.element_extractor import extract_elements
from backend.core.interfaces import PipelineStep

class ExtractElementsStep(PipelineStep):
    """
    Extracts structured elements (text, tables, images) from the document pages.
    """
    def __init__(self):
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the element extraction step.

        Args:
            context: Must contain 'pages', 'user_id', 'folder', and 'file_path'.
        
        Returns:
            The updated context with 'pages' containing extracted elements
            and a 'figure_list' for images to be processed.
        """
        pages = context.get("pages", [])
        user_id = context.get("user_id")
        folder = context.get("folder")
        file_path = context.get("file_path")

        if not all([user_id, folder, file_path]):
            raise ValueError("Context for ExtractElementsStep must contain 'user_id', 'folder', and 'file_path'.")

        print("INFO: Extracting elements from pages...")
        
        updated_pages, figure_list = extract_elements(pages, user_id, folder, file_path)
        
        context["pages"] = updated_pages
        context["figure_list"] = figure_list
        
        print(f"INFO: Extracted {len(figure_list)} figures.")

        return context