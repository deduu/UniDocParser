from typing import Dict, Any

from backend.services.file_handler import handle_file
from backend.core.interfaces import PipelineStep

class SplitStep(PipelineStep):
    """
    Splits the document (PDF or other formats) into individual pages/sheets,
    saving images of each and preparing the data structure for further processing.
    """
    def __init__(self):
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the document splitting step.

        Args:
            context: Must contain 'user_id', 'folder', and 'file_path'.
        
        Returns:
            The updated context with a 'pages' list. Each item in the list
            is a dictionary representing a page.
        """
        user_id = context.get("user_id")
        folder = context.get("folder")
        file_path = context.get("file_path")

        if not all([user_id, folder, file_path]):
            raise ValueError("Context for SplitStep must contain 'user_id', 'folder', and 'file_path'.")

        print(f"INFO: Splitting document {file_path} into pages...")
        
        # handle_file returns a list of dictionaries, each representing a page.
        pages_data = handle_file(user_id, folder, file_path)
        
        if pages_data is None:
            raise RuntimeError(f"Failed to handle or split file: {file_path}")

        # The schemas can be added later for validation, for now, dicts are fine.
        context["pages"] = pages_data
        
        print(f"INFO: Document split into {len(pages_data)} pages.")

        return context