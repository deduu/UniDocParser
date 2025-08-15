import os
from pydantic_settings import BaseSettings
from typing import ClassVar
import torch

# Adjust BASE_DIR to point to the project root, not the backend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# If config.py is at /home/dedya/UniDocParser/backend/core/config.py
# BASE_DIR should be /home/dedya/UniDocParser

UPLOAD_FOLDER: str = os.path.join(os.getcwd(), 'uploads')
OUTPUT_FOLDER: str = os.path.join(os.getcwd(), 'outputs')
IMG_DIR = os.path.join(BASE_DIR, 'img')  # Removed extra 'backend'

# Define subdirectories that need to be created
IMG_PAGES_SUBDIR: str = "pages"
IMG_FIGURES_SUBDIR: str = "figures"

class Settings(BaseSettings):
    # Annotate constants as ClassVar so they aren't treated as model fields
    BASE_DIR: ClassVar[str] = BASE_DIR
    UPLOAD_DIR: ClassVar[str] = UPLOAD_FOLDER
    OUTPUT_DIR: ClassVar[str] = OUTPUT_FOLDER
    IMG_DIR: ClassVar[str] = IMG_DIR
    
    # For convenience, provide full paths to subdirectories if other modules need them directly
    # IMG_PAGES_DIR: ClassVar[str] = os.path.join(IMG_DIR, IMG_PAGES_SUBDIR)
    # IMG_FIGURES_DIR: ClassVar[str] = os.path.join(IMG_DIR, IMG_FIGURES_SUBDIR)

    # Cuda Settings for Each Models
    FIG2TAB_MODEL_DEVICE: str = "cuda:1"
    FORMATTER_MODEL_DEVICE: str = "cuda:2"

    # Ensure upload and output directories exist
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.IMG_DIR, exist_ok=True)
        # os.makedirs(self.IMG_PAGES_DIR, exist_ok=True)
        # os.makedirs(self.IMG_FIGURES_DIR, exist_ok=True)

        # Check GPU availability
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. Please check your setup.")

    def __str__(self):
        """Print settings for debugging"""
        return f"""
        BASE_DIR: {self.BASE_DIR}
        UPLOAD_DIR: {self.UPLOAD_DIR}
        OUTPUT_DIR: {self.OUTPUT_DIR}
        IMG_DIR: {self.IMG_DIR}
        FIG2TAB_MODEL_DEVICE: {self.FIG2TAB_MODEL_DEVICE}
        FORMATTER_MODEL_DEVICE: {self.FORMATTER_MODEL_DEVICE}
        """
        # IMG_PAGES_DIR: {self.IMG_PAGES_DIR}
        # IMG_FIGURES_DIR: {self.IMG_FIGURES_DIR}

settings = Settings()
print(f"Loaded settings: {settings}")  # Add this for debugging