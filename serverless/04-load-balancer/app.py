"""Load-balancing worker: a plain HTTP server, no handler and no queue.

로드밸런싱 워커: 핸들러도 큐도 없는 평범한 HTTP 서버.

Runpod routes https://<ENDPOINT_ID>.api.runpod.ai/<path> straight to this
server. It polls GET /ping on PORT_HEALTH: 204 while starting, 200 when ready;
anything else takes the worker out of the routing pool.
Runpod 은 https://<ENDPOINT_ID>.api.runpod.ai/<path> 를 이 서버로 바로 보낸다.
PORT_HEALTH 의 GET /ping 을 확인한다: 기동 중 204, 준비되면 200.
"""

import os
import socket
import time

import uvicorn
from fastapi import FastAPI, Response

STARTED = time.time()
# Simulated model load, so the 204 -> 200 transition is visible in the logs.
# 모델 로딩을 흉내 내 204 -> 200 전환이 로그에 보이도록 한다.
WARMUP_S = float(os.getenv("WARMUP_S", "5"))
app = FastAPI()
served = 0


@app.get("/ping")
def ping(response: Response):
    if time.time() - STARTED < WARMUP_S:
        response.status_code = 204
        return None
    return {"status": "healthy"}


@app.post("/hello")
def hello(body: dict):
    global served
    served += 1
    t0 = time.perf_counter()
    name = body.get("name", "World")
    return {
        "greeting": f"Hello, {name}!",
        "worker_id": os.getenv("RUNPOD_POD_ID", socket.gethostname()),
        "served_by_this_worker": served,
        "uptime_s": round(time.time() - STARTED, 1),
        "handler_ms": round((time.perf_counter() - t0) * 1000, 3),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "80")), log_level="info")
