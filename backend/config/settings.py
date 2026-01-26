# In order for this file to work, you need to add `PyYAML` and `python-dotenv` to your dependencies.
# pip install PyYAML python-dotenv

import os
from dotenv import load_dotenv
import yaml
from pydantic_settings import BaseSettings
from typing import Dict, Any, List
from functools import lru_cache

load_dotenv()

class Settings(BaseSettings):
    # Core application settings
    base_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    upload_dir: str = os.path.join(base_dir, "unidoc_agent", "uploads")
    output_dir: str = os.path.join(base_dir, "unidoc_agent", "outputs")
    IMG_DIR: str = os.path.join(base_dir, "unidoc_agent", "images")
    
    # OpenAI Credentials (loaded from .env file)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Session settings (for user preferences like agent mode/model choices)
    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "change_me")
    session_max_age_seconds: int = 60 * 60 * 24 * 7

    # CUDA Device settings (loaded from .env file)
    fig2tab_model_device: str = os.getenv("FIG2TAB_MODEL_DEVICE", "cpu")
    formatter_model_device: str = os.getenv("FORMATTER_MODEL_DEVICE", "cpu")

    # Model and Pipeline configurations loaded from YAML
    models_config: Dict[str, Any] = {}
    pipelines_config: List[Dict[str, Any]] = []

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_yaml_configs()
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.IMG_DIR, exist_ok=True)

    def _load_yaml_configs(self):
        # Load models.yaml
        models_path = os.path.join(self.base_dir, "backend", "config", "models.yaml")
        with open(models_path, 'r') as f:
            yaml_data = yaml.safe_load(f)
            # Substitute environment variables
            self.models_config = self._substitute_env_vars(yaml_data)

        # Load pipelines.yaml
        pipelines_path = os.path.join(self.base_dir, "backend", "config", "pipelines.yaml")
        with open(pipelines_path, 'r') as f:
            self.pipelines_config = yaml.safe_load(f).get('pipelines', [])

    def _substitute_env_vars(self, config: Any) -> Any:
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(i) for i in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            var_name = config[2:-1]
            return os.getenv(var_name, "")
        return config


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
