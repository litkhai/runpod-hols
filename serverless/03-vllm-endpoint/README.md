# Serverless Lab 03 — vLLM Endpoint, OpenAI-Compatible

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** serve a model with Runpod's prebuilt vLLM worker and call it with the OpenAI SDK, changing only `base_url` and `api_key`.

**Time:** ~20 minutes, most of it the first cold start · **Cost:** GPU seconds while a worker runs; nothing while idle

### How it differs from Lab 02

| | Lab 02 | Lab 03 |
|---|---|---|
| Worker code | Your `handler.py`, built from GitHub | None — `runpod/worker-v1-vllm:v2.30.2` from Docker Hub |
| Deploy | Console (GitHub builds are console-only) | `deploy.py`, REST API |
| Client | `runsync` with Runpod's job format | OpenAI SDK against `/openai/v1` |
| Serving | transformers, one request at a time | vLLM, continuous batching |

### Files

| File | Role |
|---|---|
| `deploy.py` | Creates a template and an endpoint (workers 0–1, idle 5 s, FlashBoot on); records ids in `.endpoint.json` |
| `chat.py` | Lists models, sends one chat completion and one streamed completion |
| `teardown.py` | Deletes the endpoint, then the template |
| `common.py` | `.env` loading, REST calls, the state file |
| `requirements.txt` | `openai~=3.46` — the control plane is standard library |

### Step 1 — Setup

```bash
cd serverless/03-vllm-endpoint
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

`RUNPOD_API_KEY` comes from the repo `.env`.

### Step 2 — Deploy

```bash
.venv/bin/python deploy.py --dry-run   # prints both request bodies
.venv/bin/python deploy.py
```

The template carries the model as environment variables — `MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct`, `MAX_MODEL_LEN=4096` — which is all [worker-vllm](https://github.com/runpod-workers/worker-vllm/tree/v2.30.2) needs. The endpoint lists three GPU types in order: RTX 4090, RTX A5000, RTX A4500. Field names are from the published [OpenAPI spec](https://rest.runpod.io/v1/openapi.json).

### Step 3 — Call it

```bash
.venv/bin/python chat.py
```

```python
client = OpenAI(
    base_url=f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1",
    api_key=RUNPOD_API_KEY,
)
client.chat.completions.create(model="Qwen/Qwen2.5-1.5B-Instruct", messages=[...])
```

Output once a worker was up (2026-11-05, RTX 4090, US-NC-1):

```
models  ['Qwen/Qwen2.5-1.5B-Instruct']  (479.8s — includes any cold start)

chat    (1.6s, 40+20 tokens)
        A serverless GPU allows users to access powerful GPUs without the need for managing servers or infrastructure.

stream  1 2 3 4 5 6 7 8 9 10
        first token 0.76s, total 0.76s
```

### Step 4 — Tear down

```bash
.venv/bin/python teardown.py
```

The endpoint goes at once. The template may not: the API refused with *"Template is still held by deleted endpoint …, which is pending cleanup. It can be deleted once that endpoint's last worker has been billed, within about 90 minutes of the endpoint delete."* `teardown.py` keeps the template id in `.endpoint.json` and says so; an unused template costs nothing. Rerun it later: on 2026-11-05 the template was still refused 86 minutes after the endpoint delete and deleted at 116.

### The first cold start took 15 minutes

From `deploy.py` to the first answer. The serving worker's log splits it (UTC):

| Time | Event | Elapsed |
|---|---|---|
| 06:33:36 | Endpoint created | — |
| 06:33:40 | `loading container image from cache` | |
| 06:37:32 | `worker is ready` | 3 min 52 s image load |
| 06:47:46 | `create container` | **10 min 14 s with nothing logged** |
| 06:48:33 | Weights downloaded | 9.6 s for the 1.5B model |
| 06:48:54–06:49:00 | CUDA graph capture, two passes | 3 s + 4 s |
| 06:49:03 | `vLLM is healthy` | 77 s after `create container` |
| 06:49:07 | Queued requests answered | |

vLLM itself took 77 seconds. The other 14 minutes were the platform: loading an image it already had cached, then a worker that reported ready and created no container. [Inference characterization](../../inference-characterization/FINDINGS.md) saw the same gap at up to 56 s (C18) and cold waits of 150–383 s (C9) with a 7B model; this run's gap was ten times longer with a model five times smaller. One run — the cause is not established.

**The first request failed with HTTP 520** after 7 min 12 s. The OpenAI route is synchronous; the job stayed in the queue (`inQueue: 1` on `/health`) and a second request was answered when the container came up. `chat.py` now retries server errors up to three times.

Also seen:

- **Three workers with `workersMax` 1.** The worker list held three RTX 4090 workers in US-NC-1; one served, one stayed idle with no container, one was initializing. C24 saw five under `workersMax` 3.
- **`/health` said `ready: 1` while nothing could serve.** Around 06:41 it reported one idle, ready worker; the container that answered was created seven minutes later.
- **The compile cache goes to `/runpod-volume/vllm-cache`** even with no network volume attached, so every new container compiles again (13.3 s here).
- **The worker logs `unauthenticated requests to the HF Hub`.** Public model, no harm; a gated one needs `HF_TOKEN`.

### What was run

2026-11-05, `runpod/worker-v1-vllm:v2.30.2` (vLLM 0.32.0, Runpod worker SDK 1.12.0), `Qwen/Qwen2.5-1.5B-Instruct`, `MAX_MODEL_LEN` 4096, RTX 4090 in US-NC-1, FlashBoot on, idle timeout 5 s.

| Step | Result |
|---|---|
| `deploy.py --dry-run` | Prints both bodies, creates nothing |
| `deploy.py` | Template and endpoint created |
| `chat.py`, first run | HTTP 520 after 7 min 12 s (cold) |
| `chat.py`, second run | `models` after 480 s, then chat 1.6 s, stream first token 0.76 s |
| Worker log | KV cache 657,200 tokens; graph capture 3 + 4 s; weights 9.6 s download, 0.39 s load |
| `teardown.py` | Endpoint deleted; template refused until about two hours later — still refused at 86 min, deleted at 116 min (handled) |

Not run: a second cold start, FlashBoot off, concurrency or throughput, the Responses and Anthropic Messages routes. The billing API returned no rows for the run's hour when queried right after it.

---

## 한국어

**목표:** Runpod 이 미리 빌드한 vLLM 워커로 모델을 서빙하고, OpenAI SDK 에서 `base_url` 과 `api_key` 만 바꿔 호출합니다.

**소요 시간:** 약 20분, 대부분 첫 콜드 스타트 · **비용:** 워커가 도는 동안의 GPU 초. 유휴 상태에서는 없음

### Lab 02 와 다른 점

| | Lab 02 | Lab 03 |
|---|---|---|
| 워커 코드 | 직접 쓴 `handler.py`, GitHub 에서 빌드 | 없음 — Docker Hub 의 `runpod/worker-v1-vllm:v2.30.2` |
| 배포 | 콘솔 (GitHub 빌드는 콘솔 전용) | `deploy.py`, REST API |
| 클라이언트 | Runpod 작업 형식의 `runsync` | `/openai/v1` 에 OpenAI SDK |
| 서빙 | transformers, 한 번에 요청 하나 | vLLM, continuous batching |

### 파일 구성

| 파일 | 역할 |
|---|---|
| `deploy.py` | 템플릿과 엔드포인트 생성 (워커 0–1, 유휴 5초, FlashBoot 켬). id 를 `.endpoint.json` 에 기록 |
| `chat.py` | 모델 목록, 채팅 1회, 스트리밍 1회 |
| `teardown.py` | 엔드포인트 삭제 후 템플릿 삭제 |
| `common.py` | `.env` 로딩, REST 호출, 상태 파일 |
| `requirements.txt` | `openai~=3.46` — 제어 쪽은 표준 라이브러리만 사용 |

### 1단계 — 준비

```bash
cd serverless/03-vllm-endpoint
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

`RUNPOD_API_KEY` 는 저장소 `.env` 에서 읽습니다.

### 2단계 — 배포

```bash
.venv/bin/python deploy.py --dry-run   # 요청 본문 두 개를 출력
.venv/bin/python deploy.py
```

템플릿은 모델을 환경변수로 전달합니다. `MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct`, `MAX_MODEL_LEN=4096`. [worker-vllm](https://github.com/runpod-workers/worker-vllm/tree/v2.30.2) 에 필요한 것은 이것뿐입니다. 엔드포인트에는 GPU 를 RTX 4090, RTX A5000, RTX A4500 순으로 지정합니다. 필드 이름은 발행된 [OpenAPI 스펙](https://rest.runpod.io/v1/openapi.json) 기준입니다.

### 3단계 — 호출

```bash
.venv/bin/python chat.py
```

```python
client = OpenAI(
    base_url=f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1",
    api_key=RUNPOD_API_KEY,
)
client.chat.completions.create(model="Qwen/Qwen2.5-1.5B-Instruct", messages=[...])
```

워커가 뜬 뒤의 출력 (2026-11-05, RTX 4090, US-NC-1):

```
models  ['Qwen/Qwen2.5-1.5B-Instruct']  (479.8s — includes any cold start)

chat    (1.6s, 40+20 tokens)
        A serverless GPU allows users to access powerful GPUs without the need for managing servers or infrastructure.

stream  1 2 3 4 5 6 7 8 9 10
        first token 0.76s, total 0.76s
```

### 4단계 — 정리

```bash
.venv/bin/python teardown.py
```

엔드포인트는 바로 지워집니다. 템플릿은 아닐 수 있습니다. API 가 *"Template is still held by deleted endpoint …, which is pending cleanup. It can be deleted once that endpoint's last worker has been billed, within about 90 minutes of the endpoint delete."* 로 거부했습니다. `teardown.py` 는 템플릿 id 를 `.endpoint.json` 에 남기고 그렇게 안내합니다. 쓰지 않는 템플릿은 비용이 없으니 나중에 다시 실행하세요.

### 첫 콜드 스타트는 15분이었습니다

`deploy.py` 부터 첫 응답까지입니다. 응답한 워커의 로그로 나누면 다음과 같습니다 (UTC).

| 시각 | 이벤트 | 경과 |
|---|---|---|
| 06:33:36 | 엔드포인트 생성 | — |
| 06:33:40 | `loading container image from cache` | |
| 06:37:32 | `worker is ready` | 이미지 로딩 3분 52초 |
| 06:47:46 | `create container` | **아무 로그 없이 10분 14초** |
| 06:48:33 | 가중치 다운로드 완료 | 1.5B 모델에 9.6초 |
| 06:48:54–06:49:00 | CUDA 그래프 캡처 2회 | 3초 + 4초 |
| 06:49:03 | `vLLM is healthy` | `create container` 후 77초 |
| 06:49:07 | 대기 중이던 요청 응답 | |

vLLM 자체는 77초였습니다. 나머지 14분은 플랫폼 쪽입니다. 이미 캐시에 있던 이미지를 로딩하는 데 4분, 준비됐다고 보고한 워커가 컨테이너를 만들지 않은 채 10분. [Inference characterization](../../inference-characterization/FINDINGS.md) 에서는 같은 공백이 최대 56초 (C18), 7B 모델의 콜드 대기가 150–383초 (C9) 였습니다. 이번에는 모델이 5분의 1 크기인데 공백은 10배 길었습니다. 한 번의 실행이므로 원인은 확정하지 않았습니다.

**첫 요청은 7분 12초 만에 HTTP 520 으로 실패했습니다.** OpenAI 경로는 동기식입니다. 작업은 큐에 남았고 (`/health` 의 `inQueue: 1`), 두 번째 요청은 컨테이너가 뜬 뒤 응답됐습니다. `chat.py` 는 이제 서버 오류를 최대 세 번 재시도합니다.

그 밖에 본 것:

- **`workersMax` 1 인데 워커가 세 개.** 워커 목록에 US-NC-1 의 RTX 4090 워커가 셋 있었습니다. 하나가 응답했고, 하나는 컨테이너 없이 유휴, 하나는 초기화 중이었습니다. C24 에서는 `workersMax` 3 에 다섯 개였습니다.
- **`/health` 가 `ready: 1` 인데 응답할 수 있는 것이 없었습니다.** 06:41 무렵 유휴·준비 워커 하나를 보고했지만, 응답한 컨테이너는 7분 뒤에 만들어졌습니다.
- **컴파일 캐시가 `/runpod-volume/vllm-cache` 로 갑니다.** 네트워크 볼륨이 없어도 그렇습니다. 그래서 새 컨테이너마다 다시 컴파일합니다 (여기서는 13.3초).
- **워커가 `unauthenticated requests to the HF Hub` 를 기록합니다.** 공개 모델이라 문제는 없고, gated 모델에는 `HF_TOKEN` 이 필요합니다.

### 실행 내역

2026-11-05, `runpod/worker-v1-vllm:v2.30.2` (vLLM 0.32.0, Runpod 워커 SDK 1.12.0), `Qwen/Qwen2.5-1.5B-Instruct`, `MAX_MODEL_LEN` 4096, US-NC-1 의 RTX 4090, FlashBoot 켬, 유휴 타임아웃 5초.

| 단계 | 결과 |
|---|---|
| `deploy.py --dry-run` | 본문 두 개 출력, 생성 없음 |
| `deploy.py` | 템플릿과 엔드포인트 생성 |
| `chat.py` 첫 실행 | 7분 12초 후 HTTP 520 (콜드) |
| `chat.py` 두 번째 실행 | `models` 480초, 이어서 채팅 1.6초, 스트리밍 첫 토큰 0.76초 |
| 워커 로그 | KV 캐시 657,200 토큰. 그래프 캡처 3 + 4초. 가중치 다운로드 9.6초, 로드 0.39초 |
| `teardown.py` | 엔드포인트 삭제. 템플릿은 약 2시간 뒤까지 거부 — 86분에 여전히 거부, 116분에 삭제 (처리함) |

실행하지 않은 것: 두 번째 콜드 스타트, FlashBoot 끔, 동시성·처리량, Responses 와 Anthropic Messages 경로. 실행 직후 조회한 결제 API 는 해당 시간대에 아무 행도 돌려주지 않았습니다.
