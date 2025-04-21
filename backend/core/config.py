import os
from pydantic_settings import BaseSettings
from typing import ClassVar

# Adjust BASE_DIR to point to the project root, not the backend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# If config.py is at /home/dedya/UniDocParser/backend/core/config.py
# BASE_DIR should be /home/dedya/UniDocParser

UPLOAD_FOLDER: str = os.path.join(os.getcwd(), 'uploads')
OUTPUT_FOLDER: str = os.path.join(os.getcwd(), 'outputs')
IMG_DIR = os.path.join(BASE_DIR, 'img')  # Removed extra 'backend'

# Correct the model path - remove the extra 'backend'
YOLO_MODEL_PATH = os.path.join(BASE_DIR, 'weights', 'detect', 'yolo11_best.pt')

class Settings(BaseSettings):
    # Annotate constants as ClassVar so they aren't treated as model fields
    BASE_DIR: ClassVar[str] = BASE_DIR
    UPLOAD_DIR: ClassVar[str] = UPLOAD_FOLDER
    OUTPUT_DIR: ClassVar[str] = OUTPUT_FOLDER
    IMG_DIR: ClassVar[str] = IMG_DIR
    
    # Model paths and parameters - fixed syntax
    YOLO_MODEL_PATH: ClassVar[str] = YOLO_MODEL_PATH
    
    # Ensure upload and output directories exist
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.IMG_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.YOLO_MODEL_PATH), exist_ok=True)

    def __str__(self):
        """Print settings for debugging"""
        return f"""
        BASE_DIR: {self.BASE_DIR}
        UPLOAD_DIR: {self.UPLOAD_DIR}
        OUTPUT_DIR: {self.OUTPUT_DIR}
        IMG_DIR: {self.IMG_DIR}
        YOLO_MODEL_PATH: {self.YOLO_MODEL_PATH}
        """

settings = Settings()
print(f"Loaded settings: {settings}")  # Add this for debugging