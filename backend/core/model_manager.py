import gc
import time
import torch
from pynvml import *
from backend.core.vlm_config.vlm_fig2tab_config import VLM_Fig2Tab_PIPELINE
from backend.core.vlm_config.vlm_format_config import VLM_Formatter_PIPELINE
from backend.core.vlm_config.ft_vlm_fig2tab_config import FT_VLM_Fig2Tab_PIPELINE
from backend.core.vlm_config.ft_vlm_format_config import FT_VLM_Formatter_PIPELINE
from backend.core.vlm_config.unsloth_vlm_fig2tab_config import Unsloth_VLM_Fig2Tab_PIPELINE
from backend.core.vlm_config.unsloth_vlm_format_config import Unsloth_VLM_Formatter_PIPELINE
from backend.core.config import settings

nvmlInit() 

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
            "base":    (VLM_Fig2Tab_PIPELINE,       {"device": settings.FIG2TAB_MODEL_DEVICE}),
            "ft":      (FT_VLM_Fig2Tab_PIPELINE,    {"device": settings.FIG2TAB_MODEL_DEVICE}),
            "unsloth": (Unsloth_VLM_Fig2Tab_PIPELINE, {"device": settings.FIG2TAB_MODEL_DEVICE}),
        }
        self._formatter_map = {
            "base":    (VLM_Formatter_PIPELINE,       {"device": settings.FORMATTER_MODEL_DEVICE}),
            "ft":      (FT_VLM_Formatter_PIPELINE,    {"device": settings.FORMATTER_MODEL_DEVICE}),
            "unsloth": (Unsloth_VLM_Formatter_PIPELINE, {"device": settings.FORMATTER_MODEL_DEVICE}),
        }

    def _clear_gpu_memory(self):
        """
        A streamlined utility to clear GPU memory.
        Using torch.cuda.synchronize() is good practice to wait for operations
        to finish, but excessive time.sleep() calls are often unnecessary.
        """
        print("Clearing GPU memory...")
        time.sleep(0.33)
        gc.collect()
        time.sleep(0.33)
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        time.sleep(0.33)
        print(f"GPU Allocated Memory: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
        print(f"GPU Reserved Memory: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")

    def _get_gpu_stats(self):
        """Prints current GPU statistics."""
        fig2tab_idx = int(settings.FIG2TAB_MODEL_DEVICE.split(':')[1])
        formatter_idx = int(settings.FORMATTER_MODEL_DEVICE.split(':')[1])
        min_memory_req = 18.5 # GB (Loading model + cache)

        if torch.cuda.is_available():
            print(f"Warning: FIG2TAB and FORMATTER models are using different GPU devices.")
            fig2tab_gpu_stats = torch.cuda.get_device_properties(fig2tab_idx)
            h_fig = nvmlDeviceGetHandleByIndex(fig2tab_idx)
            info_fig = nvmlDeviceGetMemoryInfo(h_fig)
            print(f"FIG2TAB GPU {fig2tab_idx} = {fig2tab_gpu_stats.name}. Max memory = {info_fig.total} GB. Used memory = {info_fig.used} GB.")
            if info_fig.used > info_fig.free - min_memory_req:
                raise RuntimeError(f"Insufficient GPU memory on device {fig2tab_idx}. "
                                   f"Free: {info_fig.free} GB, Required: {min_memory_req} GB.")
            else:
                print(f"GPU {fig2tab_idx} is sufficiently provisioned.")

            formatter_gpu_stats = torch.cuda.get_device_properties(formatter_idx)
            h_formatter = nvmlDeviceGetHandleByIndex(formatter_idx)
            info_formatter = nvmlDeviceGetMemoryInfo(h_formatter)
            print(f"FORMATTER GPU {formatter_idx} = {formatter_gpu_stats.name}. Max memory = {info_formatter.total} GB. Used memory = {info_formatter.used} GB.")
            if info_formatter.used > info_formatter.free - min_memory_req:
                raise RuntimeError(f"Insufficient GPU memory on device {formatter_idx}. "
                                   f"Free: {info_formatter.free} GB, Required: {min_memory_req} GB.")
            else:
                print(f"GPU {formatter_idx} is sufficiently provisioned.")
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