#!/usr/bin/env python3
"""Cold and warm latency: load-balancing endpoint vs queue endpoint.

로드밸런싱 엔드포인트와 큐 엔드포인트의 콜드/웜 지연 비교.

    python3 bench.py <lb_endpoint_id> <queue_endpoint_id> [--gap 60] [--warm 5] [--out results.json]

For each endpoint: one request after `gap` seconds idle (cold), then `warm`
requests back to back. The load-balancing call is POST /hello on
https://<id>.api.runpod.ai; the queue call is POST /runsync with the same input.
A load-balancing endpoint has no queue, so a request that arrives while no
worker is ready is refused ("no workers available") instead of waiting — the
docs recommend retrying, and every retry is recorded.
각 엔드포인트에 `gap` 초 쉰 뒤 1건(콜드), 이어서 `warm` 건을 보낸다. 로드밸런싱은
큐가 없으므로 준비된 워커가 없으면 기다리지 않고 거절한다. 재시도를 모두 기록한다.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]


def key() -> str:
    if os.environ.get("RUNPOD_API_KEY"):
        return os.environ["RUNPOD_API_KEY"]
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("RUNPOD_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("RUNPOD_API_KEY is not set. Run ./setup/init-env.sh")


def post(url: str, body: dict, timeout: float = 360):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": "Bearer " + key(), "Content-Type": "application/json",
        "User-Agent": "runpod-hols-serverless-04/1.0"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}"), time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:300]}, time.perf_counter() - t0


def lb_call(ep: str, name: str, retries: int = 12, wait: float = 5):
    """POST /hello, retrying while no worker is ready. Returns the row."""
    t0, attempts = time.perf_counter(), []
    for _ in range(retries):
        code, body, dt = post(f"https://{ep}.api.runpod.ai/hello", {"name": name})
        attempts.append({"status": code, "s": round(dt, 3), "error": body.get("error") if code != 200 else None})
        if code == 200:
            return {"ok": True, "total_s": round(time.perf_counter() - t0, 3), "attempts": attempts, "body": body}
        time.sleep(wait)
    return {"ok": False, "total_s": round(time.perf_counter() - t0, 3), "attempts": attempts}


def queue_call(ep: str, name: str):
    code, body, dt = post(f"https://api.runpod.ai/v2/{ep}/runsync", {"input": {"name": name}})
    return {"ok": code == 200 and body.get("status") == "COMPLETED", "total_s": round(dt, 3), "status": code,
            "delayTime_ms": body.get("delayTime"), "executionTime_ms": body.get("executionTime"),
            "workerId": body.get("workerId"), "job_status": body.get("status")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lb")
    ap.add_argument("queue")
    ap.add_argument("--gap", type=int, default=60)
    ap.add_argument("--warm", type=int, default=5)
    ap.add_argument("--out", default="results.json")
    a = ap.parse_args()
    rows = []
    for kind, ep, call in (("load_balancer", a.lb, lb_call), ("queue", a.queue, queue_call)):
        print(f"{kind}: idle {a.gap} s, then cold + {a.warm} warm", flush=True)
        time.sleep(a.gap)
        for i in range(a.warm + 1):
            r = call(ep, f"{kind}-{i}")
            r.update(endpoint=kind, n=i, phase="cold" if i == 0 else "warm",
                     utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            rows.append(r)
            line = {k: r.get(k) for k in ("endpoint", "phase", "ok", "total_s", "delayTime_ms", "executionTime_ms")}
            if "attempts" in r:  # Python 3.8: no dict | dict
                line["attempts"] = len(r["attempts"])
            print(json.dumps(line), flush=True)
    pathlib.Path(a.out).write_text(json.dumps(rows, indent=2) + "\n")
    print("->", a.out)


if __name__ == "__main__":
    main()
