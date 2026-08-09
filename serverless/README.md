# Serverless Track

[English](#english) | [한국어](#한국어)

---

## English

Runpod Serverless runs your code as an **autoscaling HTTP endpoint**. Workers spin up when a request arrives, process the job, and spin down. You are billed only for execution time.

### 📚 Labs

| Lab | Status | Contents |
|---|---|---|
| [01-hello-worker](./01-hello-worker) | ✅ Ready | handler → local test → Docker image → endpoint deploy |
| 02-vllm-endpoint | 📋 Planned | Serve an LLM with `worker-vllm`, OpenAI-compatible API |
| 03-network-volume | 📋 Planned | Attach a Network Volume so model weights survive across workers |

### Core Concepts

**Handler** — a function taking a `job` dict and returning any JSON-serializable value. `job["input"]` holds the caller's payload. `runpod.serverless.start({"handler": handler})` hands control to the SDK, which polls the job queue and invokes your handler per job.

**Cold start** — a request arriving with no warm worker must pull the image and start the container first. This is why model loading belongs at module scope, not inside the handler: module scope runs once per worker, the handler runs once per request.

**Endpoint API** — three routes matter:

| Route | Behaviour |
|---|---|
| `POST /run` | Async. Returns a job `id` immediately; poll `/status/{id}` |
| `POST /runsync` | Sync. Blocks until done and returns the output. Best for short jobs |
| `GET /status/{id}` | Job status and result |

Base URL is `https://api.runpod.ai/v2/{ENDPOINT_ID}`, authenticated with `Authorization: Bearer $RUNPOD_API_KEY`.

**Worker counts** — Active Workers stay warm and are billed continuously; Max Workers caps scale-out. Keep Active at 0 for labs.

### 🔍 Review of the Official Reference Repo

Lab 01 is based on [`runpod-workers/worker-template`](https://github.com/runpod-workers/worker-template). Reviewed at SDK v1.11.0. The upstream template is 5 files: `handler.py`, `requirements.txt`, `Dockerfile`, `test_input.json`, and `.runpod/{hub,tests}.json`.

It is a sound scaffold, but a few things were adjusted for this lab:

| Item | Upstream | Here | Why |
|---|---|---|---|
| SDK version | `runpod~=1.7.9` | `runpod~=1.11.0` | 1.7.9 is well behind the current release |
| Base image | `runpod/base:0.6.3-cuda11.8.0` | `python:3.11-slim` | Hello-world does no GPU work. The CUDA base is multi-GB; slim builds to **106MB in ~3s**. The [official Get Started guide](https://docs.runpod.io/serverless/get-started) also uses `python:3.10-slim`. Swap to the CUDA base when you add a real model |
| Handler return | `str` | `dict` | Returns `worker_id` alongside the greeting so you can observe cold starts and scale-out |
| Copy instruction | `ADD handler.py .` | `COPY handler.py .` | `ADD` has URL/archive-extraction side effects; `COPY` is correct for a plain local file |
| `hub.json` `runsOn` | `GPU` | `CPU` | No GPU is needed, and CPU workers are cheaper to test with |
| `tests.json` | 1 test | 2 tests | Added an empty-input case to exercise the `"World"` default |

**One upstream documentation bug worth knowing:** the template README states *"It copies your `src` directory into the image."* There is no `src/` directory — the Dockerfile does `ADD handler.py .`. Ignore that line.

Also note `.runpod/hub.json` and `.runpod/tests.json` are only used when publishing to the [Runpod Hub](https://www.runpod.io/product/runpod-hub). They are harmless to keep and are included here for reference; the labs do not require publishing.

### Other Referenced Resources

| Resource | Notes |
|---|---|
| [runpod/runpod-python](https://github.com/runpod/runpod-python) | SDK. v1.11.0, `requires-python >=3.10`. Source of the `--rp_serve_api` local server |
| [Serverless Get Started](https://docs.runpod.io/serverless/get-started) | The 9-step official tutorial Lab 01 follows |
| [GitHub integration](https://docs.runpod.io/serverless/github-integration) | Runpod builds the image and hosts it in its own registry — no Docker Hub, no emulated builds on Apple Silicon. Note that redeploying requires a **GitHub release**, not just a push |
| [runpod-workers/worker-vllm](https://github.com/runpod-workers/worker-vllm) | Reference for Lab 02 |
| [runpod/containers](https://github.com/runpod/containers/tree/main/official-templates/base) | What is actually inside `runpod/base` |

---

## 한국어

Runpod Serverless 는 코드를 **오토스케일 HTTP 엔드포인트**로 실행합니다. 요청이 들어오면 워커가 뜨고, 작업을 처리한 뒤 내려갑니다. 과금은 실행된 시간에 대해서만 발생합니다.

### 📚 실습 목록

| 실습 | 상태 | 내용 |
|---|---|---|
| [01-hello-worker](./01-hello-worker) | ✅ 준비됨 | handler → 로컬 테스트 → Docker 이미지 → 엔드포인트 배포 |
| 02-vllm-endpoint | 📋 계획됨 | `worker-vllm` 으로 LLM 서빙, OpenAI 호환 API |
| 03-network-volume | 📋 계획됨 | Network Volume 을 붙여 모델 가중치를 워커 간 공유 |

### 핵심 개념

**Handler** — `job` 딕셔너리를 받아 JSON 직렬화 가능한 값을 반환하는 함수입니다. 호출자가 보낸 payload 는 `job["input"]` 에 들어옵니다. `runpod.serverless.start({"handler": handler})` 를 호출하면 SDK 가 제어권을 가져가 작업 큐를 폴링하면서 작업마다 handler 를 실행합니다.

**콜드 스타트(Cold start)** — 워밍된 워커가 없는 상태에서 요청이 들어오면 이미지를 받고 컨테이너를 띄우는 시간이 먼저 필요합니다. 모델 로딩을 handler 안이 아니라 모듈 스코프에 둬야 하는 이유가 이것입니다. 모듈 스코프는 워커당 1회, handler 는 요청당 1회 실행됩니다.

**엔드포인트 API** — 주요 경로는 세 개입니다.

| 경로 | 동작 |
|---|---|
| `POST /run` | 비동기. 즉시 작업 `id` 반환, `/status/{id}` 로 폴링 |
| `POST /runsync` | 동기. 완료까지 대기 후 결과 반환. 짧은 작업에 적합 |
| `GET /status/{id}` | 작업 상태 및 결과 조회 |

기본 URL 은 `https://api.runpod.ai/v2/{ENDPOINT_ID}` 이고, `Authorization: Bearer $RUNPOD_API_KEY` 로 인증합니다.

**워커 수 설정** — Active Worker 는 상시 워밍 상태로 유지되어 계속 과금되고, Max Worker 는 스케일아웃 상한입니다. 실습에서는 Active 를 0 으로 둡니다.

### 🔍 참조 공식 리포 검토

Lab 01 은 [`runpod-workers/worker-template`](https://github.com/runpod-workers/worker-template) 를 기반으로 합니다. SDK v1.11.0 기준으로 검토했습니다. 원본 템플릿은 `handler.py`, `requirements.txt`, `Dockerfile`, `test_input.json`, `.runpod/{hub,tests}.json` 총 5개 파일입니다.

스캐폴드 자체는 견실하지만, 이 실습에 맞게 몇 가지를 조정했습니다.

| 항목 | 원본 | 이 저장소 | 이유 |
|---|---|---|---|
| SDK 버전 | `runpod~=1.7.9` | `runpod~=1.11.0` | 1.7.9 는 현재 릴리스보다 상당히 뒤처짐 |
| 베이스 이미지 | `runpod/base:0.6.3-cuda11.8.0` | `python:3.11-slim` | hello-world 는 GPU 연산이 없음. CUDA 베이스는 수 GB 인 반면 slim 은 **106MB, 약 3초**에 빌드됨. [공식 Get Started 가이드](https://docs.runpod.io/serverless/get-started)도 `python:3.10-slim` 을 사용. 실제 모델을 올릴 때 CUDA 베이스로 교체 |
| handler 반환값 | `str` | `dict` | 인사말과 함께 `worker_id` 를 반환해 콜드 스타트와 스케일아웃을 관찰 가능하게 함 |
| 복사 명령 | `ADD handler.py .` | `COPY handler.py .` | `ADD` 는 URL 다운로드·압축 해제 부수효과가 있음. 단순 로컬 파일에는 `COPY` 가 맞음 |
| `hub.json` 의 `runsOn` | `GPU` | `CPU` | GPU 가 필요 없고 CPU 워커가 테스트 비용이 저렴함 |
| `tests.json` | 테스트 1개 | 테스트 2개 | 빈 입력 케이스를 추가해 `"World"` 기본값 경로를 검증 |

**알아둘 만한 원본 문서 오류:** 템플릿 README 에 *"It copies your `src` directory into the image"* 라고 적혀 있지만, `src/` 디렉토리는 존재하지 않고 Dockerfile 은 `ADD handler.py .` 를 수행합니다. 해당 문장은 무시하면 됩니다.

또한 `.runpod/hub.json` 과 `.runpod/tests.json` 은 [Runpod Hub](https://www.runpod.io/product/runpod-hub) 에 게시할 때만 사용됩니다. 그대로 둬도 무해하며 참고용으로 포함해 두었습니다. 실습에서 게시 과정은 필요하지 않습니다.

### 기타 참조 리소스

| 리소스 | 비고 |
|---|---|
| [runpod/runpod-python](https://github.com/runpod/runpod-python) | SDK. v1.11.0, `requires-python >=3.10`. `--rp_serve_api` 로컬 서버 제공 |
| [Serverless Get Started](https://docs.runpod.io/serverless/get-started) | Lab 01 이 따르는 9단계 공식 튜토리얼 |
| [GitHub integration](https://docs.runpod.io/serverless/github-integration) | Runpod 이 이미지를 빌드해 자체 레지스트리에 보관. Docker Hub 불필요, Apple Silicon 에뮬레이션 빌드도 회피. 단 재배포에는 단순 푸시가 아니라 **GitHub 릴리스**가 필요 |
| [runpod-workers/worker-vllm](https://github.com/runpod-workers/worker-vllm) | Lab 02 참조용 |
| [runpod/containers](https://github.com/runpod/containers/tree/main/official-templates/base) | `runpod/base` 이미지 내부 구성 |
