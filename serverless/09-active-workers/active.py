#!/usr/bin/env python3
"""Hold one active worker on a queue endpoint for a clock hour and probe it.

큐 엔드포인트에 활성 워커 하나를 정각부터 한 시간 유지하며 요청을 보낸다.

    python3 active.py <endpoint_id> --start 17:00 --minutes 60 --every 10 --out results/active.json

At --start: PATCH workers.min 1. Every --every minutes: one 1 s job with /runsync,
recording delayTime, executionTime, workerId and the worker's uptime. After
--minutes: PATCH workers.min 0. Then compare GET /v2/billing/serverless?serverlessId=…
for that hour with an hour of flex-only use. Uses the probe worker from ../06-autoscaling.
Control-plane calls use REST v2, api.runpod.io/v2 (v1 retired 2026-11-15, #101).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "06-autoscaling"))
from burst import call, key  # noqa: E402


def v2(method: str, endpoint: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"https://api.runpod.io/v2/serverless/{endpoint}",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers={"Authorization": "Bearer " + key(),
                                                         "Content-Type": "application/json",
                                                         "User-Agent": "runpod-hols-serverless-09/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def set_min_workers(endpoint: str, n: int) -> dict:
    # Resend the current workers object with only `min` changed, so max and idleTimeout cannot be reset.
    # 현재 workers 를 읽어 min 만 바꿔 보낸다. max 와 idleTimeout 이 초기화되지 않도록.
    w = {k: v for k, v in (v2("GET", endpoint).get("workers") or {}).items() if k in ("min", "max", "idleTimeout")}
    w["min"] = n
    return v2("PATCH", endpoint, {"workers": w}).get("workers") or {}


def probe(endpoint: str, label: str, inp: dict | None = None) -> dict:
    t = time.time()
    r = call(f"https://api.runpod.ai/v2/{endpoint}/runsync", {"input": inp or {"mode": "sleep", "seconds": 1, "tag": label}},
             timeout=200)
    o = r.get("output") or {}
    return {"at": dt.datetime.now().isoformat(timespec="seconds"), "label": label, "wall_s": round(time.time() - t, 2),
            "status": r.get("status"), "delayTime_ms": r.get("delayTime"), "executionTime_ms": r.get("executionTime"),
            "workerId": r.get("workerId"), "worker_uptime_s": o.get("worker_uptime_s")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint")
    ap.add_argument("--start", required=True, help="local HH:MM")
    ap.add_argument("--minutes", type=int, default=60)
    ap.add_argument("--every", type=int, default=10)
    ap.add_argument("--out", default="results/active.json")
    ap.add_argument("--input", help="job input as JSON (default: the 06 probe's 1 s sleep)")
    ap.add_argument("--flex", type=int, default=0, help="instead: N plain jobs, --every minutes apart, no PATCH")
    a = ap.parse_args()
    inp = json.loads(a.input) if a.input else None
    now = dt.datetime.now()
    start = now.replace(hour=int(a.start[:2]), minute=int(a.start[3:]), second=0, microsecond=0)
    log = {"endpoint": a.endpoint, "start": start.isoformat(), "minutes": a.minutes, "events": []}
    out = pathlib.Path(a.out)
    out.parent.mkdir(exist_ok=True)

    def save(ev):
        log["events"].append(ev)
        print(json.dumps(ev), flush=True)
        out.write_text(json.dumps(log, indent=1) + "\n")

    time.sleep(max(0, (start - dt.datetime.now()).total_seconds()))
    if a.flex:
        for n in range(a.flex):
            save(probe(a.endpoint, f"flex_{n}", inp))
            if n < a.flex - 1:
                time.sleep(a.every * 60)
        return
    save({"at": dt.datetime.now().isoformat(timespec="seconds"), "patch": set_min_workers(a.endpoint, 1)})
    end = start + dt.timedelta(minutes=a.minutes)
    n = 0
    while dt.datetime.now() < end - dt.timedelta(seconds=30):
        nxt = start + dt.timedelta(minutes=a.every * n + 2)
        time.sleep(max(0, (nxt - dt.datetime.now()).total_seconds()))
        if dt.datetime.now() >= end - dt.timedelta(seconds=30):
            break
        save(probe(a.endpoint, f"active_{n}", inp))
        n += 1
    time.sleep(max(0, (end - dt.datetime.now()).total_seconds()))
    save({"at": dt.datetime.now().isoformat(timespec="seconds"), "patch": set_min_workers(a.endpoint, 0)})
    time.sleep(120)
    save(probe(a.endpoint, "after_flex", inp))


if __name__ == "__main__":
    main()
