"""The code you develop on the Pod and then serve from Serverless, unchanged.

Pod 에서 개발하고, 그대로 Serverless 에서 서빙하는 코드.

Input:  {"n": 4096}   — size of a square matrix multiplied on the GPU
Output: GPU name, where this file was loaded from, and the multiply time.

Test on the Pod:   python handler.py --test_input '{"input": {"n": 2048}}'
"""

import os
import time

import runpod
import torch

# Loaded once per worker, not per job.
# 작업마다가 아니라 워커마다 한 번 로드된다.
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def handler(job):
    n = int(job["input"].get("n", 4096))
    a = torch.randn(n, n, device=DEVICE)
    torch.cuda.synchronize() if DEVICE == "cuda" else None
    t = time.time()
    (a @ a).sum().item()
    elapsed = time.time() - t
    return {
        "device": torch.cuda.get_device_name(0) if DEVICE == "cuda" else "cpu",
        "loaded_from": os.path.abspath(__file__),
        "runpod_sdk": runpod.__version__,
        "torch": torch.__version__,
        "n": n,
        "matmul_s": round(elapsed, 4),
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
