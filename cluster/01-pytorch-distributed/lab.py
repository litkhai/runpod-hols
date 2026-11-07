#!/usr/bin/env python3
"""Stage 1: one Pod with several GPUs — create, copy the scripts, run, fetch results, delete.

1단계: GPU 여러 장짜리 Pod 하나 — 생성, 스크립트 복사, 실행, 결과 회수, 삭제.

    python3 lab.py create                    # 2x RTX 4090, Secure Cloud, any datacenter
    python3 lab.py create --gpu "NVIDIA A40" --count 2
    python3 lab.py show                      # status, cost, SSH command
    python3 lab.py push                      # copy run.sh and the .py files to /workspace/dist
    python3 lab.py run 2x4090                # bash run.sh 2x4090 inside the Pod
    python3 lab.py pull                      # results/ back into this folder
    python3 lab.py delete

The Instant Cluster stage is created in the console; see README.
Instant Cluster 단계는 콘솔에서 만든다. README 참고.
"""

import argparse
import subprocess
import sys
import time

from common import LAB_DIR, load_state, rest, save_state

GPU = "NVIDIA GeForce RTX 4090"
# torch 2.9.1, CUDA 12.8.1; the same image the inference-characterization sweeps used.
# inference-characterization 측정에 쓴 것과 같은 이미지.
IMAGE = "runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404"
REMOTE = "/workspace/dist"
FILES = ["run.sh", "nccl_bench.py", "ddp_train.py"]


def ssh_target(p: dict) -> list:
    ip, ports = p.get("publicIp"), p.get("portMappings") or {}
    if not ip or "22" not in ports:
        sys.exit("SSH not ready yet; try `lab.py show` again in a minute")
    return ["-p", str(ports["22"]), "-i", str(__import__("pathlib").Path.home() / ".ssh/id_ed25519"),
            "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15", f"root@{ip}"]


def pod_line(p: dict) -> str:
    ip, ports = p.get("publicIp"), p.get("portMappings") or {}
    ssh = f"ssh root@{ip} -p {ports['22']}" if ip and "22" in ports else "not ready yet"
    m = p.get("machine") or {}
    return (f"{p['id']}  {p.get('desiredStatus')}  {p.get('gpuCount')}x {(p.get('gpu') or {}).get('id', '?')}  "
            f"${p.get('costPerHr')}/hr  {m.get('dataCenterId', '')}\n    ssh  {ssh}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["create", "show", "push", "run", "pull", "delete"])
    ap.add_argument("tag", nargs="?")
    ap.add_argument("--gpu", default=GPU)
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--cloud", default="SECURE", choices=["SECURE", "COMMUNITY"])
    ap.add_argument("--dc", default="", help="pin to one datacenter / 데이터센터 고정")
    a = ap.parse_args()
    st = load_state()

    if a.action == "create":
        if st.get("pod_id"):
            sys.exit(f"pod {st['pod_id']} already recorded; delete it first")
        body = {
            "name": f"hol-cluster-01-{a.count}gpu",
            "imageName": IMAGE,
            "computeType": "GPU",
            "gpuTypeIds": [a.gpu],
            "gpuCount": a.count,
            "cloudType": a.cloud,
            "containerDiskInGb": 30,
            "volumeInGb": 0,
            "ports": ["22/tcp"],
        }
        if a.dc:
            body["dataCenterIds"] = [a.dc]
        p = rest("POST", "/pods", body)
        st.update(pod_id=p["id"], created=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        save_state(st)
        print("created " + pod_line(p))
        return 0

    if not st.get("pod_id"):
        sys.exit("no pod recorded; run `lab.py create`")
    pid = st["pod_id"]
    if a.action == "show":
        print(pod_line(rest("GET", f"/pods/{pid}")))
    elif a.action == "push":
        t = ssh_target(rest("GET", f"/pods/{pid}"))
        subprocess.run(["ssh", *t, f"mkdir -p {REMOTE}"], check=True)
        port, key = t[1], t[3]
        subprocess.run(["scp", "-P", port, "-i", key, "-o", "StrictHostKeyChecking=accept-new",
                        *[str(LAB_DIR / f) for f in FILES], f"{t[-1]}:{REMOTE}/"], check=True)
        print("copied", ", ".join(FILES), "->", REMOTE)
    elif a.action == "run":
        if not a.tag:
            sys.exit("give a tag, e.g. `lab.py run 2x4090`")
        t = ssh_target(rest("GET", f"/pods/{pid}"))
        return subprocess.run(["ssh", *t, f"bash {REMOTE}/run.sh {a.tag}"]).returncode
    elif a.action == "pull":
        t = ssh_target(rest("GET", f"/pods/{pid}"))
        (LAB_DIR / "results").mkdir(exist_ok=True)
        # tar over ssh: newer scp refuses "dir/." as a remote source.
        # 최신 scp 는 원격 경로 "dir/." 를 거부하므로 ssh 로 tar 를 받는다.
        tar = subprocess.run(["ssh", *t, f"tar -C {REMOTE}/results -cf - ."], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-C", str(LAB_DIR / "results"), "-xf", "-"], input=tar, check=True)
        print("results ->", LAB_DIR / "results")
    elif a.action == "delete":
        rest("DELETE", f"/pods/{pid}")
        print("deleted pod", st.pop("pod_id"))
        save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
