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
| [02-llm-chat](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat) | Ready | Small instruct model from GitHub, weights from Runpod's cached-model store |
| 03-vllm-endpoint | Planned | Higher-throughput serving with `worker-vllm` |

### Where the model lives

The subject of Lab 02, and the thing hello-world cannot teach. Three options:

| Where | Cold start | Image size | Download billed? |
|---|---|---|---|
| Downloaded at runtime | Slow, every new worker | Small | **Yes** |
| Baked into the image | Fast | Huge | No, but builds and pulls are slow |
| **Runpod cached model** | Seconds | Small | **No** |

Put a Hugging Face ID in the endpoint's **Model** field and Runpod caches the weights on the host at `/runpod-volume/huggingface-cache/hub`, shared across workers there. Code stays in Git, weights stay out of it — the two compose rather than compete.

<div class="warn" markdown="1">
The handler has to be written for it. `HF_HUB_OFFLINE` is read when `huggingface_hub` is imported, so setting it after importing `transformers` silently does nothing — and you would be downloading on the clock while believing you were serving from cache.
</div>

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
docker build --platform linux/amd64 -t <user>/hello-worker:v1.0.0 .
```

<div class="warn" markdown="1">
`--platform linux/amd64` is mandatory on Apple Silicon. Runpod workers are amd64, and an arm64 image fails to start with no useful log output.

Avoid `:latest`. Runpod caches images, so a mutable tag can leave workers serving the previous build with no obvious sign.
</div>

### Deploying from GitHub

Runpod can clone the repo, build the image itself and host it in its own registry — no Docker Hub account and no emulated builds. For this repo, set **Dockerfile Path** to `/serverless/01-hello-worker/Dockerfile`, since each lab lives in its own directory.

<div class="warn" markdown="1">
**Set the Build context, and save it before triggering a build.** Runpod defaults the context to the repo root and the main form only asks for a Dockerfile path, so `COPY handler.py .` fails with `"/handler.py": not found`. The failed build log shows the context as the last positional argument:

```
docker buildx build --file /app/<id>/temp/serverless/01-hello-worker/Dockerfile \
                    /app/<id>/temp          <- context
```

**Advanced settings → Build context** = `/serverless/01-hello-worker` fixes it — verified by a successful build. The trap is ordering: a build kicked off by a `git push` while the save is still in flight uses the old config and fails identically, which makes the field look broken.

This keeps each lab self-contained, matching Runpod's own repos — `runpod-workers/*` put one worker per repo with the Dockerfile at the root, and the `runpod/containers` monorepo sets `context = "official-templates/<name>"` per bake target. Nothing in the org uses root-relative `COPY` paths.
</div>

<div class="note" markdown="1">
**Redeploy: docs and observation disagree.** The docs say changes "won't automatically be pushed to your endpoint" and that a **GitHub release** is required. In testing, two plain pushes each triggered a build — but only on an endpoint that had no successful build yet. Treat the release as the reliable trigger. Earlier builds can be rolled back from the Builds tab.

Two console warnings are worth knowing: *"Could not find runpod.serverless.start() in your repo"* can be a false negative on a new repository, because the check relies on GitHub's code search index, which lags. The Dockerfile-found check is the one that actually gates deployment.
</div>

### Measured on a live endpoint

Lab 01 deployed from GitHub, CPU workers, `workers_min = 0`:

| Request | `delayTime` | `executionTime` |
|---|---|---|
| First (cold) | 3,704 ms | 222 ms |
| Warm | 776–806 ms | 194–217 ms |

`delayTime` is queue plus worker startup, `executionTime` is the handler. The handler is a rounding error — almost all of the first request is cold start, which is exactly what `workers_min = 0` buys you in cost and pays for in latency.

<div class="warn" markdown="1">
**`{"input": {}}` never returns.** An empty input object hung for 90 seconds with a zero-byte response and `retries: 1`, reproducibly. It is not a handler bug — `{"input": {"other": 1}}` takes the identical default path and returns immediately. Always send at least one key.

**`/runsync` can return `IN_PROGRESS`.** It is not guaranteed to return `COMPLETED` with an `output`; be ready to poll `/status/{id}`.
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
| [02-llm-chat](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat) | 준비됨 | GitHub 연동으로 소형 instruct 모델 배포, 가중치는 Runpod 모델 캐시 |
| 03-vllm-endpoint | 계획됨 | `worker-vllm` 으로 고처리량 서빙 |

### 모델은 어디에 두는가

Lab 02 의 주제이자 hello-world 로는 가르칠 수 없는 부분입니다. 선택지는 셋입니다.

| 위치 | 콜드 스타트 | 이미지 크기 | 다운로드 과금 |
|---|---|---|---|
| 런타임 다운로드 | 느림, 새 워커마다 | 작음 | **있음** |
| 이미지에 굽기 | 빠름 | 매우 큼 | 없음, 대신 빌드·pull 이 느림 |
| **Runpod 모델 캐시** | 수 초 | 작음 | **없음** |

엔드포인트의 **Model** 필드에 Hugging Face ID 를 넣으면 Runpod 이 호스트의 `/runpod-volume/huggingface-cache/hub` 에 가중치를 캐시하고 그 호스트의 워커들이 공유합니다. 코드는 Git 에, 가중치는 Git 밖에 — 둘은 경쟁 관계가 아니라 함께 쓰는 관계입니다.

<div class="warn" markdown="1">
핸들러를 여기에 맞춰 작성해야 합니다. `HF_HUB_OFFLINE` 는 `huggingface_hub` 가 import 될 때 읽히므로, `transformers` 를 import 한 뒤에 설정하면 아무 효과 없이 무시됩니다. 캐시에서 서빙한다고 믿는 동안 실제로는 과금되며 다운로드하게 됩니다.
</div>

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
docker build --platform linux/amd64 -t <사용자>/hello-worker:v1.0.0 .
```

<div class="warn" markdown="1">
Apple Silicon 에서는 `--platform linux/amd64` 가 필수입니다. Runpod 워커는 amd64 이며, arm64 이미지는 쓸만한 로그도 없이 기동에 실패합니다.

`:latest` 는 피하세요. Runpod 이 이미지를 캐시하므로, 가변 태그를 쓰면 워커가 이전 빌드를 계속 서빙하면서도 겉으로는 표시가 나지 않을 수 있습니다.
</div>

### GitHub 연동 배포

Runpod 이 저장소를 클론해 직접 이미지를 빌드하고 자체 레지스트리에 보관합니다. Docker Hub 계정도, 에뮬레이션 빌드도 필요 없습니다. 이 저장소는 실습마다 디렉토리가 나뉘므로 **Dockerfile Path** 를 `/serverless/01-hello-worker/Dockerfile` 로 지정하세요.

<div class="warn" markdown="1">
**Build context 를 지정하고, 빌드 트리거 전에 저장하세요.** Runpod 은 컨텍스트 기본값이 저장소 루트이고 기본 화면에서는 Dockerfile 경로만 묻기 때문에, `COPY handler.py .` 가 `"/handler.py": not found` 로 실패합니다. 실패한 빌드 로그에서 컨텍스트가 마지막 위치 인자로 드러납니다.

```
docker buildx build --file /app/<id>/temp/serverless/01-hello-worker/Dockerfile \
                    /app/<id>/temp          <- 컨텍스트
```

**Advanced settings → Build context** 에 `/serverless/01-hello-worker` 를 넣으면 해결되며, 빌드 성공으로 확인했습니다. 함정은 순서입니다. 저장이 반영되기 전에 `git push` 로 시작된 빌드는 이전 설정을 써서 똑같이 실패하고, 필드가 고장난 것처럼 보입니다.

이렇게 하면 각 실습이 자체 완결적으로 유지되며, 이는 Runpod 자체 저장소 방식과 같습니다. `runpod-workers/*` 는 워커마다 저장소를 두고 Dockerfile 을 루트에 놓고, `runpod/containers` 모노레포는 bake 타겟마다 `context = "official-templates/<name>"` 을 지정합니다. 조직 어디에도 루트 기준 `COPY` 경로는 없습니다.
</div>

<div class="note" markdown="1">
**재배포 — 문서와 실제가 다릅니다.** 문서는 변경사항이 "won't automatically be pushed to your endpoint" 이며 **GitHub 릴리스**가 필요하다고 합니다. 그런데 실제로는 일반 푸시 두 번이 각각 빌드를 트리거했습니다. 다만 성공한 빌드가 없던 엔드포인트에서만 확인된 동작입니다. 릴리스를 확실한 트리거로 보세요. 이전 빌드는 Builds 탭에서 롤백할 수 있습니다.

콘솔 경고 두 가지를 알아두면 좋습니다. *"Could not find runpod.serverless.start() in your repo"* 는 새 저장소에서 오탐일 수 있습니다. 이 검사는 색인이 늦는 GitHub 코드 검색에 의존하기 때문입니다. 실제로 배포를 막는 것은 Dockerfile 검사 쪽입니다.
</div>

### 실제 엔드포인트 실측

GitHub 연동으로 배포한 Lab 01, CPU 워커, `workers_min = 0` 기준입니다.

| 요청 | `delayTime` | `executionTime` |
|---|---|---|
| 첫 요청 (콜드) | 3,704 ms | 222 ms |
| 워밍 후 | 776~806 ms | 194~217 ms |

`delayTime` 은 큐 대기와 워커 기동, `executionTime` 은 핸들러 실행입니다. 핸들러는 오차 수준이고 첫 요청의 대부분이 콜드 스타트입니다. `workers_min = 0` 이 비용으로 얻고 지연시간으로 치르는 것이 정확히 이것입니다.

<div class="warn" markdown="1">
**`{"input": {}}` 는 응답이 오지 않습니다.** 빈 입력 객체는 90초 동안 0바이트 응답에 `retries: 1` 이 붙은 채 멈췄고, 재현됩니다. 핸들러 버그가 아닙니다. `{"input": {"other": 1}}` 은 완전히 같은 기본값 경로를 타면서 즉시 응답합니다. 키를 최소 하나는 보내세요.

**`/runsync` 가 `IN_PROGRESS` 를 반환할 수 있습니다.** 항상 `output` 이 담긴 `COMPLETED` 가 오는 것은 아니므로 `/status/{id}` 폴링을 대비하세요.
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
