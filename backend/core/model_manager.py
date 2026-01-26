import gc
import time
import torch
import importlib
import hashlib
from typing import Dict, Any, Optional, Tuple

from backend.config.settings import get_settings
from backend.core.interfaces import ModelProvider

def _import_class(class_path: str):
    """Dynamically imports a class from a string path."""
    try:
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not import class {class_path}: {e}")

class ModelManager:
    """
    Manages the lifecycle of machine learning models.
    
    This class reads model configurations from the settings, loads them on demand,
    and caches them for efficient reuse. It supports switching between different
    models and clearing them from memory.
    """

    def __init__(self):
        """Initializes the ModelManager by loading configurations."""
        self.settings = get_settings()
        self._fig2tab_providers: Dict[str, Any] = {}
        self._formatter_providers: Dict[str, Any] = {}
        self._loaded_models: Dict[str, ModelProvider] = {}
        self._current_fig2tab_key: str | None = None
        self._current_formatter_key: str | None = None
        
        self._register_providers()

    def _register_providers(self):
        """
        Dynamically registers model providers from the models_config.
        """
        model_configs = self.settings.models_config.get('models', {})
        for family, providers in model_configs.items():
            for provider_config in providers:
                name = provider_config['name']
                provider_class_path = provider_config['provider']
                provider_args = provider_config['args']
                
                if family == 'fig2tab':
                    self._fig2tab_providers[name] = (provider_class_path, provider_args)
                elif family == 'formatter':
                    self._formatter_providers[name] = (provider_class_path, provider_args)

    def list_model_types(self, model_family: str) -> list[str]:
        """Returns the available model types for a given family."""
        provider_map = self._fig2tab_providers if model_family == "fig2tab" else self._formatter_providers
        return list(provider_map.keys())

    def get_default_model_type(self, model_family: str) -> Optional[str]:
        """Returns the first configured model type for a given family."""
        types = self.list_model_types(model_family)
        return types[0] if types else None

    def _build_cache_key(self, model_family: str, model_type: str, model_args: Dict[str, Any]) -> str:
        args_items = sorted(model_args.items())
        args_repr = "|".join([f"{k}={v}" for k, v in args_items])
        digest = hashlib.md5(args_repr.encode("utf-8")).hexdigest()
        return f"{model_family}:{model_type}:{digest}"

    def get_model(
        self,
        model_family: str,
        model_type: Optional[str] = None,
        model_id_override: Optional[str] = None,
        provider_args_override: Optional[Dict[str, Any]] = None,
    ) -> ModelProvider:
        """
        Generic method to get a model instance. It handles loading, caching,
        and cleaning up old models automatically.

        Args:
            model_family: The family of the model ('fig2tab' or 'formatter').
            model_type: The name of the model to load (e.g., 'openai_vision').

        Returns:
            The requested model instance.
        """
        current_model_attr = f"_current_{model_family}_key"
        current_model_key = getattr(self, current_model_attr, None)

        if model_type is None:
            model_type = self.get_default_model_type(model_family)
        if not model_type:
            raise ValueError(f"No model types configured for family '{model_family}'")
        
        # Check if the desired model is already loaded and is the current one.
        provider_map = self._fig2tab_providers if model_family == 'fig2tab' else self._formatter_providers
        if model_type not in provider_map:
            raise ValueError(f"Unknown model type '{model_type}' for family '{model_family}'")

        provider_class_path, model_args = provider_map[model_type]
        model_args = dict(model_args) if model_args else {}

        if model_id_override:
            model_args["model_id"] = model_id_override
        if provider_args_override:
            model_args.update(provider_args_override)

        cache_key = self._build_cache_key(model_family, model_type, model_args)

        # Check if the desired model is already loaded and is the current one.
        if current_model_key == cache_key and cache_key in self._loaded_models:
            print(f"'{model_type}' {model_family} model is already loaded. Using cached instance.")
            return self._loaded_models[cache_key]

        # If a different model is loaded for this family, clear it first.
        if current_model_key and current_model_key in self._loaded_models:
            print(f"Switching from '{current_model_key}' to '{cache_key}' for {model_family} model.")
            del self._loaded_models[current_model_key]
            self._clear_gpu_memory()

        print(f"Loading '{model_type}' {model_family} model from provider: {provider_class_path}")
        
        # Dynamically import the provider class
        provider_class = _import_class(provider_class_path)
        
        # Instantiate the new model
        new_model = provider_class(**model_args)

        self._loaded_models[cache_key] = new_model
        setattr(self, current_model_attr, cache_key)
        print(f"Successfully loaded '{model_type}' {model_family} model.")
        
        return new_model

    def _clear_gpu_memory(self):
        """A streamlined utility to clear GPU memory."""
        print("Clearing GPU memory...")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            print(f"GPU Allocated Memory: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
            print(f"GPU Reserved Memory: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")

# Singleton instance of the ModelManager
model_manager = ModelManager()
