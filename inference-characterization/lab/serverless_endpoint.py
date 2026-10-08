#!/usr/bin/env python3
"""Create, inspect and remove the Serverless endpoint used by coldstart_probe.py.

Usage:
    python3 serverless_endpoint.py create [--flashboot on|off] [--gpu "NVIDIA GeForce RTX 4090"] [--workers-max 1]
    python3 serverless_endpoint.py show
    python3 serverless_endpoint.py delete

create makes a template (runpod/worker-v1-vllm) and an endpoint with workersMin 0, workersMax 1,
idleTimeout 5, and records both ids in results/serverless.json so delete needs no argument.
Workers bill only while running; delete removes the endpoint and the template.

Field names come from the published OpenAPI spec (rest.runpod.io/v1/openapi.json, read 2026-10-06):
TemplateCreateInput and EndpointCreateInput.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pod_sweep import RESULTS, api, jload, jsave, load_env  # noqa: E402

STATE = os.path.join(RESULTS, "serverless.json")
# worker-vllm v2.28.0 bundles vLLM 0.30.0 (release notes, read 2026-10-06); Phase A uses 0.31.0.
IMAGE = "runpod/worker-v1-vllm:v2.28.0"
MODEL = "Qwen/Qwen2.5-7B-Instruct"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["create", "show", "delete"])
    ap.add_argument("--flashboot", default="on", choices=["on", "off"])
    ap.add_argument("--gpu", default="NVIDIA GeForce RTX 4090")
    ap.add_argument("--workers-max", type=int, default=1)
    a = ap.parse_args()
    load_env()
    st = jload(STATE, {})

    if a.action == "create":
        if st.get("endpoint_id"):
            sys.exit("endpoint %s already recorded; delete it first" % st["endpoint_id"])
        tpl = api("POST", "/templates", {
            "name": "ic-coldstart-vllm", "imageName": IMAGE, "isServerless": True,
            "containerDiskInGb": 60, "volumeInGb": 0,
            "env": {"MODEL_NAME": MODEL, "MAX_MODEL_LEN": "8192"}})
        st = {"template_id": tpl["id"], "image": IMAGE, "model": MODEL}
        jsave(STATE, st)
        ep = api("POST", "/endpoints", {
            "name": "ic-coldstart-flashboot-" + a.flashboot, "templateId": tpl["id"],
            "computeType": "GPU", "gpuTypeIds": [a.gpu], "gpuCount": 1,
            "workersMin": 0, "workersMax": a.workers_max, "idleTimeout": 5,
            # Same driver floor as the Pods; a CUDA 13 driver also runs a CUDA 12.x image.
            "minCudaVersion": "13.0",
            "flashboot": a.flashboot == "on"})
        st.update(endpoint_id=ep["id"], flashboot=a.flashboot, gpu=a.gpu, workers_max=a.workers_max)
        jsave(STATE, st)
        print(json.dumps(st, indent=2))
        print("ENDPOINT_ID=%s" % ep["id"])
    elif a.action == "show":
        if not st.get("endpoint_id"):
            sys.exit("no endpoint recorded")
        ep = api("GET", "/endpoints/" + st["endpoint_id"])
        print(json.dumps({k: ep.get(k) for k in ("id", "name", "flashboot", "workersMin", "workersMax",
                                                  "idleTimeout", "gpuTypeIds", "templateId")}, indent=2))
    else:
        if st.get("endpoint_id"):
            api("DELETE", "/endpoints/" + st["endpoint_id"])
            print("deleted endpoint", st["endpoint_id"])
        if st.get("template_id"):
            api("DELETE", "/templates/" + st["template_id"])
            print("deleted template", st["template_id"])
        jsave(STATE, {})


if __name__ == "__main__":
    main()
