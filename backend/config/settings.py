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
    upload_dir: str = os.path.join(base_dir, "uploads")
    output_dir: str = os.path.join(base_dir, "outputs")
    IMG_DIR: str = os.path.join(base_dir, "images")
    
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
    runtime_config_path: str = os.getenv(
        "RUNTIME_CONFIG_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "backend",
            "config",
            "runtime.yaml",
        ),
    )

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_yaml_configs()
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.IMG_DIR, exist_ok=True)

    def reload(self):
        self._load_yaml_configs()

    def _load_yaml_configs(self):
        # Load models.yaml
        models_path = os.path.join(self.base_dir, "backend", "config", "models.yaml")
        with open(models_path, 'r') as f:
            yaml_data = yaml.safe_load(f) or {}

        runtime_data: Dict[str, Any] = {}
        if os.path.exists(self.runtime_config_path):
            with open(self.runtime_config_path, 'r') as f:
                runtime_data = yaml.safe_load(f) or {}

        yaml_data = self._substitute_env_vars(yaml_data)
        runtime_data = self._substitute_env_vars(runtime_data)

        merged_models = self._merge_model_overrides(
            yaml_data.get("models", {}),
            runtime_data.get("models", {}),
        )
        yaml_data["models"] = merged_models

        settings_overrides = runtime_data.get("settings", {})
        if "openai_api_key" in settings_overrides:
            self.openai_api_key = settings_overrides.get("openai_api_key", "")
        if "openai_base_url" in settings_overrides:
            self.openai_base_url = settings_overrides.get("openai_base_url", self.openai_base_url)

        self.models_config = yaml_data

        # Load pipelines.yaml
        pipelines_path = os.path.join(self.base_dir, "backend", "config", "pipelines.yaml")
        with open(pipelines_path, 'r') as f:
            self.pipelines_config = yaml.safe_load(f).get('pipelines', [])

    def _merge_model_overrides(
        self,
        base_models: Dict[str, Any],
        override_models: Dict[str, Any],
    ) -> Dict[str, Any]:
        def _normalize_overrides(overrides: Any) -> Dict[str, Dict[str, Any]]:
            if isinstance(overrides, list):
                return {item.get("name"): item for item in overrides if isinstance(item, dict) and item.get("name")}
            if isinstance(overrides, dict):
                return overrides
            return {}

        merged: Dict[str, Any] = {}
        all_families = set(base_models.keys()) | set(override_models.keys())

        for family in all_families:
            base_list = base_models.get(family, []) or []
            base_map = {item.get("name"): dict(item) for item in base_list if isinstance(item, dict) and item.get("name")}
            overrides_map = _normalize_overrides(override_models.get(family, {}))

            for name, override in overrides_map.items():
                if name in base_map:
                    base_item = base_map[name]
                    if "provider" in override:
                        base_item["provider"] = override["provider"]
                    if "args" in override and isinstance(override["args"], dict):
                        base_item.setdefault("args", {})
                        base_item["args"].update(override["args"])
                    if "available_model_ids" in override:
                        base_item["available_model_ids"] = list(override["available_model_ids"] or [])
                    base_map[name] = base_item
                else:
                    if isinstance(override, dict) and override.get("provider"):
                        override_item = dict(override)
                        override_item.setdefault("name", name)
                        base_map[name] = override_item

            merged[family] = list(base_map.values())

        return merged

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
