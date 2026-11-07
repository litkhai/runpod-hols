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
| [03-vllm-endpoint](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint) | Run 2026-11-05 | Prebuilt `worker-vllm` image deployed from a script, OpenAI SDK client |

### Where the model lives

Four options. The third is the usual answer; the fourth arrived in SDK 1.12.

| Where | Cold start | Image size | Download billed? |
|---|---|---|---|
| Downloaded at runtime | Slow, every new worker | Small | **Yes** |
| Baked into the image | Fast | Huge | No, but builds and pulls are slow |
| **Runpod cached model** | Seconds | Small | **No** |
| **`VolumeCache`** (SDK 1.12+) | Seconds after the first | Small | No — a network volume you pay for |

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

<figure class="shot"><a href="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}" alt="Endpoint Overview tab with the Quick start cURL for /runsync" loading="lazy" width="1400" height="998"></a><figcaption>Endpoint Overview (02-llm-chat): the Quick start builds the same <code>/runsync</code> call on <code>https://api.runpod.ai/v2/{ENDPOINT_ID}</code>, and the panel below shows the repo, branch and model the endpoint was built from.</figcaption></figure>

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

<figure class="shot"><a href="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}" alt="Requests tab of 01-hello-world with a COMPLETED job" loading="lazy" width="1400" height="998"></a><figcaption>The same handler deployed as 01-hello-world and called from the endpoint's Requests tab, 2026-11-07: same shape, with <code>delayTime</code> 3385 ms while a CPU worker started and <code>executionTime</code> 140 ms.</figcaption></figure>

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
**Redeploy: docs and observation disagree.** The docs say changes "won't automatically be pushed to your endpoint" and that a **GitHub release** is required. In practice every push to the connected branch triggers a build: 02-llm-chat had 24 releases by 2026-11-07, one for each merge to `main`, including merges that changed no file of the worker (screenshot below). Expect a rebuild, and a new release on the endpoint, on every merge. Earlier builds can be rolled back from the Builds tab.

*"Could not find runpod.serverless.start() in your repo"* can be a false negative on a new repository — the check relies on GitHub's code search index, which lags. Only the Dockerfile check gates deployment.
</div>

<figure class="shot"><a href="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}" alt="Releases tab of 02-llm-chat: one release per merge to main" loading="lazy" width="1400" height="998"></a><figcaption>Releases (02-llm-chat), 2026-11-07: release #24 is the merge of PR #51, which changed only <code>inference-characterization/</code> files.</figcaption></figure>

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

### Lab 02 — what the runs found

Lab 02 deploys `Qwen/Qwen2.5-1.5B-Instruct` from GitHub, with the weights in the endpoint's **Model** field. Everything below was run on 2026-10-11; [the lab README](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat#what-was-run) has the full record.

**The cache is at the docs path.** The docs and the SDK name different locations, so the handler probes both and logs a `cache_probe` line. The docs path was populated: `/runpod-volume/huggingface-cache/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa79…`. `/runpod/cache` did not exist.

| Request (RTX A5000, idle timeout 5 s, FlashBoot off) | `delayTime` | `executionTime` |
|---|---|---|
| First prompt | 12,142 ms | 1,259 ms |
| Same prompt again | 126 ms | 846 ms |
| `messages` form | 133 ms | 305 ms |

The 12 s is container start, imports, a 2.37 s model load and the SDK's fitness checks. The image was already on the host — that pull happens right after a build.

<div class="warn" markdown="1">
**A 16 GB or 24 GB pool can hand you a Blackwell GPU.** The pools include `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` slices (sm_120). A CUDA 12.6 torch stops at sm_90, so the worker logged `no kernel image is available for execution on the device`, then `Worker is unhealthy, exiting.` The same image had served fine on an RTX A5000. The fix is a CUDA 12.8 base, `pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime`, plus a minimum CUDA version of 12.8 on the endpoint so older drivers are not picked. With that base the model loaded from cache in 1.49 s on the MIG slice.
</div>

<div class="note" markdown="1">
**Pinning a MIG type needs GraphQL.** The REST API rejects the MIG type in `gpuTypeIds`. The GraphQL `saveEndpoint` mutation takes a pool plus exclusions instead — `gpuIds: "AMPERE_24,-NVIDIA RTX A5000,-NVIDIA L4,-NVIDIA GeForce RTX 3090"` left only the MIG slice.

**Worker logs do not end.** `https://api.runpod.io/v2/serverless/{endpoint}/workers/{worker}/logs` answered as a stream that never closed, so a plain `curl` hangs. Give it a client timeout, such as `curl -m 20`, and read what arrived.
</div>

**Pass `top_p` only when sampling.** With `temperature: 0` the handler runs greedy decoding, where `top_p` has no effect. transformers 5 warns about a caller-set sampling flag that greedy decoding ignores, so the first handler logged `generation flags are not valid` on every greedy request. The handler now builds `temperature` and `top_p` only when `temperature` > 0. The rebuilt worker ran a `temperature: 0` request with no such warning between `Started.` and `Finished.`

### Lab 03 — what the run found

Lab 03 deploys Runpod's prebuilt `runpod/worker-v1-vllm:v2.30.2` with `Qwen/Qwen2.5-1.5B-Instruct` from a script, and calls it with the OpenAI SDK at `https://api.runpod.ai/v2/<endpoint>/openai/v1`. Run once on 2026-11-05 on an RTX 4090, FlashBoot on; [the lab README](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint) has the full record.

| Once a worker was up | Result |
|---|---|
| `models.list()` | `['Qwen/Qwen2.5-1.5B-Instruct']` |
| Chat completion, 40+20 tokens | 1.6 s |
| Streamed completion | first token 0.76 s |

<div class="warn" markdown="1">
**The first cold start took 15 minutes, and vLLM was 77 seconds of it.** The worker log shows 3 min 52 s loading an image the host had cached, then `worker is ready` followed by 10 min 14 s with nothing logged before `create container`. The first request came back as **HTTP 520 after 7 min 12 s**; the job stayed queued and a retry was answered once the container was up. `/health` reported a ready worker during that gap, and three workers existed under `workersMax` 1. One run — the cause is not established.
</div>

<div class="note" markdown="1">
**Deleting the template can wait an hour and a half or more.** After the endpoint delete, `DELETE /templates/{id}` answered *"Template is still held by deleted endpoint …, which is pending cleanup"*. The message says *"within about 90 minutes"*; on 2026-11-05 one template was still refused at 86 minutes and deleted at 116, another deleted at 92. The lab's `teardown.py` keeps the id and asks you to rerun it.
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
| [03-vllm-endpoint](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint) | 2026-11-05 실행 | 미리 빌드된 `worker-vllm` 이미지를 스크립트로 배포, OpenAI SDK 클라이언트 |

### 모델은 어디에 두는가

선택지는 넷입니다. 보통은 세 번째가 답이고, 네 번째는 SDK 1.12 에 추가됐습니다.

| 위치 | 콜드 스타트 | 이미지 크기 | 다운로드 과금 |
|---|---|---|---|
| 런타임 다운로드 | 느림, 새 워커마다 | 작음 | **있음** |
| 이미지에 굽기 | 빠름 | 매우 큼 | 없음, 대신 빌드·pull 이 느림 |
| **Runpod 모델 캐시** | 수 초 | 작음 | **없음** |
| **`VolumeCache`** (SDK 1.12+) | 첫 회 이후 수 초 | 작음 | 없음 — 대신 네트워크 볼륨 비용 |

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

<figure class="shot"><a href="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}" alt="엔드포인트 Overview 탭과 /runsync 용 Quick start cURL" loading="lazy" width="1400" height="998"></a><figcaption>엔드포인트 Overview (02-llm-chat): Quick start 는 <code>https://api.runpod.ai/v2/{ENDPOINT_ID}</code> 에 같은 <code>/runsync</code> 호출을 만들어 주고, 아래 패널은 엔드포인트를 빌드한 저장소, 브랜치, 모델을 보여준다.</figcaption></figure>

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

<figure class="shot"><a href="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}" alt="01-hello-world 의 Requests 탭과 COMPLETED 작업" loading="lazy" width="1400" height="998"></a><figcaption>같은 핸들러를 01-hello-world 로 배포하고 엔드포인트의 Requests 탭에서 호출한 결과, 2026-11-07: 같은 모양이고, CPU 워커가 뜨는 동안 <code>delayTime</code> 3385 ms, <code>executionTime</code> 140 ms.</figcaption></figure>

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
**재배포 — 문서와 실제가 다릅니다.** 문서는 변경사항이 "won't automatically be pushed to your endpoint" 이며 **GitHub 릴리스**가 필요하다고 합니다. 실제로는 연결된 브랜치에 푸시할 때마다 빌드가 돕니다. 02-llm-chat 은 2026-11-07 까지 `main` 머지마다 하나씩 릴리스 24개가 쌓였고, 워커 파일을 하나도 바꾸지 않은 머지도 포함됩니다 (아래 캡처). 머지할 때마다 재빌드와 새 릴리스가 생긴다고 보세요. 이전 빌드는 Builds 탭에서 롤백할 수 있습니다.

*"Could not find runpod.serverless.start() in your repo"* 는 새 저장소에서 오탐일 수 있습니다. 색인이 늦는 GitHub 코드 검색에 의존하는 검사입니다. 배포를 막는 것은 Dockerfile 검사뿐입니다.
</div>

<figure class="shot"><a href="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}" alt="02-llm-chat 의 Releases 탭: main 에 머지할 때마다 릴리스 하나" loading="lazy" width="1400" height="998"></a><figcaption>Releases (02-llm-chat), 2026-11-07: 릴리스 #24 는 <code>inference-characterization/</code> 파일만 바꾼 PR #51 의 머지다.</figcaption></figure>

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

### Lab 02 — 실행에서 확인한 것

Lab 02 는 `Qwen/Qwen2.5-1.5B-Instruct` 를 GitHub 연동으로 배포하고, 가중치는 엔드포인트의 **Model** 필드로 공급합니다. 아래는 모두 2026-10-11 에 실행한 결과이며, 전체 기록은 [실습 README](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat#한국어) 에 있습니다.

**캐시는 문서에 적힌 경로에 있습니다.** 문서와 SDK 가 서로 다른 위치를 말하므로 핸들러가 둘 다 확인하고 `cache_probe` 한 줄을 로그에 남깁니다. 채워진 쪽은 문서 경로 `/runpod-volume/huggingface-cache/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa79…` 였고, `/runpod/cache` 는 존재하지 않았습니다.

| 요청 (RTX A5000, idle timeout 5초, FlashBoot 끔) | `delayTime` | `executionTime` |
|---|---|---|
| 첫 프롬프트 | 12,142 ms | 1,259 ms |
| 같은 프롬프트 재요청 | 126 ms | 846 ms |
| `messages` 형식 | 133 ms | 305 ms |

12초는 컨테이너 기동, import, 모델 로드 2.37초, SDK fitness check 를 합친 시간입니다. 이미지는 이미 호스트에 있었습니다. 빌드 직후에 pull 이 일어나기 때문입니다.

<div class="warn" markdown="1">
**16 GB, 24 GB 풀에서 Blackwell GPU 가 배정될 수 있습니다.** 이 풀에는 `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` 조각(sm_120)이 섞여 있습니다. CUDA 12.6 torch 는 sm_90 까지만 지원하므로 워커가 `no kernel image is available for execution on the device` 를 남기고 `Worker is unhealthy, exiting.` 으로 종료했습니다. 같은 이미지가 RTX A5000 에서는 정상 동작했습니다. 해결책은 CUDA 12.8 베이스 `pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime` 로 바꾸고, 엔드포인트의 최소 CUDA 버전을 12.8 로 지정해 오래된 드라이버가 선택되지 않게 하는 것입니다. 이 베이스로 MIG 조각에서 캐시로부터 1.49초 만에 모델을 올렸습니다.
</div>

<div class="note" markdown="1">
**MIG 타입 고정은 GraphQL 로 해야 합니다.** REST API 는 `gpuTypeIds` 에 MIG 타입을 넣으면 거부합니다. GraphQL `saveEndpoint` 뮤테이션은 풀과 제외 목록을 받습니다. `gpuIds: "AMPERE_24,-NVIDIA RTX A5000,-NVIDIA L4,-NVIDIA GeForce RTX 3090"` 로 MIG 조각만 남았습니다.

**워커 로그는 끝나지 않습니다.** `https://api.runpod.io/v2/serverless/{endpoint}/workers/{worker}/logs` 는 닫히지 않는 스트림으로 응답해서 일반 `curl` 은 멈춥니다. `curl -m 20` 처럼 클라이언트 타임아웃을 주고 그때까지 받은 내용을 읽으세요.
</div>

**`top_p` 는 샘플링할 때만 넘깁니다.** `temperature: 0` 이면 핸들러는 greedy 디코딩을 하고, 이때 `top_p` 는 아무 효과가 없습니다. transformers 5 는 호출자가 지정했지만 greedy 디코딩이 무시하는 샘플링 플래그에 경고를 내므로, 처음 핸들러는 greedy 요청마다 `generation flags are not valid` 를 남겼습니다. 지금 핸들러는 `temperature` > 0 일 때만 `temperature` 와 `top_p` 를 넘깁니다. 다시 빌드한 워커로 `temperature: 0` 요청을 실행했고, `Started.` 와 `Finished.` 사이에 이 경고가 없었습니다.

### Lab 03 — 실행에서 확인한 것

Lab 03 은 Runpod 이 미리 빌드한 `runpod/worker-v1-vllm:v2.30.2` 에 `Qwen/Qwen2.5-1.5B-Instruct` 를 스크립트로 배포하고, OpenAI SDK 로 `https://api.runpod.ai/v2/<endpoint>/openai/v1` 를 호출합니다. 2026-11-05 RTX 4090, FlashBoot 켬으로 한 번 실행했습니다. 전체 기록은 [실습 README](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint) 에 있습니다.

| 워커가 뜬 뒤 | 결과 |
|---|---|
| `models.list()` | `['Qwen/Qwen2.5-1.5B-Instruct']` |
| 채팅, 40+20 토큰 | 1.6초 |
| 스트리밍 | 첫 토큰 0.76초 |

<div class="warn" markdown="1">
**첫 콜드 스타트는 15분이었고, 그중 vLLM 은 77초였습니다.** 워커 로그를 보면 호스트에 캐시돼 있던 이미지 로딩에 3분 52초, 이어서 `worker is ready` 뒤 `create container` 까지 아무 로그 없이 10분 14초가 지났습니다. 첫 요청은 **7분 12초 만에 HTTP 520** 으로 돌아왔고, 작업은 큐에 남아 컨테이너가 뜬 뒤 재시도에 응답됐습니다. 그 공백 동안 `/health` 는 준비된 워커를 보고했고, `workersMax` 1 인데 워커가 셋 있었습니다. 한 번의 실행이므로 원인은 확정하지 않았습니다.
</div>

<div class="note" markdown="1">
**템플릿 삭제는 1시간 반 이상 기다려야 할 수 있습니다.** 엔드포인트를 지운 뒤 `DELETE /templates/{id}` 가 *"Template is still held by deleted endpoint …, which is pending cleanup"* 으로 응답했습니다. 메시지는 *"within about 90 minutes"* 라고 하지만, 2026-11-05 에는 한 템플릿이 86분에도 거부되다 116분에 지워졌고, 다른 하나는 92분에 지워졌습니다. 실습의 `teardown.py` 는 id 를 남기고 다시 실행하라고 안내합니다.
</div>

[저장소에서 전체 실습 보기 →](https://github.com/litkhai/runpod-hols/tree/main/serverless)

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

Runpod Serverless 将你的代码作为自动扩缩的 HTTP 端点运行。请求到达时 worker 启动，处理作业，然后关闭。只按执行时间计费。

### 实验

| 实验 | 状态 | 内容 |
|---|---|---|
| [01-hello-worker](https://github.com/litkhai/runpod-hols/tree/main/serverless/01-hello-worker) | 就绪 | handler → 本地测试 → Docker 镜像 → 部署 |
| [02-llm-chat](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat) | 就绪 | 从 GitHub 部署小型 instruct 模型，权重来自 Runpod 的缓存模型存储 |
| [03-vllm-endpoint](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint) | 2026-11-05 已运行 | 用脚本部署预构建的 `worker-vllm` 镜像，OpenAI SDK 客户端 |

### 模型放在哪里

有四种选择。通常答案是第三种；第四种是 SDK 1.12 新增的。

| 位置 | 冷启动 | 镜像大小 | 下载是否计费？ |
|---|---|---|---|
| 运行时下载 | 慢，每个新 worker 都要下载 | 小 | **是** |
| 打包进镜像 | 快 | 巨大 | 否，但构建和拉取都很慢 |
| **Runpod 缓存模型** | 几秒 | 小 | **否** |
| **`VolumeCache`**（SDK 1.12+） | 首次之后几秒 | 小 | 否——但要为 network volume 付费 |

在端点的 **Model** 字段填入 Hugging Face ID，Runpod 就会把权重缓存到主机上的 `/runpod-volume/huggingface-cache/hub`，由该主机上的 worker 共享。代码放在 Git 里，权重放在 Git 之外——两者是组合关系，而不是竞争关系。

<div class="warn" markdown="1">
handler 必须为此专门编写。`HF_HUB_OFFLINE` 在 `huggingface_hub` 被导入时读取，所以在导入 `transformers` 之后再设置它会静默失效——你以为在从缓存提供服务，实际上却在计费期间下载。
</div>

### 核心概念

**Handler**——一个接收 `job` 字典并返回任意可 JSON 序列化值的函数。`job["input"]` 中是调用方的 payload。`runpod.serverless.start({"handler": handler})` 把控制权交给 SDK，由它轮询作业队列，并为每个作业调用你的 handler。

**冷启动**——在没有热 worker 时到达的请求，必须先拉取镜像并启动容器。这就是模型加载应放在模块作用域、而不是 handler 内部的原因：模块作用域每个 worker 运行一次，handler 每个请求运行一次。

**端点 API**

| 路由 | 行为 |
|---|---|
| `POST /run` | 异步——返回作业 `id`，轮询 `/status/{id}` |
| `POST /runsync` | 同步——阻塞并返回输出。最适合短作业 |
| `GET /status/{id}` | 作业状态和结果 |

基础 URL 是 `https://api.runpod.ai/v2/{ENDPOINT_ID}`，使用 `Authorization: Bearer $RUNPOD_API_KEY` 认证。

<figure class="shot"><a href="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}" alt="端点 Overview 标签页和 /runsync 的 Quick start cURL" loading="lazy" width="1400" height="998"></a><figcaption>端点 Overview（02-llm-chat）：Quick start 在 <code>https://api.runpod.ai/v2/{ENDPOINT_ID}</code> 上生成同样的 <code>/runsync</code> 调用，下方面板显示构建该端点的仓库、分支和模型。</figcaption></figure>

### 实验 01 概要

```bash
cd serverless/01-hello-worker
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python handler.py                 # runs test_input.json once
.venv/bin/python handler.py --rp_serve_api  # local API on :8000
```

本地 API 服务器返回的形态与已部署端点完全相同：

```json
{"id":"test-1bec00ea-…","status":"COMPLETED",
 "output":{"greeting":"Hello, Kee Hoon!","worker_id":"local"}}
```

<figure class="shot"><a href="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}" alt="01-hello-world 的 Requests 标签页和一个 COMPLETED 作业" loading="lazy" width="1400" height="998"></a><figcaption>同一个 handler 部署为 01-hello-world，并在端点的 Requests 标签页调用，2026-11-07：结构相同，CPU worker 启动期间 <code>delayTime</code> 为 3385 ms，<code>executionTime</code> 为 140 ms。</figcaption></figure>

然后构建——注意 platform 标志：

```bash
docker build --platform linux/amd64 -t <user>/hello-worker:v1.0.0 .
```

<div class="warn" markdown="1">
在 Apple Silicon 上 `--platform linux/amd64` 是必需的。Runpod worker 是 amd64，arm64 镜像会启动失败，而且没有任何有用的日志输出。

避免使用 `:latest`。Runpod 会缓存镜像，可变标签可能让 worker 继续提供上一次构建的版本，而没有任何明显迹象。
</div>

### 从 GitHub 部署

Runpod 可以克隆仓库、自行构建镜像并托管在自己的镜像仓库中——不需要 Docker Hub 账号，也不需要模拟构建。对本仓库，由于每个实验都在各自的目录中，请将 **Dockerfile Path** 设为 `/serverless/01-hello-worker/Dockerfile`。

<div class="warn" markdown="1">
**设置 Build context，并在触发构建之前保存。** Runpod 默认把上下文设为仓库根目录，而主表单只询问 Dockerfile 路径，所以 `COPY handler.py .` 会以 `"/handler.py": not found` 失败。失败的构建日志中，上下文显示为最后一个位置参数：

```
docker buildx build --file /app/<id>/temp/serverless/01-hello-worker/Dockerfile \
                    /app/<id>/temp          <- context
```

**Advanced settings → Build context** = `/serverless/01-hello-worker` 即可解决——已通过一次成功的构建验证。陷阱在于顺序：在保存尚未生效时由 `git push` 触发的构建会使用旧配置，并以完全相同的方式失败，让人以为这个字段坏了。

这样每个实验都保持自包含，与 Runpod 自己的仓库一致——`runpod-workers/*` 每个 worker 一个仓库，Dockerfile 位于根目录；`runpod/containers` monorepo 则为每个 bake target 设置 `context = "official-templates/<name>"`。该组织中没有任何地方使用相对于根目录的 `COPY` 路径。
</div>

<div class="note" markdown="1">
**重新部署：文档与观察不一致。** 文档说变更 "won't automatically be pushed to your endpoint"，并且需要 **GitHub release**。实际上，每次 push 到所连接的分支都会触发构建：到 2026-11-07，02-llm-chat 已有 24 个 release，每次合并到 `main` 一个，其中包括没有改动 worker 任何文件的合并（见下图）。请预期每次合并都会重新构建并在端点上产生新的 release。之前的构建可以在 Builds 标签页中回滚。

*"Could not find runpod.serverless.start() in your repo"* 在新仓库上可能是误报——该检查依赖 GitHub 的代码搜索索引，而索引有延迟。只有 Dockerfile 检查会阻止部署。
</div>

<figure class="shot"><a href="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}" alt="02-llm-chat 的 Releases 标签页：每次合并到 main 都有一个 release" loading="lazy" width="1400" height="998"></a><figcaption>Releases（02-llm-chat），2026-11-07：release #24 是 PR #51 的合并，而它只改了 <code>inference-characterization/</code> 下的文件。</figcaption></figure>

### 在线端点实测

实验 01 从 GitHub 部署，CPU worker，`workers_min = 0`：

| 请求 | `delayTime` | `executionTime` |
|---|---|---|
| 第一次（冷） | 3,704 ms | 222 ms |
| 热 | 776–806 ms | 194–217 ms |

`delayTime` 是排队加 worker 启动，`executionTime` 是 handler。handler 的耗时可以忽略不计——第一次请求几乎全是冷启动，这正是 `workers_min = 0` 在成本上换来的、并在延迟上付出的代价。

<div class="warn" markdown="1">
**`{"input": {}}` 永远不会返回。** 空的 input 对象挂起了 90 秒，响应为零字节并带有 `retries: 1`，可稳定复现。这不是 handler 的 bug——`{"input": {"other": 1}}` 走完全相同的默认路径，却立即返回。请始终至少发送一个键。

**`/runsync` 可能返回 `IN_PROGRESS`。** 它并不保证返回带有 `output` 的 `COMPLETED`；请准备好轮询 `/status/{id}`。
</div>

### 实验 02——运行发现

实验 02 从 GitHub 部署 `Qwen/Qwen2.5-1.5B-Instruct`，权重通过端点的 **Model** 字段提供。以下全部在 2026-10-11 运行；完整记录见[实验 README](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat#what-was-run)。

**缓存位于文档所写的路径。** 文档和 SDK 给出的位置不同，所以 handler 会探测两者并记录一行 `cache_probe`。被填充的是文档路径：`/runpod-volume/huggingface-cache/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa79…`。`/runpod/cache` 不存在。

| 请求（RTX A5000，idle timeout 5 s，FlashBoot 关闭） | `delayTime` | `executionTime` |
|---|---|---|
| 第一个 prompt | 12,142 ms | 1,259 ms |
| 再次发送相同 prompt | 126 ms | 846 ms |
| `messages` 形式 | 133 ms | 305 ms |

这 12 s 包括容器启动、导入、2.37 s 的模型加载以及 SDK 的 fitness check。镜像已经在主机上——拉取发生在构建之后不久。

<div class="warn" markdown="1">
**16 GB 或 24 GB 的池可能分配给你一块 Blackwell GPU。** 这些池中包括 `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` 切片（sm_120）。CUDA 12.6 的 torch 只支持到 sm_90，因此 worker 记录了 `no kernel image is available for execution on the device`，随后 `Worker is unhealthy, exiting.`。同一镜像在 RTX A5000 上运行正常。解决方法是换成 CUDA 12.8 基础镜像 `pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime`，并在端点上把最低 CUDA 版本设为 12.8，以免选中较旧的驱动。使用该基础镜像后，模型在 MIG 切片上从缓存加载仅用 1.49 s。
</div>

<div class="note" markdown="1">
**固定 MIG 类型需要 GraphQL。** REST API 不接受 `gpuTypeIds` 中的 MIG 类型。GraphQL 的 `saveEndpoint` mutation 则接受一个池加排除项——`gpuIds: "AMPERE_24,-NVIDIA RTX A5000,-NVIDIA L4,-NVIDIA GeForce RTX 3090"` 之后只剩下 MIG 切片。

**worker 日志不会结束。** `https://api.runpod.io/v2/serverless/{endpoint}/workers/{worker}/logs` 以一个永不关闭的流响应，所以普通的 `curl` 会挂起。给它设置客户端超时，例如 `curl -m 20`，然后读取已收到的内容。
</div>

**只在采样时传入 `top_p`。** 当 `temperature: 0` 时，handler 执行贪心解码，此时 `top_p` 不起作用。transformers 5 会对调用方设置、但被贪心解码忽略的采样标志发出警告，所以最初的 handler 在每个贪心请求上都记录了 `generation flags are not valid`。现在 handler 只在 `temperature` > 0 时才构造 `temperature` 和 `top_p`。重新构建的 worker 运行了一个 `temperature: 0` 请求，在 `Started.` 和 `Finished.` 之间没有出现该警告。

### 实验 03——运行发现

实验 03 用脚本部署 Runpod 预构建的 `runpod/worker-v1-vllm:v2.30.2` 和 `Qwen/Qwen2.5-1.5B-Instruct`，并用 OpenAI SDK 通过 `https://api.runpod.ai/v2/<endpoint>/openai/v1` 调用。于 2026-11-05 在 RTX 4090 上运行一次，FlashBoot 开启；完整记录见[实验 README](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint)。

| worker 启动之后 | 结果 |
|---|---|
| `models.list()` | `['Qwen/Qwen2.5-1.5B-Instruct']` |
| 聊天补全，40+20 tokens | 1.6 s |
| 流式补全 | 首个 token 0.76 s |

<div class="warn" markdown="1">
**第一次冷启动用了 15 分钟，其中 vLLM 占 77 秒。** worker 日志显示，加载一个主机已缓存的镜像用了 3 min 52 s，然后在 `worker is ready` 之后、`create container` 之前有 10 min 14 s 没有任何日志。第一个请求**在 7 min 12 s 后返回 HTTP 520**；作业仍在队列中，容器启动后一次重试得到了响应。在这段空白期间，`/health` 报告有就绪的 worker，并且在 `workersMax` 为 1 的情况下存在三个 worker。仅运行一次——原因尚未确定。
</div>

<div class="note" markdown="1">
**删除模板可能要等一个半小时甚至更久。** 删除端点后，`DELETE /templates/{id}` 返回 *"Template is still held by deleted endpoint …, which is pending cleanup"*。消息称 *"within about 90 minutes"*；2026-11-05 当天，一个模板在 86 分钟时仍被拒绝，到 116 分钟才删除，另一个在 92 分钟删除。实验的 `teardown.py` 会保留 id 并提示你重新运行。
</div>

[在仓库中查看完整实验 →](https://github.com/litkhai/runpod-hols/tree/main/serverless)

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

Runpod Serverless は、コードをオートスケールする HTTP エンドポイントとして実行します。リクエストが届くと worker が起動し、ジョブを処理して終了します。課金は実行時間に対してのみです。

### ラボ

| ラボ | 状態 | 内容 |
|---|---|---|
| [01-hello-worker](https://github.com/litkhai/runpod-hols/tree/main/serverless/01-hello-worker) | 準備済み | handler → ローカルテスト → Docker イメージ → デプロイ |
| [02-llm-chat](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat) | 準備済み | GitHub から小型の instruct モデル、重みは Runpod のキャッシュモデルストアから |
| [03-vllm-endpoint](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint) | 2026-11-05 実行 | ビルド済みの `worker-vllm` イメージをスクリプトでデプロイ、OpenAI SDK クライアント |

### モデルをどこに置くか

選択肢は 4 つです。普通は 3 つ目が答えで、4 つ目は SDK 1.12 で追加されました。

| 場所 | コールドスタート | イメージサイズ | ダウンロードは課金されるか |
|---|---|---|---|
| 実行時にダウンロード | 遅い、新しい worker ごと | 小さい | **される** |
| イメージに焼き込む | 速い | 巨大 | されないが、ビルドと pull が遅い |
| **Runpod キャッシュモデル** | 数秒 | 小さい | **されない** |
| **`VolumeCache`**（SDK 1.12+） | 初回以降は数秒 | 小さい | されない。代わりに network volume の料金がかかる |

エンドポイントの **Model** フィールドに Hugging Face ID を入れると、Runpod がホストの `/runpod-volume/huggingface-cache/hub` に重みをキャッシュし、そのホスト上の worker で共有します。コードは Git に、重みは Git の外に。両者は競合ではなく組み合わせる関係です。

<div class="warn" markdown="1">
handler はこれに合わせて書く必要があります。`HF_HUB_OFFLINE` は `huggingface_hub` が import されたときに読まれるので、`transformers` を import した後に設定しても黙って無視されます。キャッシュから配信しているつもりで、実際には課金されながらダウンロードしていることになります。
</div>

### 中核となる概念

**Handler**：`job` 辞書を受け取り、JSON シリアライズ可能な任意の値を返す関数です。`job["input"]` に呼び出し側の payload が入ります。`runpod.serverless.start({"handler": handler})` で制御を SDK に渡すと、SDK がジョブキューをポーリングし、ジョブごとに handler を呼び出します。

**コールドスタート**：ウォームな worker がないときに届いたリクエストは、まずイメージを pull してコンテナを起動しなければなりません。モデルのロードを handler の中ではなくモジュールスコープに置くべき理由がこれです。モジュールスコープは worker ごとに 1 回、handler はリクエストごとに 1 回実行されます。

**エンドポイント API**

| ルート | 動作 |
|---|---|
| `POST /run` | 非同期。ジョブ `id` を返すので `/status/{id}` をポーリング |
| `POST /runsync` | 同期。ブロックして出力を返す。短いジョブに最適 |
| `GET /status/{id}` | ジョブの状態と結果 |

ベース URL は `https://api.runpod.ai/v2/{ENDPOINT_ID}` で、`Authorization: Bearer $RUNPOD_API_KEY` で認証します。

<figure class="shot"><a href="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/endpoint-quick-start.webp' | relative_url }}" alt="エンドポイントの Overview タブと /runsync の Quick start cURL" loading="lazy" width="1400" height="998"></a><figcaption>エンドポイントの Overview（02-llm-chat）：Quick start は <code>https://api.runpod.ai/v2/{ENDPOINT_ID}</code> に同じ <code>/runsync</code> 呼び出しを組み立て、下のパネルはエンドポイントのビルド元のリポジトリ、ブランチ、モデルを示します。</figcaption></figure>

### Lab 01 の概要

```bash
cd serverless/01-hello-worker
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python handler.py                 # runs test_input.json once
.venv/bin/python handler.py --rp_serve_api  # local API on :8000
```

ローカル API サーバーは、デプロイ済みエンドポイントとまったく同じ形を返します。

```json
{"id":"test-1bec00ea-…","status":"COMPLETED",
 "output":{"greeting":"Hello, Kee Hoon!","worker_id":"local"}}
```

<figure class="shot"><a href="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/hello-world-request.webp' | relative_url }}" alt="01-hello-world の Requests タブと COMPLETED のジョブ" loading="lazy" width="1400" height="998"></a><figcaption>同じハンドラーを 01-hello-world としてデプロイし、エンドポイントの Requests タブから呼んだ結果、2026-11-07：同じ形で、CPU ワーカーの起動中に <code>delayTime</code> 3385 ms、<code>executionTime</code> 140 ms。</figcaption></figure>

続いてビルドします。platform フラグに注意してください。

```bash
docker build --platform linux/amd64 -t <user>/hello-worker:v1.0.0 .
```

<div class="warn" markdown="1">
Apple Silicon では `--platform linux/amd64` が必須です。Runpod の worker は amd64 で、arm64 イメージは役に立つログを何も出さずに起動に失敗します。

`:latest` は避けてください。Runpod はイメージをキャッシュするので、可変タグだと worker が前のビルドを配信し続けても、目に見える兆候がないことがあります。
</div>

### GitHub からのデプロイ

Runpod はリポジトリをクローンし、自分でイメージをビルドして自社のレジストリにホストできます。Docker Hub アカウントもエミュレーションビルドも不要です。このリポジトリではラボごとにディレクトリが分かれているので、**Dockerfile Path** を `/serverless/01-hello-worker/Dockerfile` に設定します。

<div class="warn" markdown="1">
**Build context を設定し、ビルドをトリガーする前に保存してください。** Runpod はコンテキストのデフォルトをリポジトリのルートにしており、メインのフォームは Dockerfile のパスしか尋ねないため、`COPY handler.py .` が `"/handler.py": not found` で失敗します。失敗したビルドログでは、コンテキストが最後の位置引数として現れます。

```
docker buildx build --file /app/<id>/temp/serverless/01-hello-worker/Dockerfile \
                    /app/<id>/temp          <- context
```

**Advanced settings → Build context** = `/serverless/01-hello-worker` で解決します。ビルドの成功で確認済みです。落とし穴は順序です。保存がまだ反映されていないうちに `git push` で始まったビルドは古い設定を使ってまったく同じように失敗するので、フィールドが壊れているように見えます。

こうすると各ラボが自己完結し、Runpod 自身のリポジトリと同じ形になります。`runpod-workers/*` は worker ごとに 1 リポジトリで Dockerfile をルートに置き、`runpod/containers` モノレポは bake ターゲットごとに `context = "official-templates/<name>"` を設定しています。組織内にルート基準の `COPY` パスを使っているものはありません。
</div>

<div class="note" markdown="1">
**再デプロイ：ドキュメントと観察が食い違います。** ドキュメントは変更が "won't automatically be pushed to your endpoint" であり、**GitHub release** が必要だとしています。実際には、接続したブランチへの push のたびにビルドが走ります。02-llm-chat には 2026-11-07 までに `main` へのマージごとに 1 つずつ、計 24 のリリースがあり、ワーカーのファイルを 1 つも変えていないマージも含まれます（下のスクリーンショット）。マージのたびに再ビルドと新しいリリースが起きると考えてください。以前のビルドは Builds タブからロールバックできます。

*"Could not find runpod.serverless.start() in your repo"* は、新しいリポジトリでは誤検知のことがあります。このチェックは GitHub のコード検索インデックスに依存しており、インデックスは遅れるためです。デプロイを止めるのは Dockerfile のチェックだけです。
</div>

<figure class="shot"><a href="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}"><img src="{{ '/assets/img/serverless/github-releases.webp' | relative_url }}" alt="02-llm-chat の Releases タブ：main へのマージごとに 1 リリース" loading="lazy" width="1400" height="998"></a><figcaption>Releases（02-llm-chat）、2026-11-07：リリース #24 は <code>inference-characterization/</code> のファイルしか変えていない PR #51 のマージです。</figcaption></figure>

### 稼働中のエンドポイントでの実測

GitHub からデプロイした Lab 01、CPU worker、`workers_min = 0`：

| リクエスト | `delayTime` | `executionTime` |
|---|---|---|
| 初回（コールド） | 3,704 ms | 222 ms |
| ウォーム | 776–806 ms | 194–217 ms |

`delayTime` はキュー待ちと worker の起動、`executionTime` は handler です。handler は誤差程度で、初回リクエストのほぼすべてがコールドスタートです。これこそ `workers_min = 0` がコスト面で得て、レイテンシ面で支払うものです。

<div class="warn" markdown="1">
**`{"input": {}}` は返ってきません。** 空の input オブジェクトは、0 バイトのレスポンスと `retries: 1` のまま 90 秒間止まり、再現性があります。handler のバグではありません。`{"input": {"other": 1}}` はまったく同じデフォルトの経路を通り、すぐに返ります。必ず少なくとも 1 つのキーを送ってください。

**`/runsync` は `IN_PROGRESS` を返すことがあります。** `output` 付きの `COMPLETED` が返る保証はないので、`/status/{id}` をポーリングできるようにしておいてください。
</div>

### Lab 02：実行でわかったこと

Lab 02 は `Qwen/Qwen2.5-1.5B-Instruct` を GitHub からデプロイし、重みはエンドポイントの **Model** フィールドで渡します。以下はすべて 2026-10-11 に実行したもので、完全な記録は[ラボの README](https://github.com/litkhai/runpod-hols/tree/main/serverless/02-llm-chat#what-was-run) にあります。

**キャッシュはドキュメントに書かれたパスにあります。** ドキュメントと SDK が別の場所を挙げているため、handler は両方を調べて `cache_probe` の行をログに出します。中身があったのはドキュメントのパス `/runpod-volume/huggingface-cache/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa79…` でした。`/runpod/cache` は存在しませんでした。

| リクエスト（RTX A5000、idle timeout 5 s、FlashBoot オフ） | `delayTime` | `executionTime` |
|---|---|---|
| 最初のプロンプト | 12,142 ms | 1,259 ms |
| 同じプロンプトをもう一度 | 126 ms | 846 ms |
| `messages` 形式 | 133 ms | 305 ms |

12 s はコンテナの起動、import、2.37 s のモデルロード、SDK の fitness check を合わせたものです。イメージはすでにホスト上にありました。pull はビルドの直後に行われます。

<div class="warn" markdown="1">
**16 GB や 24 GB のプールで Blackwell GPU が割り当てられることがあります。** これらのプールには `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` のスライス（sm_120）が含まれます。CUDA 12.6 の torch は sm_90 までなので、worker は `no kernel image is available for execution on the device` を出し、続いて `Worker is unhealthy, exiting.` となりました。同じイメージは RTX A5000 では問題なく動いていました。対処は CUDA 12.8 ベースの `pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime` にし、さらにエンドポイントの最小 CUDA バージョンを 12.8 にして古いドライバが選ばれないようにすることです。このベースで、MIG スライス上でモデルがキャッシュから 1.49 s でロードされました。
</div>

<div class="note" markdown="1">
**MIG タイプの固定には GraphQL が必要です。** REST API は `gpuTypeIds` に MIG タイプを入れると拒否します。GraphQL の `saveEndpoint` ミューテーションは、代わりにプールと除外リストを受け取ります。`gpuIds: "AMPERE_24,-NVIDIA RTX A5000,-NVIDIA L4,-NVIDIA GeForce RTX 3090"` で MIG スライスだけが残りました。

**worker のログは終わりません。** `https://api.runpod.io/v2/serverless/{endpoint}/workers/{worker}/logs` は閉じないストリームとして応答するため、素の `curl` は止まったままになります。`curl -m 20` のようにクライアント側のタイムアウトを付け、届いた分を読んでください。
</div>

**`top_p` はサンプリングするときだけ渡します。** `temperature: 0` では handler は greedy デコーディングを行い、このとき `top_p` は効果がありません。transformers 5 は、呼び出し側が設定したが greedy デコーディングでは無視されるサンプリングフラグに警告を出すため、最初の handler は greedy リクエストのたびに `generation flags are not valid` をログに出していました。現在の handler は `temperature` > 0 のときだけ `temperature` と `top_p` を組み立てます。再ビルドした worker で `temperature: 0` のリクエストを実行したところ、`Started.` と `Finished.` の間にこの警告は出ませんでした。

### Lab 03：実行でわかったこと

Lab 03 は Runpod のビルド済み `runpod/worker-v1-vllm:v2.30.2` と `Qwen/Qwen2.5-1.5B-Instruct` をスクリプトでデプロイし、OpenAI SDK で `https://api.runpod.ai/v2/<endpoint>/openai/v1` を呼び出します。2026-11-05 に RTX 4090、FlashBoot オンで 1 回実行しました。完全な記録は[ラボの README](https://github.com/litkhai/runpod-hols/tree/main/serverless/03-vllm-endpoint) にあります。

| worker が起動した後 | 結果 |
|---|---|
| `models.list()` | `['Qwen/Qwen2.5-1.5B-Instruct']` |
| チャット補完、40+20 トークン | 1.6 s |
| ストリーミング補完 | 最初のトークンまで 0.76 s |

<div class="warn" markdown="1">
**最初のコールドスタートは 15 分かかり、そのうち vLLM は 77 秒でした。** worker のログには、ホストにキャッシュ済みだったイメージのロードに 3 min 52 s、続いて `worker is ready` の後 `create container` まで何もログが出ない 10 min 14 s が記録されています。最初のリクエストは **7 min 12 s 後に HTTP 520** で返り、ジョブはキューに残ったまま、コンテナが起動した後のリトライに応答が返りました。この空白の間、`/health` は ready な worker を報告しており、`workersMax` 1 なのに worker が 3 つ存在していました。1 回の実行なので、原因は特定できていません。
</div>

<div class="note" markdown="1">
**テンプレートの削除は 1 時間半以上待つことがあります。** エンドポイントを削除した後、`DELETE /templates/{id}` は *"Template is still held by deleted endpoint …, which is pending cleanup"* と応答しました。メッセージには *"within about 90 minutes"* とありますが、2026-11-05 には、あるテンプレートは 86 分の時点でまだ拒否され 116 分で削除でき、別のものは 92 分で削除できました。ラボの `teardown.py` は id を保持し、再実行するよう案内します。
</div>

[リポジトリでラボ全体を見る →](https://github.com/litkhai/runpod-hols/tree/main/serverless)

</div>
