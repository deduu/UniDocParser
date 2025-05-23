import os
from pydantic_settings import BaseSettings
from typing import ClassVar

# The WORKDIR in your Dockerfile is /app.
# So, os.getcwd() inside the container will typically be /app.
# We'll define paths relative to this /app structure.
APP_ROOT_IN_CONTAINER = "/app"

# Define paths for UPLOAD_FOLDER, OUTPUT_FOLDER, IMG_DIR, and weights relative to APP_ROOT_IN_CONTAINER
# to match the volume mounts in docker-compose.yml
UPLOAD_FOLDER_PATH: str = os.path.join(APP_ROOT_IN_CONTAINER, 'uploads')
OUTPUT_FOLDER_PATH: str = os.path.join(APP_ROOT_IN_CONTAINER, 'outputs')
IMG_DIR_PATH: str = os.path.join(APP_ROOT_IN_CONTAINER, 'img')

# Define subdirectories that need to be created
IMG_PAGES_SUBDIR: str = "pages"
IMG_FIGURES_SUBDIR: str = "figures"


class Settings(BaseSettings):
    # Annotate constants as ClassVar so they aren't treated as model fields
    BASE_DIR: ClassVar[str] = APP_ROOT_IN_CONTAINER # Represents the app's root in the container
    UPLOAD_DIR: ClassVar[str] = UPLOAD_FOLDER_PATH
    OUTPUT_DIR: ClassVar[str] = OUTPUT_FOLDER_PATH
    IMG_DIR: ClassVar[str] = IMG_DIR_PATH
    # For convenience, provide full paths to subdirectories if other modules need them directly
    IMG_PAGES_DIR: ClassVar[str] = os.path.join(IMG_DIR_PATH, IMG_PAGES_SUBDIR)
    IMG_FIGURES_DIR: ClassVar[str] = os.path.join(IMG_DIR_PATH, IMG_FIGURES_SUBDIR)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Directories are now created in the Dockerfile.
        # No os.makedirs calls needed here anymore for these specific paths.

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