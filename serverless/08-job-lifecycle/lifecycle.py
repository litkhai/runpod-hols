#!/usr/bin/env python3
"""Walk one queue endpoint through every job state and record the raw responses.

큐 엔드포인트 하나로 작업의 모든 상태를 거쳐 보고 응답을 그대로 기록한다.

    python3 lifecycle.py <endpoint_id> --out results/lifecycle.json

Needs the probe worker from ../06-autoscaling (modes sleep, fail, error_output).
../06-autoscaling 의 프로브 워커가 필요하다.

Cases: runsync short and long, error_output, fail, cancel while queued and while
running, executionTimeout and ttl in the per-job policy, retry, purge-queue.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "06-autoscaling"))
from burst import call  # noqa: E402  (same auth and headers)

T0 = time.time()
LOG: dict = {}


def t() -> float:
    return round(time.time() - T0, 2)


def wait(base: str, job: str, limit: float = 180, every: float = 1.0) -> list:
    """Poll /status until a final state; return the distinct states seen with their times."""
    seen, end = [], time.time() + limit
    while time.time() < end:
        r = call(f"{base}/status/{job}")
        st = r.get("status")
        if not seen or seen[-1]["status"] != st:
            seen.append({"t": t(), "status": st, "resp": r})
        if st in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT") or "http_error" in r:
            break
        time.sleep(every)
    return seen


def case(name: str, fn) -> None:
    print(f"[{t():7.1f}] {name}", flush=True)
    LOG[name] = fn()
    print(json.dumps(LOG[name], default=str)[:400], flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint")
    ap.add_argument("--out", default="results/lifecycle.json")
    a = ap.parse_args()
    b = f"https://api.runpod.ai/v2/{a.endpoint}"
    run = lambda inp, policy=None: call(b + "/run", {"input": inp, **({"policy": policy} if policy else {})})

    def runsync_short():
        s = time.time(); r = call(b + "/runsync", {"input": {"mode": "sleep", "seconds": 1}}, timeout=200)
        return {"wall_s": round(time.time() - s, 1), "resp": r}

    def runsync_long():
        s = time.time(); r = call(b + "/runsync", {"input": {"mode": "sleep", "seconds": 100}}, timeout=300)
        out = {"wall_s": round(time.time() - s, 1), "resp": r}
        if r.get("id") and r.get("status") != "COMPLETED":
            out["after"] = wait(b, r["id"], 200)
        return out

    def error_output():
        j = run({"mode": "error_output"})
        return wait(b, j["id"])

    def fail():
        j = run({"mode": "fail"})
        return wait(b, j["id"])

    def cancel_running():
        j = run({"mode": "sleep", "seconds": 60})
        states = wait(b, j["id"], limit=20)  # until IN_PROGRESS or 20 s
        while states[-1]["status"] != "IN_PROGRESS" and time.time() - T0 < 600:
            states += wait(b, j["id"], limit=5)
        c = call(f"{b}/cancel/{j['id']}", {})
        return {"before": states, "cancel": c, "after": wait(b, j["id"], 30),
                "later": call(f"{b}/status/{j['id']}")}

    def execution_timeout():
        j = run({"mode": "sleep", "seconds": 30}, {"executionTimeout": 5000})
        return wait(b, j["id"], 120)

    def cancel_queued_and_purge():
        # fill both workers' slots so later jobs stay IN_QUEUE
        fill = [run({"mode": "sleep", "seconds": 40, "tag": f"fill{i}"}) for i in range(12)]
        q = [run({"mode": "sleep", "seconds": 1, "tag": f"q{i}"}) for i in range(4)]
        time.sleep(3)
        st = {x["id"]: call(f"{b}/status/{x['id']}").get("status") for x in q}
        c = call(f"{b}/cancel/{q[0]['id']}", {})
        p = call(f"{b}/purge-queue", {})
        time.sleep(2)
        after = {x["id"]: call(f"{b}/status/{x['id']}").get("status") for x in q}
        h = call(b + "/health")
        fills = {x["id"]: wait(b, x["id"], 150)[-1]["status"] for x in fill}
        return {"queued_before": st, "cancel_first": c, "purge": p, "after": after, "health_after_purge": h,
                "fill_final": fills}

    def ttl():
        fill = [run({"mode": "sleep", "seconds": 40, "tag": f"fill{i}"}) for i in range(12)]
        j = run({"mode": "sleep", "seconds": 1}, {"ttl": 10000})
        out = {"ttl_job": wait(b, j["id"], 150, every=2)}
        out["fill_final"] = [wait(b, x["id"], 150)[-1]["status"] for x in fill]
        return out

    def retry():
        j = run({"mode": "fail"})
        first = wait(b, j["id"])
        r = call(f"{b}/retry/{j['id']}", {})
        return {"first": first[-1], "retry": r, "after": wait(b, j["id"])}

    for n, f in [("runsync_short", runsync_short), ("error_output", error_output), ("fail", fail),
                 ("retry", retry), ("cancel_running", cancel_running), ("execution_timeout", execution_timeout),
                 ("cancel_queued_and_purge", cancel_queued_and_purge), ("ttl", ttl), ("runsync_long", runsync_long)]:
        try:
            case(n, f)
        except Exception as e:  # keep going, record the failure
            LOG[n] = {"exception": repr(e)}
            print(n, "exception", e, flush=True)
        pathlib.Path(a.out).parent.mkdir(exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(LOG, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
