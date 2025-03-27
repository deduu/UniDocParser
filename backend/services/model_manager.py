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
    device="cuda:0" if torch.cuda.is_available() else "cpu",
    torch_dtype=torch.float16 if torch.cuda.is_available() else None
)
