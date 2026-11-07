"""Lab 10: the smallest useful Flash app — one CPU queue endpoint, no Dockerfile, no handler.

실습 10: 가장 작은 Flash 앱 — CPU 큐 엔드포인트 하나, Dockerfile 도 핸들러도 없이.

    rp flash dev main.py --once     # temporary endpoint, run main(), delete
    rp flash deploy                 # persistent endpoint
    rp flash undeploy --app lab10-flash
"""
import time

import runpod

app = runpod.App("lab10-flash")


@app.queue(name="lab10-cpu", cpu="cpu3c-2-4", workers=(0, 2), idle_timeout=5, dependencies=["numpy"])
def describe(n: int) -> dict:
    # Runs on the Runpod worker: imports go inside the function.
    import os
    import platform
    import socket

    import numpy as np

    t = time.time()
    a = np.random.rand(n, n)
    s = float((a @ a).sum())
    return {"n": n, "sum": s, "matmul_s": round(time.time() - t, 3), "python": platform.python_version(),
            "numpy": np.__version__, "host": socket.gethostname(), "worker_id": os.environ.get("RUNPOD_POD_ID"),
            "cwd": os.getcwd()}


@runpod.local_entrypoint
def main():
    for i in range(3):
        t = time.time()
        r = describe.remote(300)
        print(f"call {i}: {time.time() - t:.1f} s -> {r}", flush=True)
