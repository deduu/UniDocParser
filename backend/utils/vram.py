# app/utils/vram.py
import gc
import logging
from contextlib import contextmanager
from typing import Optional

import torch

log = logging.getLogger(__name__)


def _mem(device: int = 0) -> Optional[dict]:
    if not torch.cuda.is_available():
        return None
    props = torch.cuda.get_device_properties(device)
    return {
        "alloc": torch.cuda.memory_allocated(device),
        "reserved": torch.cuda.memory_reserved(device),
        "peak": torch.cuda.max_memory_allocated(device),
        "total": props.total_memory,
    }


def _fmt(mem: Optional[dict]) -> str:
    if mem is None:
        return "CUDA not available"
    gb = 1024**3
    return (f"alloc={mem['alloc']/gb:.2f}GB "
            f"reserved={mem['reserved']/gb:.2f}GB "
            f"peak={mem['peak']/gb:.2f}GB "
            f"total={mem['total']/gb:.2f}GB")


def log_vram(tag: str = "vram", device: int = 0) -> None:
    """Log current VRAM usage (allocated/reserved/peak/total)."""
    try:
        log.info("[vram:%s] %s", tag, _fmt(_mem(device)))
    except Exception as e:
        log.warning("[vram:%s] log failed: %r", tag, e)


def flush_vram(
    tag: str = "flush",
    device: int = 0,
    *,
    sync: bool = True,
    gc_collect: bool = True,
    reset_peak: bool = True,
    ipc_collect: bool = False,
) -> None:
    """
    Flush CUDA caching allocator & log before/after.

    - sync: synchronize before flushing (cleaner accounting)
    - gc_collect: run Python GC to drop orphan tensors
    - reset_peak: reset peak memory stats so next peak is meaningful
    - ipc_collect: call torch.cuda.ipc_collect() (rarely needed)
    """
    if not torch.cuda.is_available():
        log.info("[vram:%s] CPU-only; nothing to flush.", tag)
        return
    try:
        before = _mem(device)
        if sync:
            torch.cuda.synchronize(device)
        if gc_collect:
            gc.collect()
        torch.cuda.empty_cache()
        if ipc_collect and hasattr(torch.cuda, "ipc_collect"):
            torch.cuda.ipc_collect()
        if reset_peak:
            torch.cuda.reset_peak_memory_stats(device)
        after = _mem(device)
        # log.info("[vram:%s] before: %s", tag, _fmt(before))
        # log.info("[vram:%s]  after: %s", tag, _fmt(after))
    except Exception as e:
        log.warning("[vram:%s] flush failed: %r", tag, e)


@contextmanager
def vram_scope(tag: str, device: int = 0, *, reset_peak_on_exit: bool = True):
    """
    Context manager that logs VRAM on enter, and flushes/logs on exit.
    Use around heavyweight steps (build_inputs, generate, etc.).
    """
    # log_vram(f"{tag}:enter", device)
    try:
        yield
    finally:
        flush_vram(f"{tag}:exit", device=device, reset_peak=reset_peak_on_exit)


def log_memory_summary(tag: str = "summary", device: int = 0) -> None:
    """Dump PyTorch allocator summary to logs."""
    if not torch.cuda.is_available():
        return
    try:
        txt = torch.cuda.memory_summary(device=device)  # full summary
        log.info("[vram:%s]\n%s", tag, txt)
    except Exception as e:
        log.warning("[vram:%s] memory_summary failed: %r", tag, e)
