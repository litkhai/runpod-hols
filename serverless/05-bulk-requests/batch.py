#!/usr/bin/env python3
"""Submit a batch (Bulk Requests) to a queue endpoint, poll it, and save every result.

큐 엔드포인트에 배치(Bulk Requests)를 제출하고, 상태를 확인하고, 모든 결과를 저장한다.

    python3 batch.py submit <endpoint_id> [--n 30]      # create + finalize, prints the batch id
    python3 batch.py poll <endpoint_id> <batch_id>      # one status line
    python3 batch.py wait <endpoint_id> <batch_id> [--every 300] [--hours 26]
    python3 batch.py results <endpoint_id> <batch_id> --out results/batch.json

API: POST/GET https://api.runpod.ai/v2/<endpoint>/batch[...] (docs.runpod.io/serverless/batch-jobs,
read 2026-11-07). Batches run on dedicated workers within 24 h, best effort.
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

ROOT = pathlib.Path(__file__).resolve().parents[2]


def key() -> str:
    if os.environ.get("RUNPOD_API_KEY"):
        return os.environ["RUNPOD_API_KEY"]
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("RUNPOD_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit("RUNPOD_API_KEY is not set")


def call(method: str, path: str, body=None):
    req = urllib.request.Request("https://api.runpod.ai/v2" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json",
                                          "User-Agent": "runpod-hols-serverless-05/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            t = r.read()
            return json.loads(t) if t.strip() else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code} {e.read().decode()[:400]}")


def line(ep: str, bid: str) -> dict:
    s = call("GET", f"/{ep}/batch/{bid}")
    s["polled_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["submit", "poll", "wait", "results"])
    ap.add_argument("endpoint")
    ap.add_argument("batch", nargs="?")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--every", type=int, default=300)
    ap.add_argument("--hours", type=float, default=26)
    ap.add_argument("--out", default="results/batch.json")
    a = ap.parse_args()
    if a.action == "submit":
        b = call("POST", f"/{a.endpoint}/batch", [{"input": {"name": f"batch-{i}"}} for i in range(a.n)])
        print(json.dumps(b))
        f = call("POST", f"/{a.endpoint}/batch/{b['id']}/finalize")
        print(json.dumps(f))
        print("BATCH_ID=" + b["id"])
    elif a.action == "poll":
        print(json.dumps(line(a.endpoint, a.batch)))
    elif a.action == "wait":
        end = time.time() + a.hours * 3600
        while time.time() < end:
            s = line(a.endpoint, a.batch)
            print(json.dumps(s), flush=True)
            if s.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                break
            time.sleep(a.every)
    else:
        rows, off = [], 0
        while True:
            r = call("GET", f"/{a.endpoint}/batch/{a.batch}/requests?offset={off}&limit=50")
            items = r.get("requests") or r.get("items") or []
            rows += items
            if not r.get("hasMore") or not items:
                break
            off += len(items)
        out = {"batch": line(a.endpoint, a.batch), "requests": rows}
        pathlib.Path(a.out).parent.mkdir(exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
        print(f"{len(rows)} requests -> {a.out}")


if __name__ == "__main__":
    main()
