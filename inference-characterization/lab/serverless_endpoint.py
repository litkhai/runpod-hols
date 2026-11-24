#!/usr/bin/env python3
"""Create, inspect and remove the Serverless endpoint used by coldstart_probe.py.

Usage:
    python3 serverless_endpoint.py create [--flashboot on|off] [--gpu "NVIDIA GeForce RTX 4090"] [--workers-max 1]
    python3 serverless_endpoint.py show
    python3 serverless_endpoint.py delete

create makes a template (runpod/worker-v1-vllm) and an endpoint with workers min 0, max 1,
idleTimeout 5, PATCHes flashboot after the create and checks the read-back (the create call
ignored false on 2026-11-07, #60), and records both ids in results/serverless.json so delete needs no argument.
Workers bill only while running; delete removes the endpoint and the template.

Field names come from the published REST v2 spec (api.runpod.io/v2/openapi.json, read 2026-11-24):
CreateTemplateRequest and CreateEndpointRequest. The October runs used v1, retired 2026-11-15 (#101).
v2 selects Serverless GPUs by pool (GET /v2/catalog/gpus, `pool`), so --gpu became --pool.
"""
import argparse, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pod_sweep import RESULTS, api, jload, jsave, load_env  # noqa: E402

STATE = os.path.join(RESULTS, "serverless.json")
# worker-vllm v2.28.0 bundles vLLM 0.30.0 (release notes, read 2026-10-06); Phase A uses 0.31.0.
IMAGE = "runpod/worker-v1-vllm:v2.28.0"
MODEL = "Qwen/Qwen2.5-7B-Instruct"
# v2 FlashBoot is an enum (OFF, FLASHBOOT, PRIORITY_FLASHBOOT), not a boolean.
FLASHBOOT = {"on": "FLASHBOOT", "off": "OFF"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["create", "show", "delete"])
    ap.add_argument("--flashboot", default="on", choices=["on", "off"])
    ap.add_argument("--pool", default="ADA_24", help="Serverless GPU pool; ADA_24 holds the RTX 4090")
    ap.add_argument("--workers-max", type=int, default=1)
    ap.add_argument("--network-volume", default="", help="attach a network volume (weights then land in /runpod-volume, #69)")
    ap.add_argument("--dc", default="", help="pin to the volume's datacenter")
    a = ap.parse_args()
    load_env()
    st = jload(STATE, {})

    if a.action == "create":
        if st.get("endpoint_id"):
            sys.exit("endpoint %s already recorded; delete it first" % st["endpoint_id"])
        tpl = api("POST", "/templates", {
            # Unique per run: a deleted endpoint holds its template for ~90 min, and names must be unique.
            "name": "ic-coldstart-vllm-" + time.strftime("%m%d%H%M"), "image": IMAGE, "serverless": True, "disk": 60,
            "env": {"MODEL_NAME": MODEL, "MAX_MODEL_LEN": "8192"}})
        st = {"template_id": tpl["id"], "image": IMAGE, "model": MODEL}
        jsave(STATE, st)
        ep = api("POST", "/serverless", {
            "name": "ic-coldstart-flashboot-" + a.flashboot, "templateId": tpl["id"], "type": "QUEUE",
            "scaling": {"type": "QUEUE_DELAY", "queueDelay": 4},
            # Same driver floor as the Pods; a CUDA 13 driver also runs a CUDA 12.x image.
            "gpu": {"pools": [a.pool], "count": 1, "minCudaVersion": "13.0"},
            "workers": {"min": 0, "max": a.workers_max, "idleTimeout": 5},
            "flashboot": FLASHBOOT[a.flashboot],
            **({"mounts": {"network": [{"volumeId": a.network_volume}]}} if a.network_volume else {}),
            **({"dataCenterIds": [a.dc]} if a.dc else {})})
        st.update(endpoint_id=ep["id"], flashboot=a.flashboot, pool=a.pool, workers_max=a.workers_max)
        jsave(STATE, st)
        # On 2026-11-07 the create call ignored "flashboot": false and the endpoint read back true
        # (#60), so set it again and record what the API reports rather than what was asked for.
        want = FLASHBOOT[a.flashboot]
        api("PATCH", "/serverless/" + ep["id"], {"flashboot": want})
        got = api("GET", "/serverless/" + ep["id"]).get("flashboot")
        st.update(flashboot_reported=got)
        jsave(STATE, st)
        if got != want:
            sys.exit("flashboot reads back %s after PATCH, wanted %s; endpoint %s left in place" % (got, want, ep["id"]))
        print(json.dumps(st, indent=2))
        print("ENDPOINT_ID=%s" % ep["id"])
    elif a.action == "show":
        if not st.get("endpoint_id"):
            sys.exit("no endpoint recorded")
        ep = api("GET", "/serverless/" + st["endpoint_id"])
        print(json.dumps({k: ep.get(k) for k in ("id", "name", "flashboot", "workers", "gpu")}, indent=2))
    else:
        if st.get("endpoint_id"):
            api("DELETE", "/serverless/" + st["endpoint_id"])
            print("deleted endpoint", st["endpoint_id"])
        if st.get("template_id"):
            api("DELETE", "/templates/" + st["template_id"])
            print("deleted template", st["template_id"])
        jsave(STATE, {})


if __name__ == "__main__":
    main()
