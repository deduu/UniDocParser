# --- add near the top ---
import math
import asyncio
import os
import torch


class VRAMLimiter:
    """
    Cooperative VRAM budget gate for a single GPU.
    - Uses torch.cuda.mem_get_info() to see free/total bytes.
    - Keeps an optimistic 'claimed' counter so two requests don't pass the gate at once.
    - Lets you 'lease' N bytes, then releases when generation finishes.
    """

    def __init__(self, device: str, safety_ratio: float = None,
                 reserve_mb: int = None, check_interval_s: float = None):
        self.device_index = self._parse_device(device)
        self._lock = asyncio.Lock()
        self._claimed = 0

        # Tunables via env, with reasonable defaults
        self.safety_ratio = safety_ratio or float(
            os.getenv("LOCAL_LLM_VRAM_SAFETY_RATIO", "0.92"))
        self.reserve_bytes = int((reserve_mb or int(
            os.getenv("LOCAL_LLM_VRAM_RESERVE_MB", "512"))) * 1024 * 1024)
        self.check_interval_s = check_interval_s or float(
            os.getenv("LOCAL_LLM_VRAM_CHECK_INTERVAL_S", "0.02"))

    def _parse_device(self, dev: str) -> int:
        # "cuda:3" -> 3 ; "cuda" -> 0 ; "cpu" -> -1 (not used)
        if dev.startswith("cuda"):
            parts = dev.split(":")
            return int(parts[1]) if len(parts) > 1 else 0
        return -1

    def _free_total(self) -> tuple[int, int]:
        free_b, total_b = torch.cuda.mem_get_info(self.device_index)
        return int(free_b), int(total_b)

    class _Lease:
        def __init__(self, outer, bytes_needed: int, timeout_s: float | None):
            self.outer = outer
            self.bytes_needed = int(bytes_needed)
            self.timeout_s = timeout_s

        async def __aenter__(self):
            import time
            start = time.perf_counter()
            while True:
                async with self.outer._lock:
                    free_b, total_b = self.outer._free_total()

                    # Don’t go past a % of total (safety cap), and keep a reserve for fragmentation/activations.
                    used_b = total_b - free_b
                    allowed_max = int(total_b * self.outer.safety_ratio)
                    available_for_claim = min(free_b - self.outer.reserve_bytes,
                                              allowed_max - used_b) - self.outer._claimed

                    if available_for_claim >= self.bytes_needed:
                        self.outer._claimed += self.bytes_needed
                        return  # lease granted

                if self.timeout_s is not None and (time.perf_counter() - start) > self.timeout_s:
                    raise TimeoutError(
                        f"VRAM lease timeout: need ~{self.bytes_needed/1e6:.0f} MB"
                    )
                await asyncio.sleep(self.outer.check_interval_s)

        async def __aexit__(self, exc_type, exc, tb):
            async with self.outer._lock:
                self.outer._claimed = max(
                    0, self.outer._claimed - self.bytes_needed)

    def lease(self, bytes_needed: int, timeout_s: float | None = None):
        return VRAMLimiter._Lease(self, bytes_needed, timeout_s)
