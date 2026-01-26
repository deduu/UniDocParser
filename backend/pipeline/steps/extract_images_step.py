from typing import Dict, Any

from backend.core.interfaces import PipelineStep
from backend.core.model_manager import model_manager
from backend.services.image_extractor import extract_images_from_figures

class ExtractImagesStep(PipelineStep):
    """
    Processes the extracted figures using a vision-language model to enrich
    them with generated text and metadata.
    """
    def __init__(self):
        pass

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the image extraction and analysis step.

        Args:
            context: Must contain 'pages' and 'figure_list'. It should also
                     contain 'fig2tab_model_type' to specify which model to use.
        
        Returns:
            The updated context.
        """
        pages = context.get("pages", [])
        figure_list = context.get("figure_list", [])
        
        # The agent will place the chosen model type in the context.
        # We can have a default as a fallback.
        fig2tab_model_type = context.get("fig2tab_model_type", "openai_vision")
        fig2tab_model_id = context.get("fig2tab_model_id")

        if not figure_list:
            print("INFO: No figures found to process. Skipping ExtractImagesStep.")
            return context

        print(f"INFO: Getting fig2tab model '{fig2tab_model_type}'...")
        
        # Get the model provider from the manager
        fig2tab_model_provider = model_manager.get_model(
            model_family='fig2tab',
            model_type=fig2tab_model_type,
            model_id_override=fig2tab_model_id,
        )
        
        print(f"INFO: Enriching {len(figure_list)} figures with model '{fig2tab_model_type}'...")

        # Run the extraction
        updated_pages, updated_figure_list = extract_images_from_figures(
            fig2tab_model_provider,
            pages,
            figure_list
        )

        context["pages"] = updated_pages
        context["figure_list"] = updated_figure_list
        
        return context