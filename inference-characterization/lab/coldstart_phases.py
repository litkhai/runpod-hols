#!/usr/bin/env python3
"""Split each Serverless cold start into phases from the worker logs that capture_worker_logs.sh saved.

Usage: python3 coldstart_phases.py <probe.json> <log_dir> [out.json]

Each cold row in <probe.json> (written by coldstart_probe.py) is matched to the container session
that served it: same workerId, sessions taken in order. Inside that session the log markers give

    container_create    system   "create container"
    vllm_start          worker   "Starting vLLM"
    weights_download_s  vLLM     "Time spent downloading weights ...: X seconds"
    compile_s           vLLM     "torch.compile took X s"
    graph_capture_s     vLLM     "Graph capturing finished in X secs" (summed over the session)
    engine_ready        vLLM     "Application startup complete"
    fitness_done        worker   "All fitness checks passed"
    job_pickup          worker   "Jobs in progress: 1"

and `delayTime - (job_pickup - container_create)` is the time before a container existed: queueing,
host selection, attempts on other workers, image load. The markers are the strings logged by
runpod/worker-v1-vllm v2.28.0 and vLLM 0.30.0 in this run; another version may word them differently,
and a phase whose marker is missing is reported as null.
Other workers' image loads ("loading container image from cache" -> "Loaded image") are listed too.
"""
import glob, json, os, re, sys
from datetime import datetime, timedelta


def ts(s):
    s = s.rstrip("Z")
    if "." in s:
        head, frac = s.split(".", 1)
        s = head + "." + frac[:6]
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def sessions(rows):
    """Split one worker's log into container sessions at each system 'create container'."""
    out, cur = [], None
    for r in rows:
        if r.get("source") == "system" and r.get("line", "").startswith("create container"):
            cur = []
            out.append(cur)
        if cur is not None:
            cur.append(r)
    return out


def first(rows, pred):
    for r in rows:
        if pred(r):
            return r
    return None


def num(rows, pattern):
    rx = re.compile(pattern)
    for r in rows:
        m = rx.search(r.get("line", ""))
        if m:
            return float(m.group(1))
    return None


def total(rows, pattern):
    rx = re.compile(pattern)
    vals = [float(m.group(1)) for r in rows for m in [rx.search(r.get("line", ""))] if m]
    return round(sum(vals), 2) if vals else None


def secs(a, b):
    return round((ts(b["ts"]) - ts(a["ts"])).total_seconds(), 1) if a and b else None


def phases(sess):
    line = lambda s: (lambda r: s in r.get("line", ""))
    create = sess[0]
    m = {
        "container_create": create,
        "vllm_start": first(sess, line("Starting vLLM")),
        "engine_ready": first(sess, line("Application startup complete")),
        "fitness_done": first(sess, line("All fitness checks passed")),
        "job_pickup": first(sess, line("Jobs in progress: 1")),
    }
    return {
        "container_create_utc": create["ts"],
        "container_to_vllm_start_s": secs(m["container_create"], m["vllm_start"]),
        "vllm_start_to_engine_ready_s": secs(m["vllm_start"], m["engine_ready"]),
        "weights_download_s": num(sess, r"Time spent downloading weights .*?: ([0-9.]+) seconds"),
        "weights_load_s": num(sess, r"Loading weights took ([0-9.]+) seconds"),
        "compile_s": num(sess, r"torch\.compile took ([0-9.]+) s"),
        # vLLM captures graphs more than once per start (two lines in this run); sum them
        "graph_capture_s": total(sess, r"Graph capturing finished in ([0-9.]+) secs"),
        "engine_init_s": num(sess, r"init engine .* took ([0-9.]+) s"),
        "engine_ready_to_fitness_done_s": secs(m["engine_ready"], m["fitness_done"]),
        "fitness_checks_s": (num(sess, r"All fitness checks passed\. \(([0-9.]+)ms\)") or 0) / 1000 or None,
        "fitness_done_to_job_pickup_s": secs(m["fitness_done"], m["job_pickup"]),
        "container_create_to_job_pickup_s": secs(m["container_create"], m["job_pickup"]),
        "has_container_log": m["vllm_start"] is not None,
    }


def main():
    probe_path, log_dir = sys.argv[1], sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(probe_path)[0] + "_phases.json"
    probes = json.load(open(probe_path))
    logs = {}
    for p in glob.glob(os.path.join(log_dir, "*.jsonl")):
        wid = os.path.basename(p).split(".")[0]
        rows = logs.setdefault(wid, {})
        for r in load(p):  # merge <id>.jsonl and <id>.early.jsonl
            rows[(r.get("ts"), r.get("source"), r.get("line"))] = r
    logs = {w: sorted(v.values(), key=lambda r: r.get("ts") or "") for w, v in logs.items()}

    image_loads = []
    for w, rows in logs.items():
        a = first(rows, lambda r: "loading container image from cache" in r.get("line", ""))
        b = first(rows, lambda r: r.get("line", "").startswith("Loaded image"))
        if a and b:
            image_loads.append({"workerId": w, "start_utc": a["ts"], "seconds": secs(a, b)})

    used = {}
    result = []
    for row in probes:
        if row.get("kind") != "cold":
            continue
        w = row.get("workerId")
        sess = sessions(logs.get(w, []))
        k = used.get(w, 0)
        # a session that served a job; skip sessions with no pickup
        served = [s for s in sess if first(s, lambda r: "Jobs in progress" in r.get("line", ""))]
        # A session cut off before pickup (logs saved too late, or the endpoint deleted) still yields
        # the phases it covers; take sessions in order once the served ones are used up.
        delay_s = round((row.get("delayTime_ms") or 0) / 1000, 1)
        reused = None
        if row.get("submitted_utc"):
            # Rows that carry the submit time are matched to the session whose container was created
            # between the request and its pickup. No such session: a container that already existed
            # served the request, i.e. no cold start happened (seen with 15 s and 30 s idle gaps).
            t0 = ts(row["submitted_utc"]) - timedelta(seconds=2)
            t1 = ts(row["submitted_utc"]) + timedelta(seconds=delay_s + 5)
            hits = [x for x in sess if t0 <= ts(x[0]["ts"]) <= t1]
            if hits:
                ph = phases(hits[0])
            else:
                ph = None
                prev = [x for x in sess if ts(x[0]["ts"]) < t0]
                reused = prev[-1][0]["ts"] if prev else None
        else:
            ph = phases(served[k]) if k < len(served) else (phases(sess[k]) if k < len(sess) else None)
            used[w] = k + 1
        rec = {"probe": row.get("probe"), "workerId": w, "delay_s": delay_s, "execution_s": round((row.get("executionTime_ms") or 0) / 1000, 2)}
        if ph:
            rec.update(ph)
            inside = ph["container_create_to_job_pickup_s"]
            rec["before_container_s"] = round(delay_s - inside, 1) if inside is not None else None
            if inside is None:
                rec["note"] = "container session captured only in part (no job pickup in the saved logs)"
        elif reused:
            rec["served_by_container_created_utc"] = reused
            rec["note"] = "served by a container created before the request: no cold start"
        else:
            rec["note"] = "no container session in the saved logs for this worker"
        result.append(rec)

    json.dump({"cold_starts": result, "image_loads_from_cache": image_loads}, open(out_path, "w"), indent=2)
    for r in result:
        print(json.dumps({k: r.get(k) for k in ("probe", "workerId", "delay_s", "before_container_s", "container_to_vllm_start_s",
                                                "vllm_start_to_engine_ready_s", "weights_download_s", "compile_s", "graph_capture_s",
                                                "engine_ready_to_fitness_done_s", "fitness_done_to_job_pickup_s", "note")}))
    for x in image_loads:
        print("image load from cache:", json.dumps(x))
    print("->", out_path)


if __name__ == "__main__":
    main()
