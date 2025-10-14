import logging
from logging.handlers import RotatingFileHandler
import os
import json
from PIL import Image


def configure_logging():
    os.makedirs("logs", exist_ok=True)
    log_file = "logs/UniDocParser.log"

    # Check if handler is already set (avoid duplicate & open file leaks)
    root_logger = logging.getLogger()
    # --- <— new: strip out any pre-existing handlers so we don’t double-print
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # Create file handler
    handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Optional: also add console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def safe_context_dump(ctx, image_preview_len: int = 6) -> str:
    HEAVY_KEYS = {"image_base64", "image", "thumbnail", "encoded"}

    def shorten(value, key=None):
        # If key name suggests it's heavy → shorten aggressively
        if key in HEAVY_KEYS and isinstance(value, str):
            return value[:image_preview_len] + "..."

        # Fallback: shorten long base64-like strings
        if isinstance(value, str) and len(value) > image_preview_len:
            if all(c.isalnum() or c in "+/=" for c in value[:50]):
                return value[:image_preview_len] + "..."
        return value

    def traverse(obj):
        try:
            if isinstance(obj, list):
                return [traverse(o) for o in obj]

            elif isinstance(obj, dict):
                return {
                    k: traverse(v) if not isinstance(v, str) else shorten(v, k)
                    for k, v in obj.items()
                }

            elif hasattr(obj, "model_dump"):
                return traverse(obj.model_dump())

            elif isinstance(obj, Image.Image):
                return f"<Image size={obj.size} mode={obj.mode}>"

            else:
                return shorten(obj)
        except Exception as e:
            return f"<error: {e.__class__.__name__}>"

    try:
        compact = traverse(ctx)
        return json.dumps(compact, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"<failed to serialize ctx: {e}>"
