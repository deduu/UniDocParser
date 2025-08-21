# app/llm/mm_adapter.py
import os
import base64
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# -------------------------
# Model family helpers
# -------------------------


def _shape(x):
    try:
        return tuple(getattr(x, "shape", None) or [])
    except Exception:
        return None


def _preview(s: str, n=200):
    s = s.replace("\n", "\\n")
    return (s[:n] + ("…" if len(s) > n else ""))


def _model_id(model) -> str:
    cfg = getattr(model, "config", None)
    if cfg is None:
        return ""
    return getattr(cfg, "name_or_path", "") or getattr(cfg, "_name_or_path", "") or ""


# Expand/adjust these as needed for your models
_QWEN_KEYS = ("qwen2.5-vl", "qwen2-vl", "qwen2.5-vl-instruct", "qwen2.5-vl-7b")
_LLAVA_KEYS = ("llava", "internvl", "llama-vision",
               "minicpm-v", "phi-3-vision", "idefics", "vila")


def _is_qwen_vl(model_id: str) -> bool:
    mid = (model_id or "").lower()
    return any(k in mid for k in _QWEN_KEYS)


def _is_llava_like(model_id: str) -> bool:
    mid = (model_id or "").lower()
    return any(k in mid for k in _LLAVA_KEYS)


def _safe_open_image(path: str) -> Optional[Image.Image]:
    try:
        if not path:
            return None
        if not os.path.exists(path):
            logger.warning("[mm] image_path not found: %s", path)
            return None
        img = Image.open(path).convert("RGB")
        return img
    except Exception as e:
        logger.warning("[mm] failed to open image_path=%s error=%r", path, e)
        return None


@dataclass
class ModelCapabilities:
    is_vlm: bool
    has_chat_template: bool


class MultimodalAdapter:
    """
    Normalizes messages (with mixed text/image blocks) to model-ready inputs.
    Works with AutoTokenizer/AutoProcessor-using models (Qwen2-VL, Qwen2.5-VL, LLaVA, etc.).
    """

    def __init__(self, model, tokenizer=None, processor=None):
        self.model = model
        self.tokenizer = tokenizer
        self.processor = processor

        # Detect capabilities
        cfg = getattr(model, "config", None)
        has_vision = False
        if cfg:
            has_vision = any(
                hasattr(cfg, attr)
                for attr in ("vision_config", "mm_vision_tower", "vision_tower", "perceiver_config")
            )
        has_chat_template = hasattr(self.tokenizer, "apply_chat_template") or hasattr(
            self.processor, "apply_chat_template")
        self.capabilities = ModelCapabilities(is_vlm=bool(self.processor and has_vision),
                                              has_chat_template=bool(has_chat_template))

    # -------------------------
    # parsing / helpers
    # -------------------------
    @staticmethod
    def _decode_data_url_to_image(url: str) -> Optional[Image.Image]:
        try:
            header, b64data = url.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            return Image.open(BytesIO(img_bytes)).convert("RGB")
        except Exception:
            return None

    def _gather_blocks(self, messages: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Image.Image]]:
        """
        Returns (chat_messages, images) where chat_messages is a list of {role, content}
        for chat templates, and images is a list of PIL.Image for VLMs (LLaVA-like path).
        This function ALSO inserts one "<image>" token per successfully loaded image.
        """
        chat_messages: List[Dict[str, Any]] = []
        images: List[Image.Image] = []

        for m in messages:
            role = m["role"]
            content = m["content"]

            # Simple string → pass through
            if isinstance(content, str):
                chat_messages.append({"role": role, "content": content})
                continue

            if isinstance(content, list):
                text_parts: List[str] = []

                for b in content:
                    btype = b.get("type")

                    if btype == "text":
                        txt = b.get("text", "")
                        if txt:
                            text_parts.append(txt)

                    elif btype in ("image", "image_path", "image_file"):
                        # Accept both unified "image" and legacy aliases
                        p = b.get("image_path") or b.get("path")
                        img = _safe_open_image(p)
                        if img is not None:
                            images.append(img)
                            # marker for LLaVA-like processors
                            text_parts.append("<image>")

                    elif btype == "image_url":
                        url = (b.get("image_url") or {}).get(
                            "url") or b.get("url")
                        if not url:
                            continue

                        if url.startswith("data:"):
                            img = self._decode_data_url_to_image(url)
                            if img is not None:
                                images.append(img)
                                text_parts.append("<image>")
                        elif url.startswith("file://"):
                            img = _safe_open_image(url[len("file://"):])
                            if img is not None:
                                images.append(img)
                                text_parts.append("<image>")
                        else:
                            # http(s): we don't fetch in local adapter; leave a visible placeholder if desired
                            text_parts.append("[image]")

                    # unknown block types → ignore

                # Collapse role’s composed content
                chat_messages.append(
                    {"role": role, "content": "\n".join(
                        p for p in text_parts if p)}
                )
            else:
                chat_messages.append({"role": role, "content": str(content)})

        return chat_messages, images

    def _to_qwen_messages(self, messages: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build Qwen-style multimodal messages:
        [{"role": "...", "content":[{"type":"image","image":PIL}, {"type":"text","text":"..."}]}]
        """
        qmsgs: List[Dict[str, Any]] = []

        for m in messages:
            role = m["role"]
            content = m["content"]
            items: List[Dict[str, Any]] = []

            if isinstance(content, str):
                if content:
                    items.append({"type": "text", "text": content})

            elif isinstance(content, list):
                for b in content:
                    t = b.get("type")

                    if t == "text":
                        txt = b.get("text", "")
                        if txt:
                            items.append({"type": "text", "text": txt})

                    elif t in ("image", "image_path", "image_file"):
                        p = b.get("image_path") or b.get("path")
                        img = _safe_open_image(p)
                        if img is not None:
                            items.append({"type": "image", "image": img})
                        else:
                            logger.warning(
                                "[mm] ignoring image block; cannot load PIL from path=%s", p)

                    elif t == "image_url":
                        url = (b.get("image_url") or {}).get(
                            "url") or b.get("url")
                        if not url:
                            continue
                        if url.startswith("data:"):
                            img = self._decode_data_url_to_image(url)
                            if img is not None:
                                items.append({"type": "image", "image": img})
                            else:
                                logger.warning(
                                    "[mm] bad data URL for image; skipping")
                        elif url.startswith("file://"):
                            img = _safe_open_image(url[len("file://"):])
                            if img is not None:
                                items.append({"type": "image", "image": img})
                            else:
                                logger.warning(
                                    "[mm] file:// image could not be opened: %s", url)
                        else:
                            # http(s) not fetched here for local models
                            logger.info(
                                "[mm] http(s) image_url present but not fetched in local adapter: %s", url)

            if items:
                qmsgs.append({"role": role, "content": items})

        img_count = sum(1 for qm in qmsgs for it in qm.get(
            "content", []) if it.get("type") == "image")
        logger.info(
            "[mm] _to_qwen_messages built %d msgs, %d images", len(qmsgs), img_count)
        return qmsgs

    # -------------------------
    # building inputs
    # -------------------------
    def build_inputs(
        self,
        messages: Iterable[Dict[str, Any]],
        device: str,
        default_system: Optional[str] = None,
        return_prompt_tokens: bool = True,
    ):
        """
        Returns (inputs_dict, prompt_token_count, decode_fn), where:
          - inputs_dict: kwargs for model.generate
          - prompt_token_count: int or 0 if unknown
          - decode_fn: callable to decode output ids → string
        """
        model_id = _model_id(self.model)
        is_qwen = _is_qwen_vl(model_id)
        is_llava = _is_llava_like(model_id)

        # -------------------------
        # Text-only (no VLM capability)
        # -------------------------
        if not self.capabilities.is_vlm or self.processor is None:
            chat_messages, _ = self._gather_blocks(messages)

            # Prefer processor/tokenizer chat template when available
            apply_template = None
            if hasattr(self.processor, "apply_chat_template"):
                apply_template = self.processor.apply_chat_template
            elif hasattr(self.tokenizer, "apply_chat_template"):
                apply_template = self.tokenizer.apply_chat_template

            if apply_template:
                text_prompt = apply_template(
                    chat_messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                parts = ["<|begin_of_text|>"]
                for m in chat_messages:
                    r = m["role"]
                    parts.append(
                        f"<|start_header_id|>{r}<|end_header_id|>\n{m['content']}")
                parts.append("<|start_header_id|>assistant<|end_header_id|>\n")
                text_prompt = "\n".join(parts)

            enc = self.tokenizer(text_prompt, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in enc.items()}
            prompt_len = inputs["input_ids"].size(1)  # <-- add

            def _decode(out_ids):
                # slice off the prompt
                gen = out_ids[0, prompt_len:]
                return self.tokenizer.decode(gen.tolist(), skip_special_tokens=True)

            prompt_tokens = prompt_len
            return inputs, (prompt_tokens if return_prompt_tokens else 0), _decode

            # enc = self.tokenizer(text_prompt, return_tensors="pt")
            # inputs = {k: v.to(device) for k, v in enc.items()}

            # def _decode(output_ids):
            #     return self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

            # prompt_tokens = inputs["input_ids"].size(1)
            # return inputs, (prompt_tokens if return_prompt_tokens else 0), _decode

        # -------------------------
        # Qwen2/2.5-VL family
        # -------------------------
        if is_qwen:
            # Build Qwen-style messages and collect images
            qmsgs = self._to_qwen_messages(messages)
            images_for_proc: List[Image.Image] = []
            for m in qmsgs:
                for item in m.get("content", []):
                    if item.get("type") == "image":
                        images_for_proc.append(item["image"])

            has_image = len(images_for_proc) > 0
            if not has_image:
                # If user provided image blocks but none could be opened, warn.
                had_image_blocks = any(
                    isinstance(m.get("content"), list) and any(
                        b.get("type") in ("image", "image_path",
                                          "image_file", "image_url")
                        for b in m.get("content")
                    ) for m in messages
                )
                if had_image_blocks:
                    logger.warning(
                        "[mm] Qwen branch: image blocks present but 0 PIL images loaded. Check paths & permissions.")

                # Fallback to text-only flow inside VLM
                chat_messages, _ = self._gather_blocks(messages)
                apply_template = None
                if hasattr(self.processor, "apply_chat_template"):
                    apply_template = self.processor.apply_chat_template
                elif hasattr(self.tokenizer, "apply_chat_template"):
                    apply_template = self.tokenizer.apply_chat_template

                if apply_template:
                    text_prompt = apply_template(
                        chat_messages, tokenize=False, add_generation_prompt=True
                    )
                else:
                    parts = ["<|begin_of_text|>"]
                    for m in chat_messages:
                        r = m["role"]
                        parts.append(
                            f"<|start_header_id|>{r}<|end_header_id|>\n{m['content']}")
                    parts.append(
                        "<|start_header_id|>assistant<|end_header_id|>\n")
                    text_prompt = "\n".join(parts)

                enc = self.tokenizer(text_prompt, return_tensors="pt")
                inputs = {k: v.to(device) for k, v in enc.items()}

                # Add this as suggestion
                prompt_len = int(inputs["input_ids"].size(
                    1)) if "input_ids" in inputs else 0

                def _decode(out_ids):
                    gen = out_ids[0]
                    if prompt_len:
                        gen = gen[prompt_len:]
                    # prefer tokenizer if available; fall back to processor.batch_decode
                    if self.tokenizer is not None:
                        return self.tokenizer.decode(gen.tolist(), skip_special_tokens=True)
                    if hasattr(self.processor, "batch_decode"):
                        return self.processor.batch_decode(gen.unsqueeze(0), skip_special_tokens=True)[0]
                    # last resort
                    return "".join(map(str, gen.tolist()))

                prompt_tokens = prompt_len
                return inputs, (prompt_tokens if return_prompt_tokens else 0), _decode

                # def _decode(out_ids):
                #     return self.tokenizer.decode(out_ids[0], skip_special_tokens=True)

                # prompt_tokens = inputs["input_ids"].size(1)
                # return inputs, (prompt_tokens if return_prompt_tokens else 0), _decode

            # Multimodal path: use chat template to produce TEXT; pass IMAGES separately
            apply_template = None
            if hasattr(self.processor, "apply_chat_template"):
                apply_template = self.processor.apply_chat_template
            elif hasattr(self.tokenizer, "apply_chat_template"):
                apply_template = self.tokenizer.apply_chat_template

            if apply_template is None:
                # Safe fallback template
                parts = ["<|begin_of_text|>"]
                for m in qmsgs:
                    r = m["role"]
                    segs = []
                    for it in m.get("content", []):
                        if it.get("type") == "text":
                            segs.append(it["text"])
                        elif it.get("type") == "image":
                            segs.append("<image>")
                    parts.append(
                        f"<|start_header_id|>{r}<|end_header_id|>\n" + "\n".join(segs))
                parts.append("<|start_header_id|>assistant<|end_header_id|>\n")
                text_prompt = "\n".join(parts)
            else:
                text_prompt = apply_template(
                    qmsgs, tokenize=False, add_generation_prompt=True
                )

            # IMPORTANT: pass text as str or [str]; images as flat list of PIL
            proc_inputs = self.processor(
                text=[text_prompt],
                images=images_for_proc,
                return_tensors="pt",
            )
            inputs = {k: v.to(device) for k, v in proc_inputs.items()}

            # Add this as suggestion
            prompt_len = int(inputs["input_ids"].size(
                1)) if "input_ids" in inputs else 0

            def _decode(out_ids):
                gen = out_ids[0]
                if prompt_len:
                    gen = gen[prompt_len:]
                # prefer tokenizer if available; fall back to processor.batch_decode
                if self.tokenizer is not None:
                    return self.tokenizer.decode(gen.tolist(), skip_special_tokens=True)
                if hasattr(self.processor, "batch_decode"):
                    return self.processor.batch_decode(gen.unsqueeze(0), skip_special_tokens=True)[0]
                # last resort
                return "".join(map(str, gen.tolist()))

            prompt_tokens = prompt_len

            # logger.info("[mm] BRANCH=qwen-vl multimodal images=%d",
            #             len(images_for_proc))
            # logger.info("[mm] prompt_preview=%r", _preview(text_prompt))
            # logger.info("[mm] inputs.keys=%s", list(inputs.keys()))
            # logger.info("[mm] input_ids.shape=%s",
            #             _shape(inputs.get("input_ids")))
            # logger.info("[mm] pixel_values.shape=%s",
            #             _shape(inputs.get("pixel_values")))
            # logger.info("[mm] prompt_len=%s", int(
            #     inputs["input_ids"].size(1)) if "input_ids" in inputs else 0)
            return inputs, (prompt_tokens if return_prompt_tokens else 0), _decode

        # ------------------------

            def _decode(out_ids):
                if hasattr(self.processor, "batch_decode"):
                    return self.processor.batch_decode(out_ids, skip_special_tokens=True)[0]
                return self.tokenizer.decode(out_ids[0], skip_special_tokens=True)

            prompt_tokens = int(inputs["input_ids"].size(
                1)) if "input_ids" in inputs else 0

            return inputs, (prompt_tokens if return_prompt_tokens else 0), _decode

        # -------------------------
        # LLaVA-like (default VLM path)
        # -------------------------
        # Build "<image>"-augmented text + images list
        chat_messages, images = self._gather_blocks(messages)

        # Prefer chat template to build text
        apply_template = None
        if hasattr(self.processor, "apply_chat_template"):
            apply_template = self.processor.apply_chat_template
        elif hasattr(self.tokenizer, "apply_chat_template"):
            apply_template = self.tokenizer.apply_chat_template

        if apply_template:
            text_prompt = apply_template(
                chat_messages, tokenize=False, add_generation_prompt=True
            )
        else:
            parts = ["<|begin_of_text|>"]
            for m in chat_messages:
                r = m["role"]
                parts.append(
                    f"<|start_header_id|>{r}<|end_header_id|>\n{m['content']}")
            parts.append("<|start_header_id|>assistant<|end_header_id|>\n")
            text_prompt = "\n".join(parts)

        proc_inputs = self.processor(
            text=[text_prompt],
            images=(images if images else None),
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in proc_inputs.items()}

        def _decode(out_ids):
            if hasattr(self.processor, "batch_decode"):
                return self.processor.batch_decode(out_ids, skip_special_tokens=True)[0]
            return self.tokenizer.decode(out_ids[0], skip_special_tokens=True)

        prompt_tokens = int(inputs["input_ids"].size(
            1)) if "input_ids" in inputs else 0
        return inputs, (prompt_tokens if return_prompt_tokens else 0), _decode
