# core/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    UPLOAD_FOLDER: str = os.path.join(os.getcwd(), 'uploads')
    OUTPUT_FOLDER: str = os.path.join(os.getcwd(), 'outputs')
    
    # Ensure upload and output directories exist
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(self.OUTPUT_FOLDER, exist_ok=True)

settings = Settings()