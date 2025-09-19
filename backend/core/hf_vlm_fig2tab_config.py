# fig2tab_llm.py
"""
Fig→Text wrapper using your LocalHuggingFaceClient with base+adapter support.

Requirements:
- LocalHuggingFaceClient must accept:
    base_model_hint: Optional[str]
    adapter_path: Optional[str]
    merge_adapter: bool = False
  and forward unknown kwargs to model.generate (so min_p/top_p work).

Usage:
    from backend.core.fig2tab_llm import get_fig2tab_vlm
    fig2tab = get_fig2tab_vlm()
    text = await fig2tab.generate(pil_image)
"""

import base64
import io
from functools import lru_cache
from typing import Optional

from PIL import Image

from backend.generation.hf_adapter import LocalHuggingFaceClient
from backend.core.prompt_config import Fig2Text_Prompt


class Fig2TabLLM:
    def __init__(
        self,
        *,
        # Default to Qwen2.5-VL base + your Unsloth adapter repo
        base_repo: str = "unsloth/Qwen2.5-VL-7B-Instruct",
        adapter_repo: Optional[str] = "ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Extract-Figure",
        device: str = "cuda:0",
        dtype: str = "float16",
        quantization: Optional[str] = None,   # e.g. "bitsandbytes" for 4-bit
        temperature: float = 1.5,
        # forwarded if your transformers supports it
        min_p: Optional[float] = 0.1,
        top_p: Optional[float] = None,       # optional; forwarded
        max_new_tokens: int = 4096,
        merge_adapter: bool = False,         # if you want to merge LoRA into base at load
    ):
        """
        If 'adapter_repo' is None, we assume 'base_repo' is a full model repo.
        If 'adapter_repo' is provided, we load base_repo then apply adapter_repo via PEFT.
        """
        self.prompt = Fig2Text_Prompt().get_prompt()

        # Heuristic: if adapter name hints 4bit, default quantization
        if quantization is None and adapter_repo and "4bit" in adapter_repo.lower():
            quantization = "bitsandbytes"

        self.client = LocalHuggingFaceClient(
            # When using an adapter, pass the *base* as model_path so config is valid
            model_path=base_repo if adapter_repo else base_repo,
            base_model_hint=base_repo,
            adapter_path=adapter_repo,         # apply LoRA/Unsloth adapter if present
            merge_adapter=merge_adapter,
            device=device,
            dtype=dtype,
            quantization=quantization,
            system_prompt=None,                # keep prompt in the user message
            attn_implementation=None,          # auto → FA2 if available, else SDPA
        )

        # Default generation knobs; unknown kwargs are forwarded to HF .generate()
        self.gen_defaults = {
            "temperature": temperature,
            "do_sample": True,
            "max_new_tokens": max_new_tokens,
        }
        if min_p is not None:
            self.gen_defaults["min_p"] = min_p
        if top_p is not None:
            self.gen_defaults["top_p"] = top_p

    # -----------------------
    # helpers
    # -----------------------
    @staticmethod
    def _to_data_url(img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    # -----------------------
    # public APIs
    # -----------------------
    async def generate(self, image: Image.Image) -> str:
        """
        Generate text from a PIL.Image using a data URL block + text prompt.
        """
        data_url = self._to_data_url(image)
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": self.prompt},
            ],
        }]
        return await self.client.chat(messages, **self.gen_defaults)

    async def generate_from_path(self, image_path: str) -> str:
        """
        Same as generate(), but pass a file path (lets adapter open PIL internally).
        """
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_path", "image_path": image_path},
                {"type": "text", "text": self.prompt},
            ],
        }]
        return await self.client.chat(messages, **self.gen_defaults)

# Lazy singleton to avoid model load at import time


@lru_cache(maxsize=1)
def get_fig2tab_vlm() -> Fig2TabLLM:
    """
    Returns a cached Fig2TabLLM instance.
    Adjust default base/adapter here if you want a global choice.
    """
    return Fig2TabLLM(
        # base_repo="Qwen/Qwen2.5-VL-7B-Instruct",
        # adapter_repo=None,
        base_repo="unsloth/Qwen2.5-VL-7B-Instruct",
        adapter_repo="ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Extract-Figure",
        device="cuda:1",
        quantization=None,   # or "bitsandbytes" if you use a 4-bit adapter
        temperature=1.5,
        min_p=0.1,
        top_p=None,
        max_new_tokens=4096,
        merge_adapter=True,
    )
