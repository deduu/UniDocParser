import base64
import io
import openai
from PIL import Image
from typing import Tuple

from backend.model_providers.common import Fig2Text_Prompt, Formatter_Prompt
from backend.core.interfaces import ImageModelProvider, FormatterModelProvider

def _encode_pil_to_base64(image: Image.Image) -> str:
    """Encodes a PIL image to a base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

class OpenAIImageProvider(ImageModelProvider):
    """
    Implements ImageModelProvider for OpenAI vision models.
    """
    def __init__(self, model_id: str, api_key: str, base_url: str, temperature: float = 0.5, max_new_tokens: int = 4096):
        self.model = model_id
        self.temperature = temperature
        self.max_tokens = max_new_tokens
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.prompt_template = Fig2Text_Prompt()

    def generate(self, image: Image.Image) -> Tuple[str, str]:
        base64_image = _encode_pil_to_base64(image)
        messages = [
            {"role": "system", "content": self.prompt_template.get_system_prompt()},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                {"type": "text", "text": self.prompt_template.get_prompt()}
            ]},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            generated_text = response.choices[0].message.content or ""
            status = "Success" if generated_text else "Failed: Empty response"
        except Exception as e:
            print(f"An error occurred with the OpenAI Vision API: {e}")
            generated_text = ""
            status = f"Failed: {e}"
        return generated_text, status

class OpenAITextProvider(FormatterModelProvider):
    """
    Implements FormatterModelProvider for OpenAI text models.
    """
    def __init__(self, model_id: str, api_key: str, base_url: str, temperature: float = 0.1, max_new_tokens: int = 8192):
        self.model = model_id
        self.temperature = temperature
        self.max_tokens = max_new_tokens
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.prompt_template = Formatter_Prompt()
        
    def generate(self, text: str, image: Image.Image) -> Tuple[str, str]:
        base64_image = _encode_pil_to_base64(image)
        user_prompt = f"Please reformat the following text:\n\n{text}"
        messages = [
            {"role": "system", "content": self.prompt_template.get_system_prompt()},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                {"type": "text", "text": self.prompt_template.get_prompt(user_prompt)}
            ]},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            generated_text = response.choices[0].message.content or ""
            status = "Success" if generated_text else "Failed: Empty response"
        except Exception as e:
            print(f"An error occurred with the OpenAI Text API: {e}")
            generated_text = ""
            status = f"Failed: {e}"
        return generated_text, status