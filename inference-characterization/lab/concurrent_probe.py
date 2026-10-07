#!/usr/bin/env python3
"""T7: with more than one worker allowed, can the job response alone tell a cold request from a warm one?

Sends BURST requests at once to a scaled-to-zero endpoint (wave "cold"), waits for all of them, then sends
BURST again at once (wave "warm"), and records delayTime, executionTime and workerId per job, plus the
worker list (GET /v2/serverless/{id}/workers) after each wave.
Env: RUNPOD_API_KEY, ENDPOINT_ID, BURST (default 5), WAVES (default "cold,warm"), OUT.
"""
import json, os, sys, threading, time, urllib.request

API = os.environ["RUNPOD_API_KEY"]
EP = os.environ["ENDPOINT_ID"]
BASE = f"https://api.runpod.ai/v2/{EP}"
BURST = int(os.environ.get("BURST", "5"))
WAVES = os.environ.get("WAVES", "cold,warm").split(",")
OUT = os.environ.get("OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "concurrent.json")
payload = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {
    "input": {"prompt": "Say hello in one sentence.", "sampling_params": {"max_tokens": 32}}}
H = {"Authorization": f"Bearer {API}", "Content-Type": "application/json",
     "User-Agent": "runpod-hols-inference-characterization/1.0"}


def call(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=H,
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.load(resp)


def one(wave, i, rows):
    t0 = time.time()
    submitted = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    j = call(BASE + "/run", payload)
    while j.get("status") not in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
        time.sleep(0.5)
        j = call(f"{BASE}/status/{j['id']}")
    rows.append({"wave": wave, "i": i, "job_id": j.get("id"), "submitted_utc": submitted,
                 "wall_s": round(time.time() - t0, 2), "delayTime_ms": j.get("delayTime"),
                 "executionTime_ms": j.get("executionTime"), "workerId": j.get("workerId"), "status": j.get("status")})


out = {"endpoint": EP, "burst": BURST, "waves": []}
for wave in WAVES:
    rows = []
    threads = [threading.Thread(target=one, args=(wave, i, rows)) for i in range(BURST)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    rows.sort(key=lambda r: r["i"])
    workers = call(f"https://api.runpod.io/v2/serverless/{EP}/workers")
    out["waves"].append({"wave": wave, "jobs": rows,
                         "workers_after": [{k: w.get(k) for k in ("id", "status", "gpuTypeId", "dataCenterId", "startedAt")}
                                           for w in workers.get("workers", [])]})
    for r in rows:
        print(json.dumps(r), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2)
print("-> " + OUT)
