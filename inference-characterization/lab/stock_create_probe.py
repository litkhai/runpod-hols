#!/usr/bin/env python3
"""T11: does a `Low` stockStatus reading predict a successful one-GPU Secure Pod create?

Each round reads stockStatus for every tracked GPU type (one GPU, Secure, CUDA 13 floor and any CUDA),
then tries one create on a type that reads `Low` and one on a type that reads no stock (the control),
and deletes any Pod it made at once. Rounds are ROUNDS (default 10), SLEEP_S apart (default 60).
Output: results/stock_create_probe.jsonl, one line per attempt: reading, HTTP result, pod id, seconds billed.
Spend: a created Pod lives for the seconds between create and delete, plus container disk.
Env: RUNPOD_API_KEY (or the repo's .env), ROUNDS, SLEEP_S, LOW_TYPES / NONE_TYPES (comma lists to pin the types).
"""
import json, os, sys, time, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pod_sweep import RESULTS, api, load_env  # noqa: E402

load_env()
OUT = os.path.join(RESULTS, "stock_create_probe.jsonl")
ROUNDS = int(os.environ.get("ROUNDS", "10"))
SLEEP = int(os.environ.get("SLEEP_S", "60"))
KEEP = ("H100", "H200", "A100", "L40", "4090", "L4", "B200")
IMAGE = "runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404"
Q = ('{ gpuTypes { id cuda13: lowestPrice(input:{gpuCount:1, secureCloud:true, minCudaVersion:"13.0"}) { stockStatus } '
     'any: lowestPrice(input:{gpuCount:1, secureCloud:true}) { stockStatus } } }')


def stock():
    req = urllib.request.Request("https://api.runpod.io/graphql", data=json.dumps({"query": Q}).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["RUNPOD_API_KEY"],
                                          "Content-Type": "application/json",
                                          "User-Agent": "runpod-hols-inference-characterization/1.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return {g["id"]: [(g["cuda13"] or {}).get("stockStatus"), (g["any"] or {}).get("stockStatus")]
            for g in d["data"]["gpuTypes"] if any(k in g["id"] for k in KEEP)}


def attempt(gpu, reading, rnd):
    body = {"name": "ic-stockprobe", "imageName": IMAGE, "computeType": "GPU", "gpuTypeIds": [gpu], "gpuCount": 1,
            "cloudType": "SECURE", "allowedCudaVersions": ["13.0"], "containerDiskInGb": 20, "volumeInGb": 0}
    row = {"round": rnd, "t_kst": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "gpu": gpu, "reading_[cuda13,any]": reading}
    t0 = time.time()
    try:
        pod = api("POST", "/pods", body)
        row.update(created=True, pod_id=pod.get("id"), datacenter=pod.get("dataCenterId") or pod.get("datacenter"),
                   cost_per_hr=pod.get("costPerHr"), machine_id=pod.get("machineId"))
        try:
            api("DELETE", "/pods/" + pod["id"])
            row["deleted"] = True
        except Exception as e:  # keep the id so it can be removed by hand
            row["deleted"] = False
            row["delete_error"] = str(e)[:300]
        row["seconds_alive"] = round(time.time() - t0, 1)
    except Exception as e:
        row.update(created=False, error=str(e)[:300])
    print(json.dumps(row), flush=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def pick(rows, status):
    pinned = os.environ.get("LOW_TYPES" if status == "Low" else "NONE_TYPES")
    cands = [g for g, (c13, _) in sorted(rows.items()) if (c13 == status if status else c13 is None)]
    if pinned:
        cands = [g for g in pinned.split(",") if g in cands]
    return cands


for rnd in range(ROUNDS):
    rows = stock()
    low, none = pick(rows, "Low"), pick(rows, None)
    print(json.dumps({"round": rnd, "low": low, "none": none}), flush=True)
    if low:
        attempt(low[rnd % len(low)], rows[low[rnd % len(low)]], rnd)
    if none:
        attempt(none[rnd % len(none)], rows[none[rnd % len(none)]], rnd)
    if rnd < ROUNDS - 1:
        time.sleep(SLEEP)
print("-> " + OUT)
