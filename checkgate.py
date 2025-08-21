#!/usr/bin/env python3
import argparse, asyncio, time, random
from pathlib import Path
from PIL import Image

# ---- import your wrapper ----
from backend.core.hf_vlm_fig2tab_config import Fig2TabLLM  # or get_fig2tab_vlm

# ---- simple VRAM gate ----
def cuda_free_gb(device: str) -> float:
    import torch
    dev = torch.device(device)
    with torch.cuda.device(dev):
        free, total = torch.cuda.mem_get_info(dev)
    return free / 1e9

async def wait_for_free_vram(min_free_gb: float, device: str, poll_s: float = 0.1, timeout_s: float = 60):
    if min_free_gb <= 0:
        return
    start = time.perf_counter()
    while True:
        if cuda_free_gb(device) >= min_free_gb:
            return
        if time.perf_counter() - start > timeout_s:
            raise TimeoutError(f"VRAM gate timed out; need >= {min_free_gb} GB free")
        await asyncio.sleep(poll_s)

async def run_one(fig2tab: Fig2TabLLM, path: Path, use_path: bool, vram_gate_gb: float, sem: asyncio.Semaphore, idx: int):
    async with sem:  # concurrency limiter
        try:
            await wait_for_free_vram(vram_gate_gb, fig2tab.client.device)
        except Exception as e:
            return {"id": idx, "ok": False, "err": str(e), "latency": 0}

        t0 = time.perf_counter()
        try:
            if use_path:
                out = await fig2tab.generate_from_path(str(path))
            else:
                img = Image.open(path).convert("RGB")
                out = await fig2tab.generate(img)
            dt = time.perf_counter() - t0
            return {"id": idx, "ok": True, "latency": dt, "chars": len(out) if isinstance(out, str) else 0}
        except Exception as e:
            return {"id": idx, "ok": False, "err": repr(e), "latency": time.perf_counter() - t0}

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--images", nargs="+", required=True, type=Path)
    ap.add_argument("-c","--concurrency", type=int, default=2)
    ap.add_argument("-n","--requests", type=int, default=8, help="total number of requests")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--base-repo", default="unsloth/Qwen2.5-VL-7B-Instruct")
    ap.add_argument("--adapter-repo", default="ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Extract-Figure")
    ap.add_argument("--no-adapter", action="store_true")
    ap.add_argument("--merge-adapter", action="store_true")
    ap.add_argument("--use-path", action="store_true")
    ap.add_argument("--vram-gate-gb", type=float, default=0.0, help="min free GB required before each gen")
    args = ap.parse_args()

    # Build single shared model
    fig2tab = Fig2TabLLM(
        base_repo=args.base_repo,
        adapter_repo=None if args.no_adapter else args.adapter_repo,
        device=args.device,
        dtype=args.dtype,
        merge_adapter=args.merge_adapter,
    )

    sem = asyncio.Semaphore(args.concurrency)
    # Expand to N requests, cycling images
    jobs = []
    for j in range(args.requests):
        p = args.images[j % len(args.images)]
        jobs.append(run_one(fig2tab, p, args.use_path, args.vram_gate_gb, sem, j))

    t0 = time.perf_counter()
    results = await asyncio.gather(*jobs)
    total = time.perf_counter() - t0

    oks = [r for r in results if r["ok"]]
    errs = [r for r in results if not r["ok"]]
    if oks:
        latencies = [r["latency"] for r in oks]
        print(f"\nOK: {len(oks)} / {len(results)}  |  avg={sum(latencies)/len(latencies):.2f}s  "
              f"p95={sorted(latencies)[int(0.95*len(latencies))-1]:.2f}s  total={total:.2f}s")
    if errs:
        print("\nErrors:")
        for r in errs[:10]:
            print(f"  id={r['id']} err={r['err']}")
    print(f"\nThroughput: {len(results)/total:.2f} req/s  with concurrency={args.concurrency}  gate={args.vram_gate_gb} GB\n")

if __name__ == "__main__":
    asyncio.run(main())
