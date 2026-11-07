"""All-reduce bandwidth sweep over NCCL, one process per GPU (launch with torchrun).

NCCL all-reduce 대역폭 측정. GPU 마다 프로세스 하나 (torchrun 으로 실행).

    torchrun --nproc_per_node 2 nccl_bench.py --out results/nccl_2x4090.json

Reports algbw = bytes / time and busbw = algbw * 2(n-1)/n, the same definitions
as nccl-tests, so the numbers compare with the link speed.
nccl-tests 와 같은 정의로 algbw, busbw 를 계산한다. busbw 가 링크 속도와 비교되는 값이다.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import time

import torch
import torch.distributed as dist


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--min-mb", type=float, default=1)
    ap.add_argument("--max-mb", type=float, default=1024)
    ap.add_argument("--iters", type=int, default=20)
    ap.add_argument("--warmup", type=int, default=5)
    a = ap.parse_args()

    dist.init_process_group(backend="nccl")
    rank, world = dist.get_rank(), dist.get_world_size()
    local = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local)

    rows = []
    mb = a.min_mb
    while mb <= a.max_mb:
        n = int(mb * 2**20) // 4
        x = torch.ones(n, dtype=torch.float32, device="cuda")
        for _ in range(a.warmup):
            dist.all_reduce(x)
        torch.cuda.synchronize()
        dist.barrier()
        t0 = time.perf_counter()
        for _ in range(a.iters):
            dist.all_reduce(x)
        torch.cuda.synchronize()
        dt = (time.perf_counter() - t0) / a.iters
        # Slowest rank sets the time, as in nccl-tests.
        # 가장 느린 rank 의 시간을 쓴다 (nccl-tests 와 같음).
        t = torch.tensor([dt], device="cuda")
        dist.all_reduce(t, op=dist.ReduceOp.MAX)
        dt = t.item()
        size = n * 4
        algbw = size / dt / 1e9
        busbw = algbw * 2 * (world - 1) / world
        rows.append({"bytes": size, "time_us": round(dt * 1e6, 1), "algbw_GBps": round(algbw, 2), "busbw_GBps": round(busbw, 2)})
        if rank == 0:
            print(f"{size:>12d} B  {dt*1e6:10.1f} us  algbw {algbw:7.2f} GB/s  busbw {busbw:7.2f} GB/s", flush=True)
        del x
        mb *= 2

    if rank == 0 and a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w") as f:
            json.dump({
                "world_size": world,
                "nnodes": int(os.environ.get("NNODES", os.environ.get("NUM_NODES", "1"))),
                "host": socket.gethostname(),
                "gpu": torch.cuda.get_device_name(local),
                "torch": torch.__version__,
                "nccl": ".".join(map(str, torch.cuda.nccl.version())),
                "rows": rows,
            }, f, indent=2)
            f.write("\n")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
