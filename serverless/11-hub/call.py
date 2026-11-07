#!/usr/bin/env python3
"""Send the Hub listing's sample request to a Faster Whisper endpoint and record the timing.

Hub 목록의 예제 요청을 Faster Whisper 엔드포인트에 보내고 시간을 기록한다.

    python3 call.py <endpoint_id> --label cold_turbo --model turbo --out results/calls.jsonl
"""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "06-autoscaling"))
from burst import call  # noqa: E402

AUDIO = "https://github.com/runpod-workers/sample-inputs/raw/main/audio/gettysburg.wav"

ap = argparse.ArgumentParser()
ap.add_argument("endpoint")
ap.add_argument("--label", required=True)
ap.add_argument("--model", default="turbo")
ap.add_argument("--transcription", default="plain_text")
ap.add_argument("--out", default="results/calls.jsonl")
a = ap.parse_args()
base = f"https://api.runpod.ai/v2/{a.endpoint}"
t0 = time.time()
job = call(base + "/run", {"input": {"audio": AUDIO, "model": a.model, "transcription": a.transcription}})
while True:
    r = call(f"{base}/status/{job['id']}")
    if r.get("status") in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT") or time.time() - t0 > 900:
        break
    time.sleep(2)
o = r.get("output") or {}
rec = {"label": a.label, "model": a.model, "transcription_arg": a.transcription, "at": time.strftime("%H:%M:%S"),
       "wall_s": round(time.time() - t0, 1), "status": r.get("status"), "delayTime_ms": r.get("delayTime"),
       "executionTime_ms": r.get("executionTime"), "workerId": r.get("workerId"),
       "device": o.get("device") if isinstance(o, dict) else None,
       "transcription": (o.get("transcription") or "")[:120] if isinstance(o, dict) else str(o)[:200],
       "error": str(r.get("error"))[:300] if r.get("error") else None}
print(json.dumps(rec, ensure_ascii=False), flush=True)
with open(a.out, "a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
