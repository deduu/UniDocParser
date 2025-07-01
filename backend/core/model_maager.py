import os
import unsloth
import gc
import time
import torch
from backend.core.vlm_config.vlm_fig2tab_config import VLM_Fig2Tab_PIPELINE
from backend.core.vlm_config.vlm_format_config import VLM_Formatter_PIPELINE
from backend.core.vlm_config.ft_vlm_fig2tab_config import FT_VLM_Fig2Tab_PIPELINE
from backend.core.vlm_config.ft_vlm_format_config import FT_VLM_Formatter_PIPELINE
from backend.core.vlm_config.unsloth_vlm_fig2tab_config import Unsloth_VLM_Fig2Tab_PIPELINE
from backend.core.vlm_config.unsloth_vlm_format_config import Unsloth_VLM_Formatter_PIPELINE

class ModelManager:
    """
    Manages the lifecycle of machine learning models, including loading,
    switching, and clearing them from memory.
    """

    def __init__(self):
        """Initializes the ModelManager."""
        self.fig2tab_model = None
        self.formatter_model = None
        self.current_fig2tab_type = None
        self.current_formatter_type = None

        # Use dictionaries to map model types to their respective classes.
        # This makes the code cleaner, more scalable, and easier to maintain.
        self._fig2tab_map = {
            "base":    (VLM_Fig2Tab_PIPELINE,       {"device": "cuda"}),
            "ft":      (FT_VLM_Fig2Tab_PIPELINE,    {"device": "cuda"}),
            "unsloth": (Unsloth_VLM_Fig2Tab_PIPELINE, {"device": "cuda"}),
        }
        self._formatter_map = {
            "base":    (VLM_Formatter_PIPELINE,       {"device": "cuda"}),
            "ft":      (FT_VLM_Formatter_PIPELINE,    {"device": "cuda"}),
            "unsloth": (Unsloth_VLM_Formatter_PIPELINE, {"device": "cuda"}),
        }

    def _clear_gpu_memory(self):
        """
        A streamlined utility to clear GPU memory.
        Using torch.cuda.synchronize() is good practice to wait for operations
        to finish, but excessive time.sleep() calls are often unnecessary.
        """
        print("Clearing GPU memory...")
        time.sleep(1)
        gc.collect()
        time.sleep(1)
        torch.cuda.empty_cache()
        # A single synchronize call is sufficient to wait for CUDA kernels to finish.
        torch.cuda.synchronize()
        time.sleep(1)
        print(f"GPU Allocated Memory: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
        print(f"GPU Reserved Memory: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")

    def _get_gpu_stats(self):
        """Prints current GPU statistics."""
        if torch.cuda.is_available():
            # This can be simplified if you just want general stats
            for i in range(torch.cuda.device_count()):
                gpu_stats = torch.cuda.get_device_properties(i)
                max_memory = round(gpu_stats.total_memory / 1024**3, 3)
                print(f"GPU {i} = {gpu_stats.name}. Max memory = {max_memory} GB.")
        else:
            print("CUDA is not available.")

    def get_model(self, model_family: str, model_type: str):
        """
        A generic method to get or switch a model. It handles loading,
        caching, and cleaning up old models automatically.

        Args:
            model_family (str): The family of the model ('fig2tab' or 'formatter').
            model_type (str): The type of model to load ('base', 'ft', 'unsloth').

        Returns:
            The requested model instance.
        """
        if model_family == 'fig2tab':
            model_map = self._fig2tab_map
            current_model_attr = 'fig2tab_model'
            current_type_attr = 'current_fig2tab_type'
        elif model_family == 'formatter':
            model_map = self._formatter_map
            current_model_attr = 'formatter_model'
            current_type_attr = 'current_formatter_type'
        else:
            raise ValueError(f"Unknown model family: {model_family}")

        target_config = model_map.get(model_type)
        if not target_config:
            raise ValueError(f"Unknown model type '{model_type}' for family '{model_family}'")
        
        # Unpack the class and its arguments from the config tuple
        target_class, model_args = target_config

        current_model = getattr(self, current_model_attr)
        current_type = getattr(self, current_type_attr)

        # Check if the desired model is already loaded.
        if current_model is not None and current_type == model_type:
            print(f"'{model_type}' {model_family} model is already loaded. Using cached instance.")
            return current_model

        # If a different model is loaded, clear it first.
        if current_model is not None:
            print(f"Switching from '{current_type}' to '{model_type}' for {model_family} model.")
            # Delete the reference to the old model object
            del current_model
            if current_model_attr in globals(): del globals()[current_model_attr]
            setattr(self, current_model_attr, None)
            self._clear_gpu_memory()

        # Load the new model
        print(f"Loading '{model_type}' {model_family} model with args: {model_args}")
        self._get_gpu_stats()

        new_model = target_class(**model_args)
        setattr(self, current_model_attr, new_model)
        setattr(self, current_type_attr, model_type)
        print(f"Successfully loaded '{model_type}' {model_family} model.")

        return new_model

model_manager = ModelManager()
# fig2tab_model = model_manager.get_model(model_family='fig2tab', model_type='base')
# formatter_model = model_manager.get_model(model_family='formatter', model_type='base')