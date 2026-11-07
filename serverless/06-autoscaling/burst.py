#!/usr/bin/env python3
"""Send a burst of jobs to a queue endpoint and record how it scales.

큐 엔드포인트에 작업을 한꺼번에 보내고 어떻게 늘어나는지 기록한다.

    python3 burst.py <endpoint_id> --jobs 50 --seconds 2 --label queue_delay_c1 --out results/queue_delay_c1.json

Submits every job with /run at once, polls /status until all finish, and every
`--sample` seconds saves GET /v2/serverless/<id>/workers (status per worker).
Per job: delayTime, executionTime, workerId and the handler's own timing
(started_at, running_at_start) from the probe worker in this folder.
모든 작업을 /run 으로 한꺼번에 보내고, 끝날 때까지 /status 를 확인하며,
--sample 초마다 워커 목록을 저장한다.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
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
    raise SystemExit("RUNPOD_API_KEY is not set")


def call(url: str, body=None, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET",
                                 headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json",
                                          "User-Agent": "runpod-hols-serverless-06/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:200]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint")
    ap.add_argument("--jobs", type=int, default=50)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--sample", type=float, default=3.0)
    ap.add_argument("--label", default="burst")
    ap.add_argument("--out", default="results/burst.json")
    a = ap.parse_args()
    base = f"https://api.runpod.ai/v2/{a.endpoint}"
    t0 = time.time()
    with cf.ThreadPoolExecutor(16) as ex:
        subs = list(ex.map(lambda i: (i, time.time(), call(base + "/run", {"input": {"mode": "sleep", "seconds": a.seconds, "tag": i}})),
                           range(a.jobs)))
    jobs = {s[2]["id"]: {"i": s[0], "submitted": round(s[1] - t0, 3)} for s in subs if "id" in s[2]}
    print(f"{a.label}: submitted {len(jobs)} in {time.time() - t0:.1f} s", flush=True)
    samples, pending, last = [], set(jobs), 0.0
    while pending and time.time() - t0 < 1800:
        if time.time() - last >= a.sample:
            last = time.time()
            w = call(f"https://api.runpod.io/v2/serverless/{a.endpoint}/workers")
            ws = [{"id": x.get("id"), "status": x.get("status")} for x in (w.get("workers") or [])]
            h = call(base + "/health")
            samples.append({"t": round(last - t0, 1), "workers": ws, "health": h.get("workers"), "jobs": h.get("jobs")})
        with cf.ThreadPoolExecutor(16) as ex:
            res = list(ex.map(lambda j: (j, call(base + "/status/" + j)), list(pending)))
        for j, r in res:
            if r.get("status") in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
                pending.discard(j)
                jobs[j].update(status=r.get("status"), done=round(time.time() - t0, 1), delayTime_ms=r.get("delayTime"),
                               executionTime_ms=r.get("executionTime"), workerId=r.get("workerId"), output=r.get("output"))
        time.sleep(1)
    done = [v for v in jobs.values() if "done" in v]
    workers = sorted({v.get("workerId") for v in done if v.get("workerId")})
    peak = max((len([x for x in s["workers"] if x["status"] in ("RUNNING", "running")]) for s in samples), default=0)
    summary = {"label": a.label, "jobs": a.jobs, "seconds_per_job": a.seconds, "completed": len(done),
               "wall_s": round(max((v["done"] for v in done), default=0), 1), "workers_used": len(workers),
               "peak_running_workers": peak,
               "delay_s_min_max": [round(min(v["delayTime_ms"] for v in done) / 1000, 1), round(max(v["delayTime_ms"] for v in done) / 1000, 1)] if done else None}
    print(json.dumps(summary), flush=True)
    pathlib.Path(a.out).parent.mkdir(exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps({"summary": summary, "jobs": jobs, "samples": samples}, indent=1) + "\n")


if __name__ == "__main__":
    main()
