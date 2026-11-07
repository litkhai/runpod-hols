#!/usr/bin/env python3
"""Measure when streamed chunks reach the client through /stream, against when the worker made them.

/stream 으로 받은 청크가 워커에서 만들어진 시각과 클라이언트에 도착한 시각을 비교한다.

    python3 stream.py <endpoint_id> --chunks 20 --every 0.5 --runs 3 --out results/stream.json

Needs the probe worker from ../06-autoscaling with HANDLER_KIND=stream: each chunk
carries `t`, seconds since the handler started. For every run this records the
/run submit time, each /stream poll (wall time and the chunks it returned), the
final /status (with return_aggregate_stream the output is the list of all chunks),
and a /runsync of the same input for comparison.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "06-autoscaling"))
from burst import call  # noqa: E402


def one(base: str, inp: dict) -> dict:
    t0 = time.time()
    job = call(base + "/run", {"input": inp})
    polls, chunks, status = [], [], None
    while time.time() - t0 < 300:
        r = call(f"{base}/stream/{job['id']}", timeout=120)
        now = round(time.time() - t0, 3)
        got = [c.get("output") for c in (r.get("stream") or [])]
        polls.append({"t": now, "status": r.get("status"), "n": len(got)})
        for c in got:
            chunks.append({"arrived": now, **(c or {})})
        status = r.get("status")
        if status in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
            break
    final = call(f"{base}/status/{job['id']}")
    return {"id": job.get("id"), "polls": polls, "chunks": chunks, "final_status": final.get("status"),
            "delayTime_ms": final.get("delayTime"), "executionTime_ms": final.get("executionTime"),
            "final_output_len": len(final.get("output") or []) if isinstance(final.get("output"), list) else final.get("output")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint")
    ap.add_argument("--chunks", type=int, default=20)
    ap.add_argument("--every", type=float, default=0.5)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default="results/stream.json")
    a = ap.parse_args()
    base = f"https://api.runpod.ai/v2/{a.endpoint}"
    inp = {"mode": "stream", "chunks": a.chunks, "every": a.every}
    runs = []
    for i in range(a.runs):
        r = one(base, inp)
        first = r["chunks"][0] if r["chunks"] else {}
        print(f"run {i}: {len(r['chunks'])} chunks over {len(r['polls'])} polls, first arrived {first.get('arrived')} s "
              f"(made at handler t={first.get('t')}), delay {r['delayTime_ms']} ms, final {r['final_status']}", flush=True)
        runs.append(r)
    s = time.time()
    sync = call(base + "/runsync", {"input": inp}, timeout=300)
    sync_out = {"wall_s": round(time.time() - s, 2), "status": sync.get("status"),
                "output_len": len(sync.get("output") or []) if isinstance(sync.get("output"), list) else sync.get("output")}
    print("runsync:", sync_out, flush=True)
    pathlib.Path(a.out).parent.mkdir(exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps({"input": inp, "runs": runs, "runsync": sync_out}, indent=1) + "\n")


if __name__ == "__main__":
    main()
