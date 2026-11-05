#!/usr/bin/env python3
"""T6 (#8): alternate FlashBoot on and off on ONE endpoint, so cold starts can be compared on the same host.

Env: RUNPOD_API_KEY, ENDPOINT_ID, N (cold probes, default 6), GAP_S (idle gap before each cold probe, default 180)
Usage: python3 flashboot_alternate.py
Before probe i, FlashBoot is set to on for even i and off for odd i (PATCH /endpoints/{id}, REST v1).
Each probe is one request after the gap (cold) and one right after (warm), in coldstart_probe.py's row
format plus a "flashboot" field, so coldstart_phases.py can split the cold starts. C22: from a 60 s gap
on, every request got a new container; 180 s leaves margin.
Output: $OUT (default results/flashboot_alternate.json).
"""
import json, os, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pod_sweep import api, load_env  # noqa: E402

load_env()
KEY = os.environ["RUNPOD_API_KEY"]
EP = os.environ["ENDPOINT_ID"]
N = int(os.environ.get("N", "6"))
GAP = int(os.environ.get("GAP_S", "180"))
OUT = os.environ.get("OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "flashboot_alternate.json")
PAYLOAD = {"input": {"prompt": "Say hello in one sentence.", "sampling_params": {"max_tokens": 32}}}


def call(path, data=None):
    req = urllib.request.Request(
        f"https://api.runpod.ai/v2/{EP}{path}",
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "User-Agent": "runpod-hols-inference-characterization/1.0"},
        method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


rows = []
for i in range(N):
    fb = i % 2 == 0
    api("PATCH", f"/endpoints/{EP}", {"flashboot": fb})
    got = api("GET", f"/endpoints/{EP}").get("flashboot")
    print(f"probe {i}: flashboot set {fb}, endpoint reports {got}; idle {GAP}s", flush=True)
    time.sleep(GAP)
    for kind in ("cold", "warm"):
        t0 = time.time()
        submitted = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
        j = call("/run", PAYLOAD)
        job_id = j.get("id")
        while j.get("status") not in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
            time.sleep(0.5)
            j = call(f"/status/{job_id}")
        row = {"probe": i, "kind": kind, "flashboot": fb, "flashboot_reported": got, "gap_s": GAP if kind == "cold" else 0,
               "job_id": job_id, "submitted_utc": submitted, "wall_s": round(time.time() - t0, 2),
               "delayTime_ms": j.get("delayTime"), "executionTime_ms": j.get("executionTime"),
               "workerId": j.get("workerId"), "status": j.get("status")}
        rows.append(row)
        print(json.dumps(row), flush=True)
    json.dump(rows, open(OUT, "w"), indent=2)
print("-> " + OUT)
