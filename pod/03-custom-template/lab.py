#!/usr/bin/env python3
"""A Pod template with plain environment variables and a Runpod secret, and a Pod made from it.

일반 환경변수와 Runpod 시크릿을 쓰는 Pod 템플릿, 그리고 그 템플릿으로 만든 Pod.

    python3 lab.py secret create            # random demo value; only its SHA-256 is printed
    python3 lab.py template create          # env: GREETING (plain) + DEMO_SECRET (secret reference)
    python3 lab.py pod create               # CPU Pod from the template
    python3 lab.py pod show                 # status, SSH command, env as the API returns it
    python3 lab.py secret rotate            # new value; the Pod sees it after a restart
    python3 lab.py pod restart
    python3 lab.py pod delete
    python3 lab.py template delete
    python3 lab.py secret delete

The demo secret is a random string made here, never a real credential.
데모 시크릿은 여기서 만든 임의 문자열이며 실제 자격 증명이 아니다.
"""

import argparse
import hashlib
import json
import secrets
import sys

from common import REST_V2, load_state, rest, save_state

SECRET_NAME = "hol_pod_03_demo"
IMAGE = "runpod/base:1.0.2-ubuntu2404"


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def new_value(st: dict) -> str:
    value = "hol-demo-" + secrets.token_hex(8)
    st["secret_sha256_16"] = sha(value)
    print(f"secret value sha256[:16] = {st['secret_sha256_16']}  (compare inside the Pod / Pod 안에서 비교)")
    return value


def pod_line(p: dict) -> str:
    ip, ports = p.get("publicIp"), p.get("portMappings") or {}
    ssh = f"ssh root@{ip} -p {ports['22']} -i ~/.ssh/id_ed25519" if ip and "22" in ports else "not ready yet"
    return f"{p['id']}  {p.get('desiredStatus')}  ${p.get('costPerHr')}/hr  template {p.get('templateId')}\n    ssh  {ssh}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["secret", "template", "pod", "status"])
    ap.add_argument("action", nargs="?", choices=["create", "rotate", "show", "restart", "delete"])
    a = ap.parse_args()
    st = load_state()

    if a.what == "status":
        print("secrets  ", [s["name"] for s in rest("GET", "/account/secrets", base=REST_V2)["secrets"]])
        print("templates", [(t["id"], t["name"]) for t in rest("GET", "/templates") if t.get("name", "").startswith("hol-pod-03")])
        print("pods     ", [(p["id"], p.get("desiredStatus")) for p in rest("GET", "/pods")])
        return 0

    if a.what == "secret":
        if a.action == "create":
            s = rest("POST", "/account/secrets", {"name": SECRET_NAME, "value": new_value(st),
                                                  "description": "runpod-hols pod/03 demo, not a credential"}, base=REST_V2)
            st["secret_id"] = s["id"]
            print(json.dumps(s, indent=2))
        elif a.action == "rotate":
            s = rest("PATCH", f"/account/secrets/{st['secret_id']}", {"value": new_value(st)}, base=REST_V2)
            print(json.dumps(s, indent=2))
        elif a.action == "delete":
            rest("DELETE", f"/account/secrets/{st.pop('secret_id')}", base=REST_V2)
            print("deleted secret", SECRET_NAME)
        save_state(st)
        return 0

    if a.what == "template":
        if a.action == "create":
            t = rest("POST", "/templates", {
                "name": "hol-pod-03",
                "imageName": IMAGE,
                "category": "CPU",
                "isServerless": False,
                "containerDiskInGb": 10,
                "volumeInGb": 0,
                "ports": ["22/tcp"],
                "env": {
                    "GREETING": "hello from the template",
                    "DEMO_SECRET": "{{ RUNPOD_SECRET_%s }}" % SECRET_NAME,
                },
                "readme": "runpod-hols pod/03-custom-template",
            })
            st["template_id"] = t["id"]
            print(json.dumps({k: t.get(k) for k in ("id", "name", "imageName", "env", "category")}, indent=2))
        elif a.action == "show":
            print(json.dumps(rest("GET", f"/templates/{st['template_id']}"), indent=2))
        elif a.action == "delete":
            rest("DELETE", f"/templates/{st.pop('template_id')}")
            print("deleted template")
        save_state(st)
        return 0

    if a.action == "create":
        p = rest("POST", "/pods", {
            "name": "hol-pod-03",
            "templateId": st["template_id"],
            "computeType": "CPU",
            "cpuFlavorIds": ["cpu3c"],
            "vcpuCount": 2,
            "cloudType": "SECURE",
        })
        st["pod_id"] = p["id"]
        save_state(st)
        print("created " + pod_line(p))
        print("    env (create response)", json.dumps(p.get("env")))
    elif a.action == "show":
        p = rest("GET", f"/pods/{st['pod_id']}")
        print(pod_line(p))
        print("    env (GET /pods)", json.dumps(p.get("env")))
    elif a.action == "restart":
        rest("POST", f"/pods/{st['pod_id']}/restart")
        print("restarted", st["pod_id"])
    elif a.action == "delete":
        rest("DELETE", f"/pods/{st.pop('pod_id')}")
        save_state(st)
        print("deleted pod")
    return 0


if __name__ == "__main__":
    sys.exit(main())
