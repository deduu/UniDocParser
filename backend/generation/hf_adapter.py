# app/llm/local_client.py
import os
import json
import uuid
import time
import logging
import math
from dataclasses import dataclass, asdict
from threading import Thread
from typing import AsyncGenerator, Dict, Any, Iterable, Optional

import torch
import asyncio
import unsloth
from peft import PeftModel

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TextIteratorStreamer,
    AutoProcessor,
    AutoConfig, AutoModelForVision2Seq
)
from contextlib import nullcontext
from .limiter import VRAMLimiter
from .base import BaseLLM
from .mm_adapter import MultimodalAdapter

from backend.utils.vram import vram_scope, flush_vram, log_vram, log_memory_summary

# ---- Perf-friendly defaults ----
torch.backends.cuda.matmul.allow_tf32 = True
torch.set_float32_matmul_precision("high")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


logger = logging.getLogger(__name__)
if not logger.handlers:
    # Minimal sane logging if the app hasn't configured logging yet.
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@dataclass
class TokenPerf:
    run_id: str
    model_path: str
    device: str
    torch_dtype: str
    attn_impl: str
    quantization: Optional[str]
    gpu_name: Optional[str]
    torch_version: str
    transformers_version: str

    prompt_tokens: int
    generated_tokens: int
    total_tokens: int

    time_total_s: float
    time_prefill_s: Optional[float]  # None in non-streaming chat()
    time_decode_s: Optional[float]   # None in non-streaming chat()

    prefill_tps: Optional[float]
    decode_tps: Optional[float]
    total_tps: float

    first_token_latency_s: Optional[float]  # alias for time_prefill_s

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def sdpa_context():
    """
    Prefer the new torch.nn.attention.sdpa_kernel() (PyTorch ≥ 2.4),
    fall back to torch.backends.cuda.sdp_kernel() on older versions,
    otherwise no-op.
    """
    try:
        # New API (no deprecation warning)
        from torch.nn.attention import sdpa_kernel as _sdpa_kernel
        return _sdpa_kernel(enable_flash=True, enable_mem_efficient=True, enable_math=True)
    except Exception:
        try:
            # Old API (deprecated but works on older Torch)
            from torch.backends.cuda import sdp_kernel as _sdpa_kernel
            return _sdpa_kernel(enable_flash=True, enable_mem_efficient=True, enable_math=True)
        except Exception:
            return nullcontext()
        
from typing import Optional
# try:
#     from peft import PeftModel
#     # backend/main.py (very top, before any transformers imports happen)
#     try:
#         import unsloth  # must be before importing transformers
#     except Exception:
#         pass

# except Exception:
#     PeftModel = None

class LocalHuggingFaceClient(BaseLLM):
    def __init__(
        self,
        model_path: str,
        device: str = "cuda:0",
        dtype: str = "float16",
        quantization: Optional[str] = None,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,

        # finetuned
        base_model_hint: Optional[str] = None,   # e.g. "Qwen/Qwen2.5-VL-7B-Instruct"
        adapter_path: Optional[str] = None,      # e.g. "ZeArkh/Qwen2.5-...-unsloth-Extract-Figure"
        merge_adapter: bool = False, 
        # "flash_attention_2" | "sdpa" | None (auto)
        attn_implementation: Optional[str] = None,

    ):
        self.device = device
        self.model_path = model_path
        self.system_prompt = system_prompt or ""
        self.quantization = quantization
        self.last_metrics: Optional[Dict[str, Any]] = None
        self._vram = VRAMLimiter(device)
        self._concurrency = asyncio.Semaphore(
            int(os.getenv("LOCAL_LLM_MAX_CONCURRENCY", "16")))  # high cap; VRAM gate will be the real limiter
        # ---- Tokenizer ----
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, use_fast=False, trust_remote_code=True)

        # LLaMA typically has no pad token → map pad to eos to silence warnings
        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # ---- Quantization config (optional) ----
        quant_kwargs = {}
        if quantization == "bitsandbytes":
            from transformers import BitsAndBytesConfig
            quant_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=(
                    torch.bfloat16 if dtype.lower() in ("bf16", "bfloat16") else torch.float16
                ),
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

        # ---- Attention implementation ----
        attn_impl = attn_implementation or "flash_attention_2"
        if attn_impl == "flash_attention_2":
            try:
                import flash_attn  # noqa: F401
            except Exception:
                attn_impl = "sdpa"

        # ---- Model ----
        self.torch_dtype = getattr(torch, dtype)
         # ---- Try get a config from the target repo; otherwise fall back to base ----
        cfg = None
        model_id_for_processor = model_path
        try:
            cfg = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        except Exception as e:
            if base_model_hint is None and adapter_path is None:
                # no fallback → re-raise the original error
                raise
            # Use the base model's config (Qwen/Llama/Gemma etc.)
            base_id = base_model_hint or model_path
            cfg = AutoConfig.from_pretrained(base_id, trust_remote_code=True)
            model_id_for_processor = base_id  # processor should come from the base

        # cfg = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        has_vision = any(
            hasattr(cfg, k) for k in ("vision_config", "mm_vision_tower", "vision_tower", "perceiver_config")
        )

         # ---- Load base weights (either from model_path if it’s a full model repo,
        #      or from base_model_hint if we’re going to apply an adapter) ----
        is_adapter = adapter_path is not None
        weights_source = (base_model_hint if is_adapter else model_path)

        loader_kwargs = dict(
            config=cfg,
            torch_dtype=self.torch_dtype,
            device_map={"": device},
            low_cpu_mem_usage=True,
            attn_implementation=attn_impl,
            trust_remote_code=True,
            **quant_kwargs,
        )
        if has_vision:
            base_model = AutoModelForVision2Seq.from_pretrained(weights_source, **loader_kwargs)
        else:
            base_model = AutoModelForCausalLM.from_pretrained(weights_source, **loader_kwargs)

           # 3) Apply adapter if provided
        if adapter_path:
            if PeftModel is None:
                raise RuntimeError("peft is required: pip install peft")
            base_model = PeftModel.from_pretrained(base_model, adapter_path)
            if merge_adapter:
                base_model = base_model.merge_and_unload()
                
        self.model = base_model.eval()
        # if has_vision:
        #     self.model = AutoModelForVision2Seq.from_pretrained(
        #         model_path,
        #         torch_dtype=self.torch_dtype,
        #         device_map={"": device},
        #         low_cpu_mem_usage=True,
        #         attn_implementation=attn_impl,
        #         trust_remote_code=True,
        #         **quant_kwargs,
        #     )
        # else:
        #     self.model = AutoModelForCausalLM.from_pretrained(
        #         model_path,
        #         torch_dtype=self.torch_dtype,
        #         device_map={"": device},
        #         low_cpu_mem_usage=True,
        #         attn_implementation=attn_impl,
        #         trust_remote_code=True,
        #         **quant_kwargs,
        #     )
        # self.model.eval()

        # ---- Try processor (enables VLM mode when present) ----
        self.processor = None
        try:
            self.processor = AutoProcessor.from_pretrained(
                model_id_for_processor, trust_remote_code=True)
        except Exception:
            self.processor = None

        # ---- Multimodal adapter (detects if model is VLM) ----
        self.mm = MultimodalAdapter(
            self.model, tokenizer=self.tokenizer, processor=self.processor)
        self.is_vlm = self.mm.capabilities.is_vlm

        # Static info for logs
        self._attn_impl = attn_impl
        self._gpu_name = (
            torch.cuda.get_device_name(
                0) if torch.cuda.is_available() and "cuda" in device else None
        )
        import transformers as _tfv
        self._tf_version = _tfv.__version__
        self._torch_version = torch.__version__

    # ---------- Formatting ----------
    def _format_messages(self, messages: Iterable[Dict[str, str]]) -> str:
        formatted = ["<|begin_of_text|>"]
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted.append(
                    f"<|start_header_id|>system<|end_header_id|>\n{content}")
            elif role == "user":
                formatted.append(
                    f"<|start_header_id|>user<|end_header_id|>\n{content}")
            elif role == "assistant":
                formatted.append(
                    f"<|start_header_id|>assistant<|end_header_id|>\n{content}")
        formatted.append("<|start_header_id|>assistant<|end_header_id|>\n")
        return "\n".join(formatted)

    # ---------- Utilities ----------
    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer(text, add_special_tokens=False).input_ids)

    def _build_metrics(
        self,
        *,
        run_id: str,
        prompt_tokens: int,
        generated_tokens: int,
        time_total: float,
        time_prefill: Optional[float],
        time_decode: Optional[float],
    ) -> Dict[str, Any]:
        total_tokens = prompt_tokens + generated_tokens
        total_tps = (total_tokens / time_total) if time_total > 0 else None
        prefill_tps = (
            prompt_tokens / time_prefill) if (time_prefill and time_prefill > 0) else None
        decode_tps = (
            generated_tokens / time_decode) if (time_decode and time_decode > 0) else None

        perf = TokenPerf(
            run_id=run_id,
            model_path=self.model_path,
            device=self.device,
            torch_dtype=str(self.torch_dtype).replace("torch.", ""),
            attn_impl=self._attn_impl,
            quantization=self.quantization,
            gpu_name=self._gpu_name,
            torch_version=self._torch_version,
            transformers_version=self._tf_version,
            prompt_tokens=prompt_tokens,
            generated_tokens=generated_tokens,
            total_tokens=total_tokens,
            time_total_s=time_total,
            time_prefill_s=time_prefill,
            time_decode_s=time_decode,
            prefill_tps=prefill_tps,
            decode_tps=decode_tps,
            total_tps=total_tps if total_tps is not None else 0.0,
            first_token_latency_s=time_prefill,
        )
        return asdict(perf)

    def _log_metrics(self, metrics: Dict[str, Any]) -> None:
        # Single JSON line per run for easy grepping / jq
        logger.info("[llm_perf]%s", TokenPerf(**metrics).to_json())

   # ---------- Non-streaming chat (coarse total TPS only) ----------
    async def chat(self, messages: Iterable[Dict[str, Any]], **kwargs: Any) -> str:
        logger.info("chat mode")
        run_id = str(uuid.uuid4())
        # prompt = self._format_messages(messages)
        # enc = self.tokenizer(prompt, return_tensors="pt")
        # inputs = {k: v.to(self.device) for k, v in enc.items()}
        # prompt_tokens = enc.input_ids.size(1)

        log_vram("before-build")
        with vram_scope("build_inputs"):
            inputs, prompt_tokens, decode_fn = self.mm.build_inputs(
                messages, device=self.device, default_system=self.system_prompt
            )

        gcfg = getattr(self.model, "generation_config", None)
        gen_kwargs = {
            "max_new_tokens": kwargs.get("max_new_tokens", kwargs.get("max_tokens", 512)),
            "do_sample": kwargs.get("do_sample", True),
            "temperature": kwargs.get("temperature", 0.7),
            "pad_token_id": getattr(gcfg, "pad_token_id", self.tokenizer.pad_token_id),
            "eos_token_id": getattr(gcfg, "eos_token_id", self.tokenizer.eos_token_id),
            "use_cache": True,
        }

        # inside chat()/stream(), after gen_kwargs is defined:
        passthrough = {k: v for k, v in kwargs.items()
                    if k not in {"max_new_tokens","max_tokens","do_sample","temperature","on_metrics","ctx_window"}}
        gen_kwargs.update(passthrough)


        need_bytes = self._estimate_request_bytes(
            prompt_tokens, gen_kwargs["max_new_tokens"])
        timeout_s = float(os.getenv("LOCAL_LLM_VRAM_TIMEOUT_S", "15"))

        async with self._concurrency:
            async with self._vram.lease(need_bytes, timeout_s=timeout_s):
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t0 = time.perf_counter()
                with sdpa_context(), torch.inference_mode():
                    log_vram("before-generate")
                    with vram_scope("generate"):
                        output_ids = self.model.generate(
                            **inputs, **gen_kwargs)
                    # output_ids = self.model.generate(**inputs, **gen_kwargs)
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t1 = time.perf_counter()

        # text_full = self.tokenizer.decode(output[0], skip_special_tokens=True)
        # generated = text_full[len(prompt):].strip()
        generated = decode_fn(output_ids).strip()
        generated_tokens = self._count_tokens(generated)

        metrics = self._build_metrics(
            run_id=run_id,
            prompt_tokens=prompt_tokens,
            generated_tokens=generated_tokens,
            time_total=t1 - t0,
            time_prefill=None,
            time_decode=None,
        )
        self.last_metrics = metrics
        self._log_metrics(metrics)
        cb = kwargs.get("on_metrics")
        if callable(cb):
            cb(metrics)

          # Drop large tensors and flush right away
        try:
            del output_ids
            del inputs
        except Exception:
            pass
        flush_vram("post-decode")

        return generated

    # ---------- Streaming chat with detailed timing ----------

    async def stream(self, messages: Iterable[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[str, None]:
        logger.info("stream mode")
        run_id = str(uuid.uuid4())
        if self.is_vlm:
            logger.warning(
                "Streaming for VLM is experimental — enabling anyway.")
        # prompt = self._format_messages(messages)

        inputs, prompt_tokens, decode_fn = self.mm.build_inputs(
            messages, device=self.device, default_system=self.system_prompt
        )

        ctx_window = kwargs.get("ctx_window")
        if isinstance(ctx_window, int) and "input_ids" in inputs:
            if inputs["input_ids"].size(1) > ctx_window:
                inputs["input_ids"] = inputs["input_ids"][:, -ctx_window:]
                if "attention_mask" in inputs:
                    inputs["attention_mask"] = inputs["attention_mask"][:, -ctx_window:]

        # inputs = {k: v.to(self.device, non_blocking=True)
        #           for k, v in enc.items()}

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        gcfg = getattr(self.model, "generation_config", None)
        gen_kwargs = {
            "max_new_tokens": kwargs.get("max_new_tokens", kwargs.get("max_tokens", 512)),
            "do_sample": kwargs.get("do_sample", True),
            "temperature": kwargs.get("temperature", 0.7),
            "streamer": streamer,
            "pad_token_id": getattr(gcfg, "pad_token_id", self.tokenizer.pad_token_id),
            "eos_token_id": getattr(gcfg, "eos_token_id", self.tokenizer.eos_token_id),
            "use_cache": True,
        }
        # inside chat()/stream(), after gen_kwargs is defined:
        passthrough = {k: v for k, v in kwargs.items()
                    if k not in {"max_new_tokens","max_tokens","do_sample","temperature","on_metrics","ctx_window"}}
        gen_kwargs.update(passthrough)

        # gen_kwargs = {
        #     "max_new_tokens": kwargs.get("max_new_tokens", kwargs.get("max_tokens", 512)),
        #     # greedy faster; flip if you want sampling
        #     "do_sample": kwargs.get("do_sample", False),
        #     "temperature": kwargs.get("temperature", 0.7),
        #     "streamer": streamer,
        #     "pad_token_id": self.tokenizer.pad_token_id,
        #     "eos_token_id": self.tokenizer.eos_token_id,
        #     "use_cache": True,
        # }

        need_bytes = self._estimate_request_bytes(
            prompt_tokens, gen_kwargs["max_new_tokens"])
        timeout_s = float(os.getenv("LOCAL_LLM_VRAM_TIMEOUT_S", "15"))

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        t_start = None
        t_first = None
        t_end = None
        collected_chunks: list[str] = []

        def _generate():
            nonlocal t_start
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_start = time.perf_counter()
            with sdpa_context(), torch.inference_mode():
                self.model.generate(**inputs, **gen_kwargs)
            if torch.cuda.is_available():
                torch.cuda.synchronize()

        def _drain_streamer():
            nonlocal t_first
            for chunk in streamer:
                if t_first is None:
                    t_first = time.perf_counter()
                asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        async with self._concurrency:
            async with self._vram.lease(need_bytes, timeout_s=timeout_s):
                Thread(target=_generate, daemon=True).start()
                Thread(target=_drain_streamer, daemon=True).start()

                while True:
                    chunk = await queue.get()
                    if chunk is None:
                        t_end = time.perf_counter()
                        generated_text = "".join(collected_chunks).strip()
                        generated_tokens = self._count_tokens(generated_text)

                        time_total = (
                            t_end - t_start) if (t_end and t_start) else 0.0
                        time_prefill = (
                            t_first - t_start) if (t_first and t_start) else None
                        time_decode = (
                            t_end - t_first) if (t_end and t_first) else None

                        metrics = self._build_metrics(
                            run_id=run_id,
                            prompt_tokens=prompt_tokens,
                            generated_tokens=generated_tokens,
                            time_total=time_total,
                            time_prefill=time_prefill,
                            time_decode=time_decode,
                        )
                        self.last_metrics = metrics
                        self._log_metrics(metrics)
                        cb = kwargs.get("on_metrics")
                        if callable(cb):
                            cb(metrics)
                        break

                    collected_chunks.append(chunk)
                    yield chunk

    async def supports_tools(self) -> bool:
        return False

    def _estimate_request_bytes(self, prompt_tokens: int, max_new_tokens: int) -> int:
        cfg = self.model.config
        H = int(getattr(cfg, "hidden_size", 4096))
        L = int(getattr(cfg, "num_hidden_layers", 32))
        A = int(getattr(cfg, "num_attention_heads", 32))
        KVA = int(getattr(cfg, "num_key_value_heads", A))  # GQA aware

        # KV cache dtype ~ fp16/bf16 typically → 2 bytes (fall back to 2)
        dtype_bytes = 2
        try:
            dt = getattr(self.model, "dtype", self.torch_dtype)
            if dt == torch.float32:
                dtype_bytes = 4
            elif dt in (torch.float16, torch.bfloat16):
                dtype_bytes = 2
        except Exception:
            pass

        # KV per token ≈ 2 (K+V) * hidden_size * (KVA/A) * L * bytes
        kv_per_token = 2 * H * (KVA / max(1, A)) * L * dtype_bytes  # bytes

        total_tokens = prompt_tokens + max_new_tokens  # worst-case during decode
        kv_total = kv_per_token * total_tokens

        # Fudge in some activations/fragmentation (256MB) + 20% headroom
        overhead = 256 * 1024 * 1024
        need = int(math.ceil(kv_total * 1.2 + overhead))
        return need
