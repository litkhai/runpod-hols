#!/usr/bin/env python3
"""Hold one active worker on a queue endpoint for a clock hour and probe it.

큐 엔드포인트에 활성 워커 하나를 정각부터 한 시간 유지하며 요청을 보낸다.

    python3 active.py <endpoint_id> --start 17:00 --minutes 60 --every 10 --out results/active.json

At --start: PATCH workersMin 1. Every --every minutes: one 1 s job with /runsync,
recording delayTime, executionTime, workerId and the worker's uptime. After
--minutes: PATCH workersMin 0. Then compare /billing/endpoints for that hour with
an hour of flex-only use. Uses the probe worker from ../06-autoscaling.
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


def patch(endpoint: str, body: dict) -> dict:
    req = urllib.request.Request(f"https://rest.runpod.io/v1/endpoints/{endpoint}", data=json.dumps(body).encode(),
                                 method="PATCH", headers={"Authorization": "Bearer " + key(),
                                                          "Content-Type": "application/json",
                                                          "User-Agent": "runpod-hols-serverless-09/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    return {k: d.get(k) for k in ("workersMin", "workersMax", "idleTimeout")}


def probe(endpoint: str, label: str) -> dict:
    t = time.time()
    r = call(f"https://api.runpod.ai/v2/{endpoint}/runsync", {"input": {"mode": "sleep", "seconds": 1, "tag": label}},
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
    a = ap.parse_args()
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
    save({"at": dt.datetime.now().isoformat(timespec="seconds"), "patch": patch(a.endpoint, {"workersMin": 1})})
    end = start + dt.timedelta(minutes=a.minutes)
    n = 0
    while dt.datetime.now() < end - dt.timedelta(seconds=30):
        nxt = start + dt.timedelta(minutes=a.every * n + 2)
        time.sleep(max(0, (nxt - dt.datetime.now()).total_seconds()))
        if dt.datetime.now() >= end - dt.timedelta(seconds=30):
            break
        save(probe(a.endpoint, f"active_{n}"))
        n += 1
    time.sleep(max(0, (end - dt.datetime.now()).total_seconds()))
    save({"at": dt.datetime.now().isoformat(timespec="seconds"), "patch": patch(a.endpoint, {"workersMin": 0})})
    time.sleep(120)
    save(probe(a.endpoint, "after_flex"))


if __name__ == "__main__":
    main()
