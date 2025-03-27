# core/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_FOLDER: str = os.path.join(os.getcwd(), 'uploads')
    OUTPUT_FOLDER: str = os.path.join(os.getcwd(), 'outputs')
    IMG_DIR = os.path.join(BASE_DIR, 'backend', 'img')
    # Model paths and parameters
    YOLO_MODEL_PATH = os.path.join(BASE_DIR, 'backend', 'weights', 'detect', 'yolo11_best.pt')
    
    # Ensure upload and output directories exist
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(self.OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(self.IMG_DIR, exist_ok=True)
        os.makedirs(self.YOLO_MODEL_PATH, exist_ok=True)

settings = Settings()