# from backend.core.ft_vlm_fig2tab_config import fig2tab_vlm
from backend.core.hf_vlm_fig2tab_config import get_fig2tab_vlm

# fig2tab_vlm = get_fig2tab_vlm()

import asyncio
import base64
import io
import logging
from typing import Any, Dict, List, Optional

from PIL import Image
# <-- use the LAZY getter
from backend.core.hf_vlm_fig2tab_config import get_fig2tab_vlm
from backend.utils.safe_paths import ensure_parent_dir

logger = logging.getLogger(__name__)


def _data_url_to_pil(url: str) -> Image.Image:
    header, b64data = url.split(",", 1)
    return Image.open(io.BytesIO(base64.b64decode(b64data))).convert("RGB")


def _coerce_to_pil(v: Any) -> Image.Image:
    if isinstance(v, Image.Image):
        return v.convert("RGB")
    if isinstance(v, (bytes, bytearray)):
        return Image.open(io.BytesIO(v)).convert("RGB")
    if isinstance(v, str):
        if v.startswith("data:"):
            return _data_url_to_pil(v)
        # assume filesystem path
        return Image.open(v).convert("RGB")
    raise KeyError("No usable image payload")


async def _fig_to_table_async(figure_list: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    vlm = get_fig2tab_vlm()  # lazy init; won’t explode at import time
    out: List[Dict[str, Any]] = []
    # logger.info(f"pages: {pages}")

    page_lookup = {p["index"]: p for p in pages}

    # logger.info(f"page_lookup: {page_lookup}")
    for rec in figure_list:
        # page_el = page_lookup.get(rec.get("page_num"))
        page_el = page_lookup.get(rec.get("page_num"))

        # logger.info(f"page_el: {page_el}")
        image_path = ensure_parent_dir(page_el["image"])

        img_val: Optional[Any] = (
            rec.get("pil_image")
            or rec.get("image")
            or rec.get("image_path")
            or rec.get("path")
        )
        if img_val is None:
            logger.warning(
                "[fig2tab] skipping figure without image keys: %s", rec.keys())
            out.append(rec)
            continue

        try:
            pil = _coerce_to_pil(img_val)
        except Exception as e:
            logger.exception("[fig2tab] failed to open image: %r", e)
            out.append(rec)
            continue

        try:
            # Fig2TabLLM.generate is async
            text = await vlm.generate(pil, image_path)
            rec["generated_text"] = text
        except Exception as e:
            logger.exception("[fig2tab] VLM generate failed: %r", e)
        out.append(rec)
    return out


def fig_to_table(figure_list: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Synchronous facade used by the thread-executed step.
    Safe to call asyncio.run() here because ExtractImagesStep.run() is executed
    inside asyncio.to_thread (i.e., not on the main event loop thread).
    """
    return asyncio.run(_fig_to_table_async(figure_list, pages))
# Figure to Table VLM
# def fig_to_table(figure_list):

#     for i, image in enumerate(figure_list):
#         output = fig2tab_vlm.generate(image["pil_image"])
#         figure_list[i]["generated_text"] = output

#     return figure_list


def take_data(result_text):
    data_text = result_text
    if "data:" in data_text:
        # split the text by data:
        data_text = data_text.split("data:")[1].strip()
        if "enddata;" in data_text:
            data_text = data_text.split("enddata;")[0].strip()
        else:
            data_text = data_text.split("Concise Description:")[0].strip()
    else:
        return take_desc(result_text)

    return data_text


def take_desc(result_text):
    desc_text = result_text
    if "Short Description:" not in desc_text:
        return ""
    desc_text = desc_text.split("Short Description:")[1].strip()
    return desc_text


def take_caption(result_text):
    caption_text = result_text
    # check if the text contains Concise Description:
    if "Concise Description:" in caption_text:
        caption_text = caption_text.split("Concise Description:")[1].strip()
    elif "addCriterion:" in caption_text:
        caption_text = caption_text.split("addCriterion:")[1].strip()
    else:
        return ""
    caption_text = caption_text.split("\n")[0].strip()
    return caption_text


def take_type(result_text):
    type_text = result_text
    if "Type:" not in type_text:
        return "image"
    type_text = type_text.split("Type:")[1].strip()
    type_text = type_text.split("\n")[0].strip()
    return type_text.lower()


def extract_images(pages, figure_list):

    figure_list = fig_to_table(figure_list, pages)

    for i, fig in enumerate(figure_list):
        logger.info(
            f"Figure: {fig} and generated_text: {fig['generated_text']}")
        # check if the result is empty
        if fig["generated_text"] == "":
            continue

        for el in pages[fig["page_num"]]["elements"]:
            if el["idx"] == fig["idx"]:
                el["text"] = take_data(fig["generated_text"])
                el['image_metadata']["image_type"] = take_type(
                    fig["generated_text"])
                el['image_metadata']["caption"] = take_caption(
                    fig["generated_text"])
                el['image_metadata']["description"] = take_desc(
                    fig["generated_text"])
                break

    return pages
