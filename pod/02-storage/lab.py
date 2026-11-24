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
CPU = "cpu3c"  # CPU flavor id, GET /v2/catalog/cpus
IMAGE = "runpod/base:1.0.2-ubuntu2404"


def ssh_line(p: dict) -> str:
    # v2 returns a ready-made command; `direct` is null until 22/tcp is published and the Pod runs.
    # v2 는 실행 가능한 명령을 돌려준다. 22/tcp 가 열리고 Pod 가 실행 중이어야 `direct` 가 채워진다.
    d = (p.get("ssh") or {}).get("direct")
    return d["command"] + " -i ~/.ssh/id_ed25519" if d else "not ready yet"


def pod_line(p: dict) -> str:
    m = p.get("mounts") or {}
    vol = m.get("persistent") or {}
    net = (m.get("network") or [{}])[0]
    return (f"{p['id']}  {p.get('status')}  ${p.get('cost')}/hr  "
            f"container {p.get('disk')}GB  volume {vol.get('size', 0)}GB at {vol.get('path', '-')}  "
            f"network volume {net.get('volumeId', '-')} at {net.get('path', '-')}\n    ssh  {ssh_line(p)}")


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
        pods = rest("GET", "/pods")["pods"]
        vols = rest("GET", "/network-volumes")["networkVolumes"]
        print(f"Pods ({len(pods)})")
        for p in pods:
            print("  " + pod_line(p).replace("\n", "\n  "))
        print(f"Network volumes ({len(vols)})")
        for v in vols:
            print(f"  {v['id']}  {v.get('name')}  {v.get('size')}GB  {v.get('dataCenter')}")
        return 0

    if a.what == "volume":
        if a.action == "create":
            if st.get("volume_id"):
                sys.exit(f"volume {st['volume_id']} already recorded")
            v = rest("POST", "/network-volumes", {"name": "hol-pod-02", "size": 10, "dataCenter": a.dc})
            st.update(volume_id=v["id"], dc=a.dc)
            save_state(st)
            print(json.dumps(v, indent=2))
        elif a.action == "delete":
            rest("DELETE", f"/network-volumes/{st['volume_id']}")
            print("deleted volume", st.pop("volume_id"))
            save_state(st)
        else:
            print(json.dumps(rest("GET", f"/network-volumes/{st['volume_id']}"), indent=2))
        return 0

    if a.action == "create":
        if st.get("pod_id"):
            sys.exit(f"pod {st['pod_id']} already recorded; delete it first")
        body = {
            "name": f"hol-pod-02-{'cpu' if a.cpu else 'gpu'}-{a.disk}",
            "image": IMAGE,
            "cloud": "SECURE",
            "dataCenterIds": [st.get("dc", a.dc)],
            "disk": 10,
            "ports": ["22/tcp"],
            # v2 sets up SSH only when asked; v1 always did. / v2 는 요청해야 SSH 를 설정한다.
            "startSsh": True,
        }
        if a.cpu:
            body["cpu"] = {"id": CPU, "vcpuCount": 2}
        else:
            body["gpu"] = {"id": a.gpu, "count": 1}
        if a.disk == "network":
            body["mounts"] = {"network": [{"volumeId": st["volume_id"], "path": "/workspace"}]}
        elif a.cpu:
            # v2 rejects a Pod volume on a CPU Pod; v1 accepted the field and made no volume.
            # v2 는 CPU Pod 의 Pod 볼륨을 거부한다. v1 은 필드를 받고 볼륨을 만들지 않았다.
            print("CPU Pod: no Pod volume (REST v2 disallows `mounts.persistent` on CPU Pods)")
        else:
            body["mounts"] = {"persistent": {"size": 10, "path": "/workspace"}}
        p = rest("POST", "/pods", body)
        st.update(pod_id=p["id"], disk=a.disk)
        save_state(st)
        print("created " + pod_line(p))
    elif a.action == "show":
        print(pod_line(rest("GET", f"/pods/{st['pod_id']}")))
    elif a.action in ("stop", "start"):
        rest("POST", f"/pods/{st['pod_id']}/action", {"action": a.action})
        print(a.action, st["pod_id"])
    elif a.action == "delete":
        rest("DELETE", f"/pods/{st['pod_id']}")
        print("deleted pod", st.pop("pod_id"))
        save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
