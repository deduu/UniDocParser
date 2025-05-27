import os
from pydantic_settings import BaseSettings
from typing import ClassVar

# Adjust BASE_DIR to point to the project root, not the backend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# If config.py is at /home/dedya/UniDocParser/backend/core/config.py
# BASE_DIR should be /home/dedya/UniDocParser

# Define paths for UPLOAD_FOLDER, OUTPUT_FOLDER, IMG_DIR, and weights relative to APP_ROOT_IN_CONTAINER
# to match the volume mounts in docker-compose.yml
UPLOAD_FOLDER_PATH: str = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER_PATH: str = os.path.join(BASE_DIR, 'outputs')
IMG_DIR_PATH: str = os.path.join(BASE_DIR, 'img')

# Define subdirectories that need to be created
IMG_PAGES_SUBDIR: str = "pages"
IMG_FIGURES_SUBDIR: str = "figures"

class Settings(BaseSettings):
    # Annotate constants as ClassVar so they aren't treated as model fields
    BASE_DIR: ClassVar[str] = BASE_DIR
    UPLOAD_DIR: ClassVar[str] = UPLOAD_FOLDER_PATH
    OUTPUT_DIR: ClassVar[str] = OUTPUT_FOLDER_PATH
    IMG_DIR: ClassVar[str] = IMG_DIR_PATH
    
    # For convenience, provide full paths to subdirectories if other modules need them directly
    IMG_PAGES_DIR: ClassVar[str] = os.path.join(IMG_DIR_PATH, IMG_PAGES_SUBDIR)
    IMG_FIGURES_DIR: ClassVar[str] = os.path.join(IMG_DIR_PATH, IMG_FIGURES_SUBDIR)
    
    # Ensure upload and output directories exist
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.IMG_DIR, exist_ok=True)
        os.makedirs(self.IMG_PAGES_DIR, exist_ok=True)
        os.makedirs(self.IMG_FIGURES_DIR, exist_ok=True)

    def __str__(self):
        """Print settings for debugging"""
        return f"""
        BASE_DIR: {self.BASE_DIR}
        UPLOAD_DIR: {self.UPLOAD_DIR}
        OUTPUT_DIR: {self.OUTPUT_DIR}
        IMG_DIR: {self.IMG_DIR}
        IMG_PAGES_DIR: {self.IMG_PAGES_DIR}
        IMG_FIGURES_DIR: {self.IMG_FIGURES_DIR}
        """

settings = Settings()
print(f"Loaded settings: {settings}")  # Add this for debugging