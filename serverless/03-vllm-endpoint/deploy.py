#!/usr/bin/env python3
"""Create a Serverless endpoint running Runpod's prebuilt vLLM worker.

Runpod 의 미리 빌드된 vLLM 워커로 Serverless 엔드포인트를 만든다.

    python deploy.py --dry-run     # print the template and endpoint, create nothing
    python deploy.py               # create both, record ids in .endpoint.json

Nothing bills until a request arrives: workers.min is 0. A worker then bills
from boot until idleTimeout seconds after its last request.
workers.min 이 0 이므로 요청이 오기 전에는 과금되지 않는다. 요청이 오면 워커는
기동부터 마지막 요청 후 idleTimeout 초까지 과금된다.
"""

import argparse
import json
import sys

from common import load_state, rest, save_state

# Prebuilt image from runpod-workers/worker-vllm, tag v2.32.0 (release 2026-11-19; v2.30.2 until 2026-11-26).
# No build, no registry auth: the endpoint pulls it directly.
# runpod-workers/worker-vllm 의 미리 빌드된 이미지. 빌드도 레지스트리 인증도 필요 없다.
IMAGE = "runpod/worker-v1-vllm:v2.32.0"
MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
# REST v2 selects Serverless GPUs by pool (GET /v2/catalog/gpus, `pool`), not by type,
# and places workers on whichever listed pool has capacity — there is no order.
# The v1 list was RTX 4090, RTX A5000, RTX A4500: pools ADA_24, AMPERE_24, AMPERE_16 (catalog read 2026-11-24).
# REST v2 는 Serverless GPU 를 종류가 아니라 풀로 고르고, 여유가 있는 풀에 워커를 놓는다 (순서 없음).
POOLS = ["ADA_24", "AMPERE_24", "AMPERE_16"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--max-model-len", default="4096")
    ap.add_argument("--pool", action="append", help="GPU pool id; repeat for more pools / 반복하면 풀 추가")
    ap.add_argument("--workers-max", type=int, default=1)
    ap.add_argument("--idle-timeout", type=int, default=5, help="seconds / 초")
    ap.add_argument("--flashboot", choices=["on", "off"], default="on")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if load_state().get("endpoint_id"):
        print("An endpoint is already recorded in .endpoint.json. Run teardown.py first.")
        print(".endpoint.json 에 엔드포인트가 이미 기록돼 있습니다. 먼저 teardown.py 를 실행하세요.")
        return 1

    template = {
        "name": "hol-03-vllm",
        "image": IMAGE,
        "serverless": True,
        "disk": 30,
        "env": {"MODEL_NAME": a.model, "MAX_MODEL_LEN": a.max_model_len},
    }
    endpoint = {
        "name": "hol-03-vllm",
        "type": "QUEUE",
        "scaling": {"type": "QUEUE_DELAY", "queueDelay": 4},
        "gpu": {"pools": a.pool or POOLS, "count": 1},
        "workers": {"min": 0, "max": a.workers_max, "idleTimeout": a.idle_timeout},
        "flashboot": "FLASHBOOT" if a.flashboot == "on" else "OFF",
    }
    print("Template / 템플릿:\n" + json.dumps(template, indent=2))
    print("Endpoint / 엔드포인트:\n" + json.dumps(endpoint, indent=2))
    if a.dry_run:
        print("\n--dry-run: nothing created. / 아무것도 생성하지 않았습니다.")
        return 0

    tpl = rest("POST", "/templates", template)
    state = {"template_id": tpl["id"], "image": IMAGE, "model": a.model}
    save_state(state)  # recorded before the endpoint, so teardown can remove a half-made pair
    ep = rest("POST", "/serverless", {**endpoint, "templateId": tpl["id"]})
    state["endpoint_id"] = ep["id"]
    save_state(state)

    print(f"\nCreated template {tpl['id']} and endpoint {ep['id']}")
    print(f"템플릿 {tpl['id']}, 엔드포인트 {ep['id']} 생성")
    print(f"OpenAI base URL: https://api.runpod.ai/v2/{ep['id']}/openai/v1")
    print("\nNext / 다음:  python chat.py   then / 끝나면  python teardown.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
