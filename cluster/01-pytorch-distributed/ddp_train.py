"""Small DDP training loop on synthetic data; prints samples/s (launch with torchrun).

합성 데이터로 도는 작은 DDP 학습 루프. 초당 샘플 수를 출력한다 (torchrun 으로 실행).

    torchrun --nproc_per_node 1 ddp_train.py --out results/ddp_1gpu.json
    torchrun --nproc_per_node 2 ddp_train.py --out results/ddp_2gpu.json

The model is a stack of linear layers sized so that the gradient all-reduce
(about 400 MB per step in fp32) is a visible share of the step. Scaling
efficiency = samples/s on n GPUs / (n * samples/s on 1 GPU).
모델은 기울기 all-reduce (스텝당 fp32 약 400 MB) 가 스텝 시간에서 보이도록 크기를 잡았다.
확장 효율 = n GPU 처리량 / (n × 1 GPU 처리량).
"""

from __future__ import annotations

import argparse
import json
import os
import time

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--width", type=int, default=4096)
    ap.add_argument("--layers", type=int, default=6)
    ap.add_argument("--batch", type=int, default=256, help="per GPU / GPU 당")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--warmup", type=int, default=10)
    a = ap.parse_args()

    dist.init_process_group(backend="nccl")
    rank, world = dist.get_rank(), dist.get_world_size()
    local = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local)
    torch.manual_seed(0)

    layers = []
    for _ in range(a.layers):
        layers += [nn.Linear(a.width, a.width), nn.GELU()]
    model = DDP(nn.Sequential(*layers).cuda(), device_ids=[local])
    opt = torch.optim.SGD(model.parameters(), lr=1e-3)
    params = sum(p.numel() for p in model.parameters())
    x = torch.randn(a.batch, a.width, device="cuda")
    y = torch.randn(a.batch, a.width, device="cuda")

    def step() -> float:
        opt.zero_grad(set_to_none=True)
        loss = nn.functional.mse_loss(model(x), y)
        loss.backward()
        opt.step()
        return loss

    for _ in range(a.warmup):
        step()
    torch.cuda.synchronize()
    dist.barrier()
    t0 = time.perf_counter()
    for _ in range(a.steps):
        loss = step()
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    sps = a.batch * world * a.steps / dt
    if rank == 0:
        print(f"world {world}  params {params/1e6:.0f}M  step {dt/a.steps*1000:.1f} ms  "
              f"{sps:,.0f} samples/s  loss {loss.item():.4f}", flush=True)
        if a.out:
            os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
            with open(a.out, "w") as f:
                json.dump({"world_size": world, "params": params, "batch_per_gpu": a.batch,
                           "step_ms": round(dt / a.steps * 1000, 2), "samples_per_s": round(sps, 1),
                           "gpu": torch.cuda.get_device_name(local)}, f, indent=2)
                f.write("\n")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
