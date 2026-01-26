from typing import Protocol, Dict, Any, Tuple, Optional, runtime_checkable
from PIL import Image

# ------------------------------------------------------------------------------
# UniDoc Agent - Interfaces
# ------------------------------------------------------------------------------
# This file defines the abstract interfaces (contracts) for core components.
# Using Protocols ensures components are interchangeable and adhere to a contract.
# ------------------------------------------------------------------------------

class ImageModelProvider(Protocol):
    """
    A contract for model providers that process IMAGES.
    """
    def generate(self, image: Image.Image) -> Tuple[str, str]:
        """
        Generates text content based on a given PIL image.

        Args:
            image (Image.Image): The input PIL image.

        Returns:
            A tuple containing:
            - str: The generated text.
            - str: The status of the generation (e.g., "Success", "Failed").
        """
        ...

class FormatterModelProvider(Protocol):
    """
    A contract for model providers that process TEXT.
    """
    def generate(self, text: str, image: Image.Image) -> Tuple[str, str]:
        """
        Generates text content based on a given string and image.

        Args:
            text (str): The input text.
            image (Image.Image): The input PIL image.

        Returns:
            A tuple containing:
            - str: The generated text.
            - str: The status of the generation (e.g., "Success", "Failed").
        """
        ...


class ModelProvider(Protocol):
    """
    A generic contract for model providers (image or text).
    """
    def generate(
        self,
        text: Optional[str] = None,
        image: Optional[Image.Image] = None,
    ) -> Tuple[str, str]:
        ...


@runtime_checkable
class PipelineStep(Protocol):
    """
    A contract for all pipeline steps.
    """
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the logic for this step.

        Args:
            context (Dict[str, Any]): The shared state of the document being processed.

        Returns:
            Dict[str, Any]: The updated context.
        """
        ...