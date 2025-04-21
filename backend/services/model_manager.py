import os
import torch
from ultralytics import YOLO
from transformers import pipeline
from backend.core.config import settings

# Load the YOLO model once
YOLO_MODEL = YOLO(settings.YOLO_MODEL_PATH)

# Load the VLM pipeline once – adjust the device and dtype as needed
VLM_MODEL_ID = "google/gemma-3-4b-it"  # or change to a different variant if needed
VLM_PIPELINE = pipeline(
    "image-text-to-text",
    model=VLM_MODEL_ID,
    # device="cpu",
    device="cuda:0" if torch.cuda.is_available() else "cpu",
    torch_dtype=torch.bfloat16,
    max_new_tokens=4096
    # torch_dtype=torch.float16 if torch.cuda.is_available() else None
)

FORMATTER_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"  # or change to a different variant if needed
Formatter_PIPELINE = pipeline(
    "image-text-to-text",
    model=FORMATTER_MODEL_ID,
    device="cuda:1" if torch.cuda.is_available() else "cpu",
    torch_dtype=torch.bfloat16,
    max_new_tokens=4096
)
