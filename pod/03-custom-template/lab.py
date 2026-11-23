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

from common import load_state, rest, save_state

SECRET_NAME = "hol_pod_03_demo"
IMAGE = "runpod/base:1.0.2-ubuntu2404"
CPU = "cpu3c"  # CPU flavor id, GET /v2/catalog/cpus


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def new_value(st: dict) -> str:
    value = "hol-demo-" + secrets.token_hex(8)
    st["secret_sha256_16"] = sha(value)
    print(f"secret value sha256[:16] = {st['secret_sha256_16']}  (compare inside the Pod / Pod 안에서 비교)")
    return value


def pod_line(p: dict) -> str:
    # v2 returns a ready-made command; `direct` is null until 22/tcp is published and the Pod runs.
    # v2 는 실행 가능한 명령을 돌려준다. 22/tcp 가 열리고 Pod 가 실행 중이어야 `direct` 가 채워진다.
    d = (p.get("ssh") or {}).get("direct")
    ssh = d["command"] + " -i ~/.ssh/id_ed25519" if d else "not ready yet"
    return f"{p['id']}  {p.get('status')}  ${p.get('cost')}/hr  template {p.get('template')}\n    ssh  {ssh}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["secret", "template", "pod", "status"])
    ap.add_argument("action", nargs="?", choices=["create", "rotate", "show", "restart", "delete"])
    a = ap.parse_args()
    st = load_state()

    if a.what == "status":
        print("secrets  ", [s["name"] for s in rest("GET", "/account/secrets")["secrets"]])
        print("templates", [(t["id"], t["name"]) for t in rest("GET", "/templates")["templates"] if t.get("name", "").startswith("hol-pod-03")])
        print("pods     ", [(p["id"], p.get("status")) for p in rest("GET", "/pods")["pods"]])
        return 0

    if a.what == "secret":
        if a.action == "create":
            s = rest("POST", "/account/secrets", {"name": SECRET_NAME, "value": new_value(st),
                                                  "description": "runpod-hols pod/03 demo, not a credential"})
            st["secret_id"] = s["id"]
            print(json.dumps(s, indent=2))
        elif a.action == "rotate":
            s = rest("PATCH", f"/account/secrets/{st['secret_id']}", {"value": new_value(st)})
            print(json.dumps(s, indent=2))
        elif a.action == "delete":
            rest("DELETE", f"/account/secrets/{st.pop('secret_id')}")
            print("deleted secret", SECRET_NAME)
        save_state(st)
        return 0

    if a.what == "template":
        if a.action == "create":
            t = rest("POST", "/templates", {
                "name": "hol-pod-03",
                "image": IMAGE,
                "category": "CPU",
                "serverless": False,
                "disk": 10,
                "ports": ["22/tcp"],
                "startSsh": True,
                "startJupyter": False,
                "env": {
                    "GREETING": "hello from the template",
                    "DEMO_SECRET": "{{ RUNPOD_SECRET_%s }}" % SECRET_NAME,
                },
            })
            st["template_id"] = t["id"]
            print(json.dumps({k: t.get(k) for k in ("id", "name", "image", "env", "category")}, indent=2))
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
            "cpu": {"id": CPU, "vcpuCount": 2},
            "cloud": "SECURE",
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
        rest("POST", f"/pods/{st['pod_id']}/action", {"action": "restart"})
        print("restarted", st["pod_id"])
    elif a.action == "delete":
        rest("DELETE", f"/pods/{st.pop('pod_id')}")
        save_state(st)
        print("deleted pod")
    return 0


if __name__ == "__main__":
    sys.exit(main())
