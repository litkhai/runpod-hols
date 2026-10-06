#!/usr/bin/env python3
"""Run the sweep for one GPU label on a fresh Pod, fetch the results, and terminate the Pod.

Usage:
    python3 pod_sweep.py --label RTX_4090 --gpu "NVIDIA GeForce RTX 4090" [--cloud SECURE] [--dry-run]
    python3 pod_sweep.py --ledger        # what has been spent so far

The Pod is terminated in a finally block: on success, failure, timeout or Ctrl-C.
Every Pod is appended to results/ledger.json with its rate and billed time, and a launch
is refused when the ledger plus this run's ceiling would exceed BUDGET_USD.

Env: RUNPOD_API_KEY (or the repo's .env), BUDGET_USD (default 40), SSH_KEY (default ~/.ssh/id_ed25519)
"""
import argparse, json, os, shlex, subprocess, sys, time, urllib.error, urllib.request

LAB = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(LAB))
RESULTS = os.path.join(LAB, "results")
LEDGER = os.path.join(RESULTS, "ledger.json")
PRICES = os.path.join(RESULTS, "prices.json")
API = "https://rest.runpod.io/v1"
# The PyTorch template image already used by pod/01-launch-connect. vLLM brings its own torch.
IMAGE = "runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404"
# vLLM 0.31.0 pins torch 2.13.0 with CUDA 13 dependencies, so the host driver must support CUDA 13.
CUDA = ["13.0"]
UPLOAD = ["run_sweep.sh", "capture_host.sh", "sample_gpu.sh", "use_cases.json", "pod_bootstrap.sh"]


def load_env():
    p = os.path.join(REPO, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def api(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + os.environ["RUNPOD_API_KEY"],
                                          "Content-Type": "application/json",
                 # Cloudflare in front of the API rejects the default Python-urllib agent (error 1010).
                 "User-Agent": "runpod-hols-inference-characterization/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError("%s %s -> %s %s" % (method, path, e.code, e.read().decode()[:500]))


def jload(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def jsave(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), indent=2)


def locked_update(path, default, fn):
    """Read-modify-write under an flock, so parallel runs do not drop each other's rows."""
    import fcntl
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        obj = fn(jload(path, default))
        jsave(path, obj)
        return obj


def spent():
    return sum(x.get("usd", 0) for x in jload(LEDGER, []))


LOG_PATH = None  # set to results/<label>/orchestrator.log once the label is known


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    if LOG_PATH:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label")
    ap.add_argument("--gpu", help="Runpod GPU type id, e.g. 'NVIDIA GeForce RTX 4090'")
    ap.add_argument("--cloud", default="SECURE", choices=["SECURE", "COMMUNITY"])
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--vllm", default="0.31.0")
    ap.add_argument("--max-model-len", default="8192")
    ap.add_argument("--cases", default="", help="space-separated use cases; default all in use_cases.json")
    ap.add_argument("--rates", default="", help="space-separated request rates overriding use_cases.json")
    ap.add_argument("--max-hours", type=float, default=2.0, help="terminate after this long regardless")
    ap.add_argument("--retry-min", type=float, default=10, help="keep retrying a create that finds no capacity")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ledger", action="store_true")
    a = ap.parse_args()

    load_env()
    budget = float(os.environ.get("BUDGET_USD", "40"))
    if a.ledger:
        for x in jload(LEDGER, []):
            print(json.dumps(x))
        print("spent %.2f of %.2f USD" % (spent(), budget))
        return 0
    if not (a.label and a.gpu):
        ap.error("--label and --gpu are required")

    key = os.path.expanduser(os.environ.get("SSH_KEY", "~/.ssh/id_ed25519"))
    body = {"name": "ic-" + a.label.lower().replace("_", "-"), "imageName": IMAGE, "computeType": "GPU",
            "gpuTypeIds": [a.gpu], "gpuCount": 1, "cloudType": a.cloud, "allowedCudaVersions": CUDA,
            "containerDiskInGb": 80, "volumeInGb": 0, "ports": ["22/tcp"],
            "env": {"PUBLIC_KEY": open(key + ".pub").read().strip()}}
    if a.cloud == "COMMUNITY":
        body["supportPublicIp"] = True
    print(json.dumps({k: v for k, v in body.items() if k != "env"}, indent=2))
    if a.dry_run:
        print("--dry-run: nothing created. spent so far %.2f of %.2f USD" % (spent(), budget))
        return 0

    global LOG_PATH
    os.makedirs(os.path.join(RESULTS, a.label), exist_ok=True)
    LOG_PATH = os.path.join(RESULTS, a.label, "orchestrator.log")
    pod_id, started, rate, status = None, None, None, "not-created"
    try:
        deadline = time.time() + a.retry_min * 60
        while True:
            try:
                pod = api("POST", "/pods", body)
                break
            except RuntimeError as e:
                # A failed create bills nothing; stock flips between Low and none from minute to minute.
                if "no instances currently available" not in str(e) or time.time() > deadline:
                    status = "no-capacity" if "no instances" in str(e) else "create-failed"
                    raise
                log("no capacity for %s (%s), retrying in 60s" % (a.gpu, a.cloud))
                time.sleep(60)
        pod_id, started = pod["id"], time.time()
        rate = pod.get("adjustedCostPerHr") or pod.get("costPerHr")
        log("created %s at %s USD/h on machine %s" % (pod_id, rate, (pod.get("machine") or {}).get("dataCenterId", "?")))
        if rate and spent() + rate * a.max_hours > budget:
            status = "refused-budget"
            raise RuntimeError("ledger %.2f + %.2f/h x %.1fh exceeds budget %.2f" % (spent(), rate, a.max_hours, budget))
        locked_update(PRICES, {}, lambda p: dict(p, **{a.label: rate}))

        ip = port = None
        while time.time() - started < 900:
            p = api("GET", "/pods/" + pod_id)
            ip, port = p.get("publicIp"), (p.get("portMappings") or {}).get("22")
            if ip and port:
                break
            time.sleep(10)
        if not (ip and port):
            status = "no-ssh"
            raise RuntimeError("no public IP / port 22 mapping after 15 min")
        ssh = ["ssh", "-i", key, "-p", str(port), "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
               "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30", "-o", "LogLevel=ERROR", "root@" + ip]
        scp_base = ["scp", "-i", key, "-P", str(port), "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR"]
        for _ in range(30):
            if subprocess.run(ssh + ["true"], capture_output=True).returncode == 0:
                break
            time.sleep(10)
        else:
            status = "no-ssh"
            raise RuntimeError("ssh never accepted the key")
        log("ssh ok root@%s -p %s" % (ip, port))

        subprocess.run(ssh + ["mkdir -p /root/lab"], check=True)
        subprocess.run(scp_base + [os.path.join(LAB, f) for f in UPLOAD] + ["root@%s:/root/lab/" % ip], check=True)
        envs = "GPU_LABEL=%s MODEL=%s VLLM_VERSION=%s MAX_MODEL_LEN=%s CASES=%s RATES=%s" % tuple(
            shlex.quote(x) for x in (a.label, a.model, a.vllm, a.max_model_len, a.cases, a.rates))
        # The subshell detaches the whole command; backgrounding an && list would keep ssh's stdout
        # open in the list's subshell and block this call until the sweep finished.
        subprocess.run(ssh + ["cd /root/lab && chmod +x *.sh && (%s setsid nohup ./pod_bootstrap.sh > bootstrap.log 2>&1 < /dev/null &)" % envs],
                       check=True, timeout=120)
        log("bootstrap started")

        seen = 0
        status = "timeout"
        while time.time() - started < a.max_hours * 3600:
            time.sleep(30)
            r = subprocess.run(ssh + ["cd /root/lab; tail -n +%d bootstrap.log; echo __STATE__; ls DONE FAILED 2>/dev/null; exit 0" % (seen + 1)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                log("ssh poll failed, retrying")
                continue
            out, _, state = r.stdout.partition("__STATE__\n")
            for line in out.splitlines():
                if line.startswith(("==", "===", "FAILED", "ready", "vllm ", "all flags")) or "KV cache" in line or "concurrency" in line:
                    log("  " + line)
            seen += len(out.splitlines())
            if "DONE" in state:
                status = "done"
                break
            if "FAILED" in state:
                status = "failed"
                break

        # Fetch before the finally block terminates the Pod; the container disk goes with it.
        local = os.path.join(RESULTS, a.label)
        remote_n = subprocess.run(ssh + ["ls /root/lab/results/%s 2>/dev/null | wc -l; exit 0" % a.label],
                                  capture_output=True, text=True).stdout.strip() or "0"
        for i in range(3):
            subprocess.run(scp_base + ["-r", "root@%s:/root/lab/results/%s" % (ip, a.label), RESULTS + "/"])
            subprocess.run(scp_base + ["root@%s:/root/lab/bootstrap.log" % ip, os.path.join(local, "bootstrap.log")])
            # orchestrator.log and bootstrap.log exist only locally
            got = len([f for f in os.listdir(local) if f not in ("orchestrator.log", "bootstrap.log")])
            if got >= int(remote_n):
                break
            log("fetch got %d of %s files, retry %d" % (got, remote_n, i + 1))
            time.sleep(10)
        host = os.path.join(local, "host.json")
        if not (os.path.exists(host) and os.path.getsize(host) > 50):
            log("WARNING: host.json missing or empty")
        log("fetched results -> %s (status %s)" % (os.path.join(RESULTS, a.label), status))
    finally:
        if pod_id:
            for i in range(5):
                try:
                    api("DELETE", "/pods/" + pod_id)
                    log("terminated %s" % pod_id)
                    break
                except Exception as e:  # keep trying: an orphaned Pod bills until someone notices
                    log("terminate failed (%s), retry %d" % (e, i + 1))
                    time.sleep(10)
            hours = (time.time() - started) / 3600
            row = {"label": a.label, "gpu": a.gpu, "cloud": a.cloud, "pod_id": pod_id, "usd_per_hr": rate,
                   "hours": round(hours, 3), "usd": round(hours * (rate or 0), 3), "status": status,
                   "ended": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            locked_update(LEDGER, [], lambda rows: rows + [row])
            log("ledger: %.2f of %.2f USD" % (spent(), budget))
    return 0 if status == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
