import torch
import gc
from transformers import pipeline, AutoProcessor
from PIL import Image
from typing import Tuple

from backend.model_providers.common import Fig2Text_Prompt, Formatter_Prompt
from backend.core.interfaces import ImageModelProvider, FormatterModelProvider

class HuggingFaceImageProvider(ImageModelProvider):
    """
    Implements ImageModelProvider for local Hugging Face vision models.
    """
    def __init__(self, model_id: str, device: str = "cpu", **kwargs):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = pipeline(
            "image-to-text",
            model=model_id,
            device=self.device,
            torch_dtype=torch.bfloat16 if self.device.startswith("cuda") else torch.float32,
            **kwargs
        )
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.prompt_template = Fig2Text_Prompt()
        self.generate_kwargs = { "max_new_tokens": 2048 }

    def generate(self, image: Image.Image) -> Tuple[str, str]:
        messages = [
            {"role": "system", "content": self.prompt_template.get_system_prompt()},
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": self.prompt_template.get_prompt()}]}
        ]
        prompt_text = self.processor.apply_chat_template(messages, add_generation_prompt=True)
        
        try:
            outputs = self.model(image, prompt=prompt_text, generate_kwargs=self.generate_kwargs)
            generated_text = outputs[0]["generated_text"]
            if prompt_text in generated_text:
                generated_text = generated_text.split(prompt_text, 1)[1]
            status = "Success"

            output_token = self.processor(text=generated_text, return_tensors="pt").input_ids
            len_output = output_token.shape[1]
            if len_output >= self.generate_kwargs["max_new_tokens"] - 5:
                status = "Failed: output length exceeded max_new_tokens (check if any repetition)"
        except Exception as e:
            print(f"An error occurred during Hugging Face image model inference: {e}")
            generated_text = ""
            status = f"Failed: {e}"
        finally:
            if self.device.startswith("cuda"):
                gc.collect()
                torch.cuda.empty_cache()
        return generated_text, status

class HuggingFaceTextProvider(FormatterModelProvider):
    """
    Implements FormatterModelProvider for local Hugging Face text models.
    """
    def __init__(self, model_id: str, device: str, **kwargs):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = pipeline(
            "image-to-text",
            model=model_id,
            device=self.device,
            torch_dtype=torch.bfloat16 if self.device.startswith("cuda") else torch.float32,
            **kwargs
        )
        self.prompt_template = Formatter_Prompt()
        self.generate_kwargs = {
            "max_new_tokens": 8192,
            "do_sample": True,
            "temperature": 0.1,
            "top_p": 0.1 
        }

    def generate(self, text: str, image: Image.Image) -> Tuple[str, str]:
        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": self.prompt_template.get_system_prompt()}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": self.prompt_template.get_prompt(text)}
                ]
            }
        ]
        try:
            outputs = self.model(text=messages, generate_kwargs=self.generate_kwargs)
            generated_text = outputs[0]["generated_text"]
            status = "Success"

            output_token = self.processor(text=generated_text, return_tensors="pt").input_ids
            len_output = output_token.shape[1]
            if len_output >= self.generate_kwargs["max_new_tokens"] - 5:
                status = "Failed: output length exceeded max_new_tokens (check if any repetition)"
        except Exception as e:
            print(f"An error occurred during Hugging Face text model inference: {e}")
            generated_text = ""
            status = f"Failed: {e}"
        finally:
            if self.device.startswith("cuda"):
                gc.collect()
                torch.cuda.empty_cache()
        return generated_text, status
