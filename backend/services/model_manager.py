import os
import torch
from transformers import pipeline, AutoTokenizer
from backend.core.config import settings

# Load the VLM pipeline once – adjust the device and dtype as needed
# or change to a different variant if needed


# Fig2Tab_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
# Fig2Tab_PIPELINE = pipeline(
#     "image-text-to-text",
#     model=Fig2Tab_MODEL_ID,
#     device="cuda:0" if torch.cuda.is_available() else "cpu",
#     torch_dtype=torch.bfloat16,
#     max_new_tokens=1024,
#     batch_size=1,   # Adjust batch size as needed
# )

# Load the VLM pipeline once – adjust the device and dtype as needed
# or change to a different variant if needed
# Define the kwargs for VLM
formatter_generate_kwargs = {
    # "do_sample": True,
    "temperature": 0.3,
    "top_p": 0.5,
    "max_new_tokens": 4096,
}

FORMATTER_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
Formatter_PIPELINE = pipeline(
    "image-text-to-text",
    model=FORMATTER_MODEL_ID,
    device="cuda:1" if torch.cuda.is_available() else "cpu",
    torch_dtype=torch.bfloat16,
    max_new_tokens=4096,
    batch_size=1,   # Adjust batch size as needed
)

# vlm_tokenizer = AutoTokenizer.from_pretrained(Fig2Tab_MODEL_ID)