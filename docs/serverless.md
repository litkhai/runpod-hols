---
layout: default
title: Serverless
permalink: /serverless/
---

# Serverless

<div class="lang" data-lang="en" markdown="1">

## English

Runpod Serverless runs your code as an autoscaling HTTP endpoint. Workers start when a request arrives, process the job, and shut down. You are billed only for execution time.

### Labs

| Lab | Status | Contents |
|---|---|---|
| [01-hello-worker](https://github.com/litkhai/runpod-hols/tree/main/serverless/01-hello-worker) | Ready | handler → local test → Docker image → deploy |
| 02-vllm-endpoint | Planned | Serve an LLM with `worker-vllm`, OpenAI-compatible API |
| 03-network-volume | Planned | Attach a Network Volume so weights survive across workers |

### Core concepts

**Handler** — a function taking a `job` dict and returning any JSON-serializable value. `job["input"]` holds the caller's payload. `runpod.serverless.start({"handler": handler})` hands control to the SDK, which polls the job queue and invokes your handler per job.

**Cold start** — a request arriving with no warm worker must pull the image and start the container first. This is why model loading belongs at module scope, not inside the handler: module scope runs once per worker, the handler runs once per request.

**Endpoint API**

| Route | Behaviour |
|---|---|
| `POST /run` | Async — returns a job `id`, poll `/status/{id}` |
| `POST /runsync` | Sync — blocks and returns the output. Best for short jobs |
| `GET /status/{id}` | Job status and result |

Base URL is `https://api.runpod.ai/v2/{ENDPOINT_ID}`, authenticated with `Authorization: Bearer $RUNPOD_API_KEY`.

### Lab 01 in brief

```bash
cd serverless/01-hello-worker
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python handler.py                 # runs test_input.json once
.venv/bin/python handler.py --rp_serve_api  # local API on :8000
```

The local API server returns exactly the shape the deployed endpoint does:

```json
{"id":"test-1bec00ea-…","status":"COMPLETED",
 "output":{"greeting":"Hello, Kee Hoon!","worker_id":"local"}}
```

Then build — note the platform flag:

```bash
docker build --platform linux/amd64 -t <user>/hello-worker:latest .
```

<div class="warn" markdown="1">
`--platform linux/amd64` is mandatory on Apple Silicon. Runpod workers are amd64, and an arm64 image fails to start with no useful log output.
</div>

### Review of the official template

Lab 01 is based on [`runpod-workers/worker-template`](https://github.com/runpod-workers/worker-template). It is a sound scaffold, but six things were changed:

| Item | Upstream | Here | Why |
|---|---|---|---|
| SDK version | `runpod~=1.7.9` | `runpod~=1.11.0` | 1.7.9 is well behind current |
| Base image | `runpod/base:0.6.3-cuda11.8.0` | `python:3.11-slim` | No GPU work in hello-world. Slim builds to **106MB in ~3s** vs multiple GB. The official Get Started guide also uses slim |
| Handler return | `str` | `dict` | Returns `worker_id` so cold starts and scale-out are observable |
| Copy instruction | `ADD handler.py .` | `COPY handler.py .` | `ADD` has URL and archive side effects |
| `hub.json` `runsOn` | `GPU` | `CPU` | No GPU needed |
| `tests.json` | 1 test | 2 tests | Added an empty-input case for the default path |

<div class="note" markdown="1">
**Upstream documentation bug.** The template README says *"It copies your `src` directory into the image."* There is no `src/` directory — the Dockerfile does `ADD handler.py .`. Ignore that line.
</div>

[Full lab in the repo →](https://github.com/litkhai/runpod-hols/tree/main/serverless)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

Runpod Serverless 는 코드를 오토스케일 HTTP 엔드포인트로 실행합니다. 요청이 들어오면 워커가 뜨고, 작업을 처리한 뒤 내려갑니다. 과금은 실행된 시간에 대해서만 발생합니다.

### 실습 목록

| 실습 | 상태 | 내용 |
|---|---|---|
| [01-hello-worker](https://github.com/litkhai/runpod-hols/tree/main/serverless/01-hello-worker) | 준비됨 | handler → 로컬 테스트 → Docker 이미지 → 배포 |
| 02-vllm-endpoint | 계획됨 | `worker-vllm` 으로 LLM 서빙, OpenAI 호환 API |
| 03-network-volume | 계획됨 | Network Volume 을 붙여 가중치를 워커 간 공유 |

### 핵심 개념

**Handler** — `job` 딕셔너리를 받아 JSON 직렬화 가능한 값을 반환하는 함수입니다. 호출자의 payload 는 `job["input"]` 에 들어옵니다. `runpod.serverless.start({"handler": handler})` 를 호출하면 SDK 가 제어권을 가져가 작업 큐를 폴링하며 작업마다 handler 를 실행합니다.

**콜드 스타트** — 워밍된 워커가 없을 때 들어온 요청은 이미지를 받고 컨테이너를 띄우는 시간을 먼저 거칩니다. 모델 로딩을 handler 안이 아니라 모듈 스코프에 둬야 하는 이유입니다. 모듈 스코프는 워커당 1회, handler 는 요청당 1회 실행됩니다.

**엔드포인트 API**

| 경로 | 동작 |
|---|---|
| `POST /run` | 비동기 — 작업 `id` 반환, `/status/{id}` 로 폴링 |
| `POST /runsync` | 동기 — 완료까지 대기 후 결과 반환. 짧은 작업에 적합 |
| `GET /status/{id}` | 작업 상태 및 결과 |

기본 URL 은 `https://api.runpod.ai/v2/{ENDPOINT_ID}` 이며 `Authorization: Bearer $RUNPOD_API_KEY` 로 인증합니다.

### Lab 01 요약

```bash
cd serverless/01-hello-worker
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python handler.py                 # test_input.json 1회 실행
.venv/bin/python handler.py --rp_serve_api  # :8000 로컬 API
```

로컬 API 서버는 배포된 엔드포인트와 완전히 동일한 형태를 반환합니다.

```json
{"id":"test-1bec00ea-…","status":"COMPLETED",
 "output":{"greeting":"Hello, Kee Hoon!","worker_id":"local"}}
```

이후 빌드합니다. platform 플래그에 주의하세요.

```bash
docker build --platform linux/amd64 -t <사용자>/hello-worker:latest .
```

<div class="warn" markdown="1">
Apple Silicon 에서는 `--platform linux/amd64` 가 필수입니다. Runpod 워커는 amd64 이며, arm64 이미지는 쓸만한 로그도 없이 기동에 실패합니다.
</div>

### 공식 템플릿 검토

Lab 01 은 [`runpod-workers/worker-template`](https://github.com/runpod-workers/worker-template) 를 기반으로 합니다. 스캐폴드 자체는 견실하지만 여섯 가지를 변경했습니다.

| 항목 | 원본 | 이 저장소 | 이유 |
|---|---|---|---|
| SDK 버전 | `runpod~=1.7.9` | `runpod~=1.11.0` | 1.7.9 는 현재 릴리스보다 상당히 뒤처짐 |
| 베이스 이미지 | `runpod/base:0.6.3-cuda11.8.0` | `python:3.11-slim` | hello-world 는 GPU 연산이 없음. slim 은 **106MB, 약 3초**에 빌드되는 반면 원본은 수 GB. 공식 Get Started 가이드도 slim 사용 |
| handler 반환값 | `str` | `dict` | `worker_id` 를 반환해 콜드 스타트와 스케일아웃을 관찰 가능하게 함 |
| 복사 명령 | `ADD handler.py .` | `COPY handler.py .` | `ADD` 는 URL·압축 해제 부수효과가 있음 |
| `hub.json` 의 `runsOn` | `GPU` | `CPU` | GPU 가 필요 없음 |
| `tests.json` | 테스트 1개 | 테스트 2개 | 빈 입력 케이스를 추가해 기본값 경로 검증 |

<div class="note" markdown="1">
**원본 문서 오류.** 템플릿 README 에 *"It copies your `src` directory into the image"* 라고 적혀 있지만 `src/` 디렉토리는 없고 Dockerfile 은 `ADD handler.py .` 를 수행합니다. 해당 문장은 무시하세요.
</div>

[저장소에서 전체 실습 보기 →](https://github.com/litkhai/runpod-hols/tree/main/serverless)

</div>
