#!/usr/bin/env python3
"""Probe Runpod Serverless cold vs warm starts and record what the platform returns.

Env: RUNPOD_API_KEY, ENDPOINT_ID, N (probe pairs, default 5), GAP_S (idle gap so workers scale to zero, default 600)
Usage: python3 coldstart_probe.py [payload.json]
Each probe sends one request after an idle gap (cold) and one immediately after (warm).
Output: $OUT (default results/coldstart.json next to this script) with wall time,
delayTime, executionTime, workerId per request. "cold" is the request after the idle gap;
a cold row whose workerId equals the previous warm row's was served by a worker that never scaled down.
"""
import json, os, sys, time, urllib.request

API = os.environ["RUNPOD_API_KEY"]
EP = os.environ["ENDPOINT_ID"]
BASE = f"https://api.runpod.ai/v2/{EP}"
N = int(os.environ.get("N", "5"))
GAP = int(os.environ.get("GAP_S", "600"))
OUT = os.environ.get("OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "coldstart.json")
payload = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {
    "input": {"prompt": "Say hello in one sentence.", "sampling_params": {"max_tokens": 32}}
}


def call(path, data=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": f"Bearer {API}", "Content-Type": "application/json",
                 # Cloudflare in front of the API rejects the default Python-urllib agent (error 1010).
                 "User-Agent": "runpod-hols-inference-characterization/1.0"},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.load(resp)


rows = []
for i in range(N):
    for kind in ("cold", "warm"):
        t0 = time.time()
        submitted = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
        j = call("/run", payload)
        job_id = j.get("id")
        while j.get("status") not in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
            time.sleep(0.5)
            j = call(f"/status/{j['id']}")
        row = {"probe": i, "kind": kind, "job_id": job_id, "submitted_utc": submitted, "wall_s": round(time.time() - t0, 2),
               "delayTime_ms": j.get("delayTime"), "executionTime_ms": j.get("executionTime"),
               "workerId": j.get("workerId"), "status": j.get("status")}
        rows.append(row)
        print(json.dumps(row), flush=True)
    # Write after every pair so an interrupted run keeps what it measured.
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=2)
    if i < N - 1:
        time.sleep(GAP)
print("-> " + OUT)
