"""Serverless chat worker backed by a small instruct model.

소형 instruct 모델을 사용하는 Serverless 채팅 워커.

Local testing / 로컬 테스트:
    python handler.py                 # runs test_input.json once
    python handler.py --rp_serve_api  # local API on http://localhost:8000

Locally the model is downloaded from the Hub. On Runpod, if the endpoint has
a cached model configured, it is loaded from disk instead — see README.
로컬에서는 모델을 Hub 에서 받는다. Runpod 에서는 엔드포인트에 캐시된 모델이
설정돼 있으면 디스크에서 로드한다. README 참조.
"""

import os
import time

from model_cache import snapshot_path

# Must match the Model field on the endpoint. Overridable via an endpoint
# environment variable so one image can serve several models.
# 엔드포인트의 Model 필드와 일치해야 한다. 이미지 하나로 여러 모델을 서빙할 수
# 있도록 엔드포인트 환경변수로 덮어쓸 수 있게 했다.
MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")

# Resolve the cache BEFORE importing transformers. HF_HUB_OFFLINE and
# TRANSFORMERS_OFFLINE are read at import time, so setting them afterwards
# would have no effect.
#
# transformers 를 import 하기 전에 캐시를 확인한다. HF_HUB_OFFLINE 와
# TRANSFORMERS_OFFLINE 는 import 시점에 읽히므로, 나중에 설정하면 효과가 없다.
_CACHED_PATH = snapshot_path(MODEL_ID)
if _CACHED_PATH:
    # Cached: refuse to reach the network at all, so a cache miss fails loudly
    # instead of silently downloading on the clock.
    # 캐시 사용: 네트워크 접근을 아예 막는다. 캐시가 없으면 조용히 다운로드하며
    # 과금되는 대신 즉시 실패하도록.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import runpod  # noqa: E402  — import order is deliberate, see above
import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

# --- Module scope: runs once per worker, not once per request ---------------
# 모듈 스코프: 요청당 1회가 아니라 워커당 1회 실행된다.
#
# This is the whole point of the lab. A cold start pays this cost once; every
# subsequent request on the same worker skips it entirely.
# 이 랩의 핵심이다. 콜드 스타트가 이 비용을 한 번 치르고, 같은 워커의 이후
# 요청들은 이 과정을 통째로 건너뛴다.

_source = _CACHED_PATH or MODEL_ID
_load_started = time.perf_counter()

tokenizer = AutoTokenizer.from_pretrained(_source, local_files_only=bool(_CACHED_PATH))
model = AutoModelForCausalLM.from_pretrained(
    _source,
    local_files_only=bool(_CACHED_PATH),
    dtype="auto",       # bf16/fp16 on GPU, fp32 on CPU
    device_map="auto",  # needs `accelerate`
)
model.eval()

LOAD_SECONDS = round(time.perf_counter() - _load_started, 2)
DEVICE = str(next(model.parameters()).device)

print(
    f"Loaded {MODEL_ID} from {'cache' if _CACHED_PATH else 'hub'} "
    f"in {LOAD_SECONDS}s on {DEVICE}",
    flush=True,
)

MAX_NEW_TOKENS_CAP = 1024


def _build_messages(job_input):
    """Accept either a bare prompt or a full message list.

    단순 프롬프트와 전체 메시지 목록 양쪽을 받는다.
    """
    messages = job_input.get("messages")
    if messages:
        if not isinstance(messages, list) or not all(
            isinstance(m, dict) and "role" in m and "content" in m for m in messages
        ):
            raise ValueError(
                "messages must be a list of {role, content} objects "
                "/ messages 는 {role, content} 객체의 목록이어야 한다"
            )
        return messages

    prompt = job_input.get("prompt")
    if not prompt or not str(prompt).strip():
        raise ValueError(
            "provide either 'prompt' or 'messages' "
            "/ 'prompt' 또는 'messages' 중 하나가 필요하다"
        )

    system = job_input.get("system", "You are a concise, helpful assistant.")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": str(prompt)},
    ]


def handler(job):
    """Generate a reply for one job. / 작업 1건에 대한 응답을 생성한다."""
    job_input = job.get("input") or {}

    try:
        messages = _build_messages(job_input)
    except ValueError as exc:
        # `error` is a control key, not data: the SDK pops it and marks the job
        # FAILED. Raising would fail it too, but would hand the caller a full
        # traceback with absolute paths. This fails cleanly with one line.
        # See ../handler-reference.md.
        #
        # `error` 는 데이터가 아니라 제어 키다. SDK 가 이 키를 꺼내 작업을 실패로
        # 표시한다. 예외를 던져도 실패하지만 절대 경로가 담긴 전체 트레이스백이
        # 호출자에게 전달된다. 이 방식은 한 줄로 깔끔하게 실패한다.
        # ../handler-reference.md 참조.
        return {"error": str(exc)}

    # Clamp rather than reject — a runaway max_tokens is a cost problem, and
    # silently capping is friendlier than failing the request.
    # 거부하지 않고 상한을 건다. 과도한 max_tokens 는 비용 문제이고,
    # 요청을 실패시키기보다 조용히 잘라주는 편이 낫다.
    max_new_tokens = min(int(job_input.get("max_tokens", 256)), MAX_NEW_TOKENS_CAP)
    temperature = float(job_input.get("temperature", 0.7))

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    prompt_tokens = int(inputs["input_ids"].shape[-1])

    started = time.perf_counter()
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            top_p=float(job_input.get("top_p", 0.9)),
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # Strip the prompt back off — generate() returns prompt + completion.
    # 프롬프트를 잘라낸다. generate() 는 프롬프트와 생성분을 모두 반환한다.
    completion_ids = generated[0][inputs["input_ids"].shape[-1]:]
    reply = tokenizer.decode(completion_ids, skip_special_tokens=True).strip()

    return {
        "text": reply,
        "model": MODEL_ID,
        "tokens_in": prompt_tokens,
        "tokens_out": int(completion_ids.shape[-1]),
        "latency_ms": elapsed_ms,
        # Diagnostics that make the lab's point visible.
        # 이 랩이 보여주려는 지점을 드러내는 진단 값들.
        "loaded_from": "cache" if _CACHED_PATH else "hub",
        "model_load_seconds": LOAD_SECONDS,
        "device": DEVICE,
        "worker_id": os.environ.get("RUNPOD_POD_ID", "local"),
    }


runpod.serverless.start({"handler": handler})
