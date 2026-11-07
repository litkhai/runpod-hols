#!/usr/bin/env python3
"""Stage 2: an Instant Cluster (2 nodes x 8 GPUs) over GraphQL — wait for stock, create, run, fetch, delete.

2단계: GraphQL 로 Instant Cluster (노드 2 x GPU 8) — 재고 대기, 생성, 실행, 회수, 삭제.

    python3 cluster.py stock                 # stockStatus of the cluster type
    python3 cluster.py auto --hours 48       # wait for stock, then everything below, unattended
    python3 cluster.py create | show | push | run <tag> | pull | delete

The console is not needed: the GraphQL API has createCluster / deleteCluster
(found 2026-11-07; introspection is off, the input fields were read from
validation errors). `auto` starts a separate watchdog that deletes the cluster
--stop minutes after creation whatever happens to this process.
콘솔 없이 GraphQL 의 createCluster / deleteCluster 로 만든다. `auto` 는 생성 직후
별도 감시 프로세스를 띄워, 이 프로세스가 어떻게 되든 --stop 분 뒤 클러스터를 지운다.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

from common import LAB_DIR, api_key, load_state, rest, save_state

GPU = "NVIDIA A100-SXM4-80GB"
PODS, PER_POD = 2, 8
# The console's "for clusters" template image; the plain image has no libibverbs, so NCCL fell back
# to sockets on 2026-11-07. 콘솔의 "for clusters" 템플릿 이미지. 일반 이미지는 libibverbs 가 없어
# 2026-11-07 실행에서 NCCL 이 소켓으로 내려갔다.
IMAGE = "runpod/pytorch:1.0.7-cu1300-torch291-ubuntu2404-cluster"
REMOTE = "/workspace/dist"
FILES = ["run.sh", "nccl_bench.py", "ddp_train.py"]
MAX_PER_HR = 80.0  # the account's spend limit; A100 16 x 2.148 = 34.37, H100 16 x 4.788 = 76.61
# --gpus: the first type in stock wins; its short name goes into the results tag.
# --gpus: 먼저 재고가 나온 종류로 만들고, 결과 태그에 그 짧은 이름을 넣는다.
SHORT = {"NVIDIA A100-SXM4-80GB": "A100SXM", "NVIDIA H100 80GB HBM3": "H100SXM"}
# Runpod puts these in the container environment; an SSH session does not inherit them.
# Runpod 이 컨테이너 환경에 넣는 값. SSH 세션은 물려받지 않으므로 PID 1 에서 읽는다.
ENV_FROM_PID1 = (". /etc/rp_environment 2>/dev/null; eval \"$(tr '\\0' '\\n' < /proc/1/environ | grep -E "
                 "'^(NUM_NODES|NUM_TRAINERS|NODE_RANK|NODE_ADDR|PRIMARY_ADDR|PRIMARY_PORT|WORLD_SIZE)=' "
                 "| sed 's/^/export /')\"")


def log(*a) -> None:
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def gql(query: str, variables: dict | None = None) -> dict:
    req = urllib.request.Request(
        "https://api.runpod.io/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": "Bearer " + api_key(), "Content-Type": "application/json",
                 "User-Agent": "runpod-hols-cluster-dist/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    if d.get("errors"):
        raise RuntimeError(d["errors"][0].get("message", str(d["errors"]))[:300])
    return d["data"]


def stock() -> tuple:
    q = ("query($l: GpuLowestPriceInput, $g: GpuTypeFilter){ gpuTypes(input:$g){ clusterPrice "
         "lowestPrice(input:$l){ stockStatus } } }")
    v = {"g": {"id": GPU}, "l": {"gpuCount": PER_POD, "minDisk": 0, "minMemoryInGb": 8, "minVcpuCount": 2,
                                 "secureCloud": True, "compliance": [], "dataCenterId": "", "isCluster": True,
                                 "podCount": PODS, "throughput": 1600}}
    g = gql(q, v)["gpuTypes"][0]
    return (g["lowestPrice"] or {}).get("stockStatus"), g["clusterPrice"]


def clusters() -> list:
    return gql("{ myself { clusters { id name gpuTypeId podCount gpuCountPerPod createdAt pods { id } } } }")[
        "myself"]["clusters"]


def create() -> dict:
    st = load_state()
    if st.get("cluster_id"):
        sys.exit(f"cluster {st['cluster_id']} already recorded; delete it first")
    inp = {"clusterName": "hol-cluster-01", "gpuTypeId": GPU, "podCount": PODS, "gpuCountPerPod": PER_POD,
           "type": "TRAINING", "imageName": IMAGE, "containerDiskInGb": 50, "volumeInGb": 0,
           "ports": "22/tcp", "startSsh": True}
    q = "mutation($i: CreateClusterInput!){ createCluster(input:$i){ id name pods { id } } }"
    try:
        c = gql(q, {"i": inp})["createCluster"]
    except RuntimeError as e:
        # Without deployCost the API asks for price 0 and names the per-pod minimum; deployCost is
        # for the whole cluster (it is divided by podCount), so offer minimum x podCount.
        # deployCost 가 없으면 가격 0 으로 거절되고 오류에 노드당 최소 가격이 나온다. deployCost 는
        # 클러스터 전체 값 (podCount 로 나눠 비교) 이므로 최소 가격 x podCount 로 다시 요청한다.
        m = re.search(r"minimum price \(([\d.]+)\)", str(e))
        if not m or float(m.group(1)) * PODS > MAX_PER_HR:
            raise
        inp["deployCost"] = round(float(m.group(1)) * PODS, 2)
        log("retry with deployCost", inp["deployCost"])
        c = gql(q, {"i": inp})["createCluster"]
    st.update(cluster_id=c["id"], pod_ids=[p["id"] for p in c["pods"]], created=time.time())
    save_state(st)
    log("created cluster", c["id"], "pods", st["pod_ids"])
    return st


def delete() -> None:
    st = load_state()
    cid = st.get("cluster_id")
    ids = [cid] if cid else [c["id"] for c in clusters() if c["name"] == "hol-cluster-01"]
    for i in ids:
        try:
            gql("mutation($i: DeleteClusterInput!){ deleteCluster(input:$i) }", {"i": {"id": i}})
            log("deleted cluster", i)
        except Exception as e:  # already gone, or retry below
            log("delete", i, "->", e)
    left = [c["id"] for c in clusters()]
    log("clusters left:", left or "none")
    if not left:
        st.pop("cluster_id", None)
        st.pop("pod_ids", None)
        save_state(st)


def watchdog(minutes: int) -> None:
    # Detached: survives this process. Retries the delete until no cluster is left.
    # 분리된 프로세스: 이 프로세스가 죽어도 남는다. 클러스터가 없어질 때까지 삭제를 반복한다.
    cmd = (f"sleep {minutes * 60}; cd {LAB_DIR}; for i in 1 2 3 4 5 6; do python3 cluster.py delete; "
           f"python3 cluster.py list | grep -q '^none$' && break; sleep 60; done")
    p = subprocess.Popen(["bash", "-c", cmd], start_new_session=True, stdout=open(LAB_DIR / ".watchdog.log", "a"),
                         stderr=subprocess.STDOUT)
    log(f"watchdog pid {p.pid}: delete at +{minutes} min")


def pods() -> list:
    return [rest("GET", f"/pods/{i}") for i in load_state().get("pod_ids", [])]


def ssh_args(p: dict) -> list | None:
    ip, ports = p.get("publicIp"), p.get("portMappings") or {}
    if not ip or "22" not in ports:
        return None
    return ["-p", str(ports["22"]), "-i", str(pathlib.Path.home() / ".ssh/id_ed25519"), "-o",
            "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30",
            f"root@{ip}"]


def wait_ssh(timeout_s: int) -> list:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        ps = pods()
        ts = [ssh_args(p) for p in ps]
        if ts and all(ts) and all(subprocess.run(["ssh", *t, "true"], capture_output=True).returncode == 0
                                  for t in ts):
            log("ssh ready on", len(ts), "nodes after", round(time.time() - t0), "s;",
                ", ".join(f"{p['id']} ${p.get('costPerHr')}/hr" for p in ps))
            return ts
        time.sleep(20)
    raise RuntimeError(f"ssh not ready after {timeout_s} s")


def push(ts: list) -> None:
    for t in ts:
        subprocess.run(["ssh", *t, f"mkdir -p {REMOTE}"], check=True)
        subprocess.run(["scp", "-P", t[1], "-i", t[3], "-o", "StrictHostKeyChecking=accept-new",
                        *[str(LAB_DIR / f) for f in FILES], f"{t[-1]}:{REMOTE}/"], check=True)
    log("copied scripts to", len(ts), "nodes")


def run(ts: list, tag: str, timeout_s: int) -> list:
    out = LAB_DIR / "results" / tag
    out.mkdir(parents=True, exist_ok=True)
    procs = [subprocess.Popen(["ssh", *t, f"{ENV_FROM_PID1}; bash {REMOTE}/run.sh {tag}"],
                              stdout=open(out / f"ssh-node{i}.log", "w"), stderr=subprocess.STDOUT)
             for i, t in enumerate(ts)]
    t0 = time.time()
    while any(p.poll() is None for p in procs) and time.time() - t0 < timeout_s:
        time.sleep(10)
    for p in procs:
        if p.poll() is None:
            p.kill()
    codes = [p.returncode for p in procs]
    log("run.sh exit codes", codes, "after", round(time.time() - t0), "s")
    return codes


def pull(ts: list) -> None:
    dest = LAB_DIR / "results"
    for t in ts:
        r = subprocess.run(["ssh", *t, f"tar -C {REMOTE}/results -cf - ."], capture_output=True)
        if r.returncode == 0:
            subprocess.run(["tar", "-C", str(dest), "-xf", "-"], input=r.stdout, check=True)
    log("results ->", dest)


def auto(a) -> int:
    end = time.time() + a.hours * 3600
    global GPU
    while True:
        for GPU in a.gpus.split(","):
            s, price = stock()
            if s:
                break
        if s:
            log("stock", GPU, s, f"${price}/GPU-hr")
            if a.tag == "auto":
                a.tag = f"{PODS}x{PER_POD}x{SHORT.get(GPU, GPU.split()[-1])}-cluster"
            if price * PODS * PER_POD > MAX_PER_HR:
                log("price above cap, not creating")
            elif clusters():
                log("a cluster already exists, not creating")
                return 1
            else:
                try:
                    create()
                    break
                except Exception as e:
                    log("create failed:", e)
        if time.time() > end:
            log("no stock within", a.hours, "h")
            return 1
        time.sleep(a.every)
    st = load_state()
    st["timeline"] = {"created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    save_state(st)
    watchdog(a.stop)
    tl = st["timeline"]
    try:
        ts = wait_ssh(20 * 60)
        tl["ssh_ready"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        cost = sum(float(p.get("costPerHr") or 0) for p in pods())
        tl["cost_per_hr"] = cost
        log(f"cluster cost ${cost:.2f}/hr")
        if cost > MAX_PER_HR:
            raise RuntimeError(f"cost ${cost}/hr above cap")
        push(ts)
        tl["exit_codes"] = run(ts, a.tag, 40 * 60)
        tl["run_done"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        pull(ts)
    except Exception as e:
        log("FAILED:", e)
        tl["error"] = str(e)
    finally:
        st = load_state()
        st.setdefault("timeline", {}).update(tl)
        save_state(st)
        delete()
        tl["deleted"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        (LAB_DIR / "results" / a.tag).mkdir(parents=True, exist_ok=True)
        (LAB_DIR / "results" / a.tag / "timeline.json").write_text(json.dumps(tl, indent=1) + "\n")
    return 0 if not tl.get("error") else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["stock", "list", "auto", "create", "show", "push", "run", "pull", "delete"])
    ap.add_argument("tag", nargs="?", default="2x8xA100SXM")
    ap.add_argument("--hours", type=float, default=48)
    ap.add_argument("--gpus", default=GPU, help="comma-separated GPU type ids to wait for, in order")
    ap.add_argument("--every", type=int, default=120, help="seconds between stock checks")
    ap.add_argument("--stop", type=int, default=75, help="hard stop, minutes after create")
    a = ap.parse_args()
    if a.action == "stock":
        print(*stock())
    elif a.action == "list":
        cs = clusters()
        print("\n".join(json.dumps(c) for c in cs) if cs else "none")
    elif a.action == "auto":
        return auto(a)
    elif a.action == "create":
        create()
        watchdog(a.stop)
    elif a.action == "show":
        for p in pods():
            print(p["id"], p.get("desiredStatus"), p.get("costPerHr"), " ".join(ssh_args(p) or ["ssh not ready"]))
    elif a.action == "push":
        push(wait_ssh(60))
    elif a.action == "run":
        return max(run(wait_ssh(60), a.tag, 40 * 60))
    elif a.action == "pull":
        pull(wait_ssh(60))
    elif a.action == "delete":
        delete()
    return 0


if __name__ == "__main__":
    sys.exit(main())
