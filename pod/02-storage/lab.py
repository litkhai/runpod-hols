#!/usr/bin/env python3
"""Create, stop, start and delete the Pods and the network volume for the storage lab.

스토리지 실습용 Pod 와 네트워크 볼륨을 만들고, 중지·재개·삭제한다.

    python lab.py volume create             # 10 GB network volume in --dc
    python lab.py pod create --disk volume  # Pod with a Pod volume at /workspace
    python lab.py pod create --disk network # Pod with the network volume at /workspace
    python lab.py pod show                  # status, cost, SSH command
    python lab.py pod stop | start | delete
    python lab.py volume delete
    python lab.py status                    # everything on the account that bills

One Pod at a time; its id is kept in .storage.json.
Pod 는 한 번에 하나. id 는 .storage.json 에 기록된다.
"""

import argparse
import json
import sys

from common import load_state, rest, save_state

DC = "EU-RO-1"
GPU = "NVIDIA GeForce RTX 4090"
IMAGE = "runpod/base:1.0.2-ubuntu2404"


def pod_line(p: dict) -> str:
    ip, ports = p.get("publicIp"), p.get("portMappings") or {}
    ssh = f"ssh root@{ip} -p {ports['22']} -i ~/.ssh/id_ed25519" if ip and "22" in ports else "not ready yet"
    nv = (p.get("networkVolume") or {}).get("id")
    return (f"{p['id']}  {p.get('desiredStatus')}  ${p.get('costPerHr')}/hr  "
            f"container {p.get('containerDiskInGb')}GB  volume {p.get('volumeInGb')}GB  "
            f"network volume {nv or '-'}  at {p.get('volumeMountPath')}\n    ssh  {ssh}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["volume", "pod", "status"])
    ap.add_argument("action", nargs="?", choices=["create", "show", "stop", "start", "delete"])
    ap.add_argument("--disk", choices=["volume", "network"], default="volume")
    ap.add_argument("--dc", default=DC)
    ap.add_argument("--gpu", default=GPU)
    ap.add_argument("--cpu", action="store_true", help="CPU Pod (cpu3c, 2 vCPU) instead of a GPU / GPU 대신 CPU Pod")
    a = ap.parse_args()
    st = load_state()

    if a.what == "status":
        pods = rest("GET", "/pods")
        vols = rest("GET", "/networkvolumes")
        print(f"Pods ({len(pods)})")
        for p in pods:
            print("  " + pod_line(p).replace("\n", "\n  "))
        print(f"Network volumes ({len(vols)})")
        for v in vols:
            print(f"  {v['id']}  {v.get('name')}  {v.get('size')}GB  {v.get('dataCenterId')}")
        return 0

    if a.what == "volume":
        if a.action == "create":
            if st.get("volume_id"):
                sys.exit(f"volume {st['volume_id']} already recorded")
            v = rest("POST", "/networkvolumes", {"name": "hol-pod-02", "size": 10, "dataCenterId": a.dc})
            st.update(volume_id=v["id"], dc=a.dc)
            save_state(st)
            print(json.dumps(v, indent=2))
        elif a.action == "delete":
            rest("DELETE", f"/networkvolumes/{st['volume_id']}")
            print("deleted volume", st.pop("volume_id"))
            save_state(st)
        else:
            print(json.dumps(rest("GET", f"/networkvolumes/{st['volume_id']}"), indent=2))
        return 0

    if a.action == "create":
        if st.get("pod_id"):
            sys.exit(f"pod {st['pod_id']} already recorded; delete it first")
        body = {
            "name": f"hol-pod-02-{'cpu' if a.cpu else 'gpu'}-{a.disk}",
            "imageName": IMAGE,
            "cloudType": "SECURE",
            "dataCenterIds": [st.get("dc", a.dc)],
            "containerDiskInGb": 10,
            "volumeMountPath": "/workspace",
            "ports": ["22/tcp"],
        }
        if a.cpu:
            body.update(computeType="CPU", cpuFlavorIds=["cpu3c"], vcpuCount=2)
        else:
            body.update(computeType="GPU", gpuTypeIds=[a.gpu], gpuCount=1)
        if a.disk == "network":
            body["networkVolumeId"] = st["volume_id"]
        else:
            body["volumeInGb"] = 10
        p = rest("POST", "/pods", body)
        st.update(pod_id=p["id"], disk=a.disk)
        save_state(st)
        print("created " + pod_line(p))
    elif a.action == "show":
        print(pod_line(rest("GET", f"/pods/{st['pod_id']}")))
    elif a.action in ("stop", "start"):
        rest("POST", f"/pods/{st['pod_id']}/{a.action}")
        print(a.action, st["pod_id"])
    elif a.action == "delete":
        rest("DELETE", f"/pods/{st['pod_id']}")
        print("deleted pod", st.pop("pod_id"))
        save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
