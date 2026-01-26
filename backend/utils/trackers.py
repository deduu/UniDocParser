import time
import functools
import logging
import os
import inspect
from inspect import iscoroutinefunction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_processing_time(func):
    def get_caller_filename():
        stack = inspect.stack()
        for frame_info in stack[2:]:
            filename = frame_info.filename
            if filename != __file__:  # skip decorator's own file
                return os.path.basename(filename)
        return os.path.basename(__file__)  # fallback

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        class_name = args[0].__class__.__name__ if args else "UnknownClass"
        caller = get_caller_filename()
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.info(
            f"[{caller} -> {class_name}] Function '{func.__name__}' took {end_time - start_time:.4f} seconds.")
        return result

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        class_name = args[0].__class__.__name__ if args else "UnknownClass"
        caller = get_caller_filename()
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.info(
            f"[{caller} -> {class_name}] Async function '{func.__name__}' took {end_time - start_time:.4f} seconds.")
        return result

    return async_wrapper if iscoroutinefunction(func) else sync_wrapper


def log_partial_message(message, word_count=100):
    words = message.split()
    partial_message = ' '.join(words[:word_count]) + (
        f"... (+{len(words) - word_count} more words)" if len(words) > word_count else "")
    logger.info(f"{partial_message}")
