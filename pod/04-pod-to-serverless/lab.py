#!/usr/bin/env python3
"""Develop on a Pod, serve the same files from Serverless, through one network volume.

하나의 네트워크 볼륨을 통해, Pod 에서 개발한 파일을 그대로 Serverless 에서 서빙한다.

    python3 lab.py volume create         # 10 GB in EU-RO-1
    python3 lab.py pod create            # RTX 4090 Pod, volume at /workspace
    python3 lab.py pod show              # SSH command
      (on the Pod: install deps into /workspace/app/deps, copy handler.py, test it)
    python3 lab.py pod delete
    python3 lab.py endpoint create       # template + endpoint, same volume at /runpod-volume
    python3 lab.py run                   # one runsync job
    python3 lab.py endpoint delete
    python3 lab.py volume delete
    python3 lab.py status
"""

import argparse
import json
import sys
import time
import urllib.request

from common import api_key, load_state, rest, save_state

DC = "EU-RO-1"
GPU = "NVIDIA GeForce RTX 4090"
# Has CUDA, torch and python3.12; the Pod and the workers run the same image.
# CUDA, torch, python3.12 포함. Pod 과 워커가 같은 이미지를 쓴다.
IMAGE = "runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404"


def pod_line(p: dict) -> str:
    ip, ports = p.get("publicIp"), p.get("portMappings") or {}
    ssh = f"ssh root@{ip} -p {ports['22']} -i ~/.ssh/id_ed25519" if ip and "22" in ports else "not ready yet"
    return f"{p['id']}  {p.get('desiredStatus')}  ${p.get('costPerHr')}/hr\n    ssh  {ssh}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["volume", "pod", "endpoint", "run", "status"])
    ap.add_argument("action", nargs="?", choices=["create", "show", "delete"])
    ap.add_argument("--n", type=int, default=4096)
    a = ap.parse_args()
    st = load_state()

    if a.what == "status":
        print("pods     ", [(p["id"], p.get("desiredStatus")) for p in rest("GET", "/pods")])
        print("endpoints", [(e["id"], e.get("name")) for e in rest("GET", "/endpoints")])
        print("volumes  ", [(v["id"], v.get("name")) for v in rest("GET", "/networkvolumes")])
        print("templates", [(t["id"], t["name"]) for t in rest("GET", "/templates") if t.get("name", "").startswith("hol-pod-04")])
        return 0

    if a.what == "volume":
        if a.action == "create":
            v = rest("POST", "/networkvolumes", {"name": "hol-pod-04", "size": 10, "dataCenterId": DC})
            st["volume_id"] = v["id"]
            print(json.dumps(v))
        elif a.action == "delete":
            rest("DELETE", f"/networkvolumes/{st.pop('volume_id')}")
            print("deleted volume")
        save_state(st)
        return 0

    if a.what == "pod":
        if a.action == "create":
            p = rest("POST", "/pods", {
                "name": "hol-pod-04-dev", "imageName": IMAGE, "cloudType": "SECURE",
                "computeType": "GPU", "gpuTypeIds": [GPU], "gpuCount": 1,
                "dataCenterIds": [DC], "networkVolumeId": st["volume_id"],
                "volumeMountPath": "/workspace", "containerDiskInGb": 20, "ports": ["22/tcp"],
            })
            st["pod_id"] = p["id"]
            print("created " + pod_line(p))
        elif a.action == "show":
            print(pod_line(rest("GET", f"/pods/{st['pod_id']}")))
        elif a.action == "delete":
            rest("DELETE", f"/pods/{st.pop('pod_id')}")
            print("deleted pod")
        save_state(st)
        return 0

    if a.what == "endpoint":
        if a.action == "create":
            t = rest("POST", "/templates", {
                "name": "hol-pod-04-worker", "imageName": IMAGE, "isServerless": True,
                "containerDiskInGb": 20, "volumeInGb": 0,
                # The worker runs the file the Pod wrote. Serverless mounts the
                # network volume at /runpod-volume, not /workspace.
                # 워커는 Pod 이 쓴 파일을 실행한다. Serverless 는 네트워크 볼륨을
                # /workspace 가 아니라 /runpod-volume 에 마운트한다.
                "dockerStartCmd": ["python3", "-u", "/runpod-volume/app/handler.py"],
                "env": {"PYTHONPATH": "/runpod-volume/app/deps"},
            })
            st["template_id"] = t["id"]
            save_state(st)
            e = rest("POST", "/endpoints", {
                "name": "hol-pod-04", "templateId": t["id"], "computeType": "GPU",
                "gpuTypeIds": [GPU], "gpuCount": 1, "workersMin": 0, "workersMax": 1,
                "idleTimeout": 5, "networkVolumeId": st["volume_id"],
            })
            st["endpoint_id"] = e["id"]
            print(f"template {t['id']}, endpoint {e['id']}")
        elif a.action == "delete":
            rest("DELETE", f"/endpoints/{st.pop('endpoint_id')}")
            print("deleted endpoint")
            try:
                rest("DELETE", f"/templates/{st['template_id']}")
                st.pop("template_id")
                print("deleted template")
            except SystemExit as e:
                print(f"template kept for now: {e}")
        save_state(st)
        return 0

    # run: one synchronous job, waiting through a cold start
    req = urllib.request.Request(
        f"https://api.runpod.ai/v2/{st['endpoint_id']}/runsync",
        data=json.dumps({"input": {"n": a.n}}).encode(), method="POST",
        headers={"Authorization": "Bearer " + api_key(), "Content-Type": "application/json",
                 "User-Agent": "runpod-hols-pod-to-serverless/1.0"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        out = json.loads(r.read())
    # runsync gave up after ~90 s on a cold start (2026-11-05) and returned
    # IN_QUEUE with the job id; the job itself carries on. Poll /status.
    # 콜드 스타트에서 runsync 는 약 90초 후 IN_QUEUE 와 job id 를 돌려줬다.
    # 작업은 계속 진행되므로 /status 를 폴링한다.
    while out.get("status") in ("IN_QUEUE", "IN_PROGRESS"):
        print(f"  {out['status']} after {time.time() - t:.0f}s")
        time.sleep(10)
        status = urllib.request.Request(
            f"https://api.runpod.ai/v2/{st['endpoint_id']}/status/{out['id']}",
            headers={"Authorization": "Bearer " + api_key(), "User-Agent": "runpod-hols-pod-to-serverless/1.0"})
        with urllib.request.urlopen(status, timeout=60) as r:
            out = json.loads(r.read())
    print(f"wall {time.time() - t:.1f}s")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
