# app/core/settings.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    STORAGE_ROOT: Path = Path("uploads")
    USE_X_ACCEL: bool = False            # flip on if you front with Nginx
    X_ACCEL_PREFIX: str = "/protected"   # internal location in nginx

settings = Settings()
