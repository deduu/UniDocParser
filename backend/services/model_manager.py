import os
import torch
from ultralytics import YOLO
from transformers import pipeline
from backend.core.config import settings

# Load the YOLO model once
YOLO_MODEL = YOLO(settings.YOLO_MODEL_PATH)

# Load the VLM pipeline once – adjust the device and dtype as needed
Fig2Tab_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"  # or change to a different variant if needed
Fig2Tab_PIPELINE = pipeline(
    "image-text-to-text",
    model=Fig2Tab_MODEL_ID,
    device="cuda:0" if torch.cuda.is_available() else "cpu",
    torch_dtype=torch.bfloat16,
    max_new_tokens=1024,
    batch_size=1,   # Adjust batch size as needed
)

FORMATTER_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"  # or change to a different variant if needed
Formatter_PIPELINE = pipeline(
    "image-text-to-text",
    model=FORMATTER_MODEL_ID,
    device="cuda:1" if torch.cuda.is_available() else "cpu",
    torch_dtype=torch.bfloat16,
    max_new_tokens=4096,
    batch_size=1,   # Adjust batch size as needed
)
