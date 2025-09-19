# formatter_llm.py
"""
Formatter wrapper using your LocalHuggingFaceClient with base+adapter support.

Requirements:
- LocalHuggingFaceClient must accept:
    base_model_hint: Optional[str]
    adapter_path: Optional[str]
    merge_adapter: bool = False
  and forward unknown kwargs to model.generate (so min_p/top_p work).

Usage:
    from backend.core.formatter_llm import get_formatter_vlm
    formatter = get_formatter_vlm()
    text = await formatter.generate(pil_image, extracted_text="...")
"""

import base64
import io
import logging
from functools import lru_cache
from typing import Optional

from PIL import Image

from backend.generation.hf_adapter import LocalHuggingFaceClient
from backend.core.prompt_config import Formatter_Prompt

logger = logging.getLogger(__name__)


class FormatterLLM:
    def __init__(
        self,
        *,
        base_repo: str = "unsloth/Qwen2.5-VL-7B-Instruct",
        adapter_repo: Optional[str] = "ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Markdown-Formatter",
        device: str = "cuda:0",
        dtype: str = "float16",
        quantization: Optional[str] = None,
        temperature: float = 1.5,
        min_p: Optional[float] = 0.1,
        top_p: Optional[float] = None,
        max_new_tokens: int = 8192,  # 8k tokens, like your pipeline
        merge_adapter: bool = False,
    ):
        self.prompt_template = Formatter_Prompt()

        # Heuristic: pick quantization if adapter name hints 4bit
        if quantization is None and adapter_repo and "4bit" in adapter_repo.lower():
            quantization = "bitsandbytes"

        self.client = LocalHuggingFaceClient(
            model_path=base_repo if adapter_repo else base_repo,
            base_model_hint=base_repo,
            adapter_path=adapter_repo,
            merge_adapter=merge_adapter,
            device=device,
            dtype=dtype,
            quantization=quantization,
            system_prompt=None,   # keep prompt in user msg
            attn_implementation=None,
        )

        self.gen_defaults = {
            "temperature": temperature,
            "do_sample": True,
            "max_new_tokens": max_new_tokens,
        }
        if min_p is not None:
            self.gen_defaults["min_p"] = min_p
        if top_p is not None:
            self.gen_defaults["top_p"] = top_p

    @staticmethod
    def _to_data_url(img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    # -----------------------
    # public APIs
    # -----------------------
    async def generate(self, extracted_text: str, image: Image.Image) -> str:
        """
        Generate formatted markdown from extracted_text + image.
        """
        data_url = self._to_data_url(image)
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": self.prompt_template.get_ft_prompt(
                    extracted_text)},
            ],
        }]

        logger.info(
            f"Generating with prompt: {messages[0]['content'][1]['text']}")

        return await self.client.chat(messages, **self.gen_defaults)

    async def generate_from_path(self, extracted_text: str, image_path: str) -> str:
        """
        Same as generate(), but pass a file path instead of a PIL image.
        """
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_path", "image_path": image_path},
                {"type": "text", "text": self.prompt_template.get_ft_prompt(
                    extracted_text)},
            ],
        }]
        return await self.client.chat(messages, **self.gen_defaults)


@lru_cache(maxsize=1)
def get_formatter_vlm() -> FormatterLLM:
    """
    Returns a cached FormatterLLM instance.
    Adjust defaults here for global choice.
    """
    return FormatterLLM(
        base_repo="Qwen/Qwen2.5-VL-7B-Instruct",
        adapter_repo=None,  # or your unsloth adapter
        device="cuda:2",
        quantization=None,
        temperature=1.5,
        min_p=0.1,
        top_p=None,
        max_new_tokens=8192,
        merge_adapter=True,
    )
