"""Probe worker for labs 06-08: sleeps, fails or streams on request, reports where it ran.

실습 06-08 용 프로브 워커: 요청에 따라 대기·실패·스트리밍하고, 어디서 돌았는지 보고한다.

Input (all optional):
    {"mode": "sleep", "seconds": 1.0}    sleep, then return timing        (06, 08)
    {"mode": "fail"}                     raise -> job FAILED              (08)
    {"mode": "error_output"}             return {"error": ...}            (08)
    {"mode": "stream", "chunks": 10, "every": 0.2}   generator only       (07)

Environment:
    CONCURRENCY   jobs one worker takes at once (concurrency_modifier), default 1   (06)
    HANDLER_KIND  "plain" (async function, default) or "stream" (async generator) (07)
"""
import asyncio
import os
import socket
import time

import runpod

STARTED = time.time()
CONCURRENCY = int(os.getenv("CONCURRENCY", "1"))
WORKER = os.getenv("RUNPOD_POD_ID", socket.gethostname())
running = 0


def info(extra: dict) -> dict:
    return {"worker_id": WORKER, "worker_uptime_s": round(time.time() - STARTED, 2),
            "concurrency": CONCURRENCY, **extra}


async def plain(job):
    global running
    inp = job.get("input") or {}
    mode = inp.get("mode", "sleep")
    if mode == "fail":
        raise RuntimeError("asked to fail")
    if mode == "error_output":
        return {"error": "reported in the output, not raised"}
    running += 1
    at_start = running
    t0 = time.time()
    try:
        await asyncio.sleep(float(inp.get("seconds", 1.0)))
    finally:
        running -= 1
    return info({"started_at": round(t0, 3), "slept_s": round(time.time() - t0, 3), "tag": inp.get("tag"),
                 "running_at_start": at_start})


async def stream(job):
    inp = job.get("input") or {}
    t0 = time.time()
    for i in range(int(inp.get("chunks", 10))):
        await asyncio.sleep(float(inp.get("every", 0.2)))
        yield {"i": i, "t": round(time.time() - t0, 3), "worker_id": WORKER}


if os.getenv("HANDLER_KIND", "plain") == "stream":
    runpod.serverless.start({"handler": stream, "return_aggregate_stream": True})
else:
    runpod.serverless.start({"handler": plain, "concurrency_modifier": lambda current: CONCURRENCY})
