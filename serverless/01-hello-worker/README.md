# Lab 01 — Hello Worker

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** build a minimal Serverless worker, verify it locally, containerize it, and deploy it as a Runpod endpoint.

**Time:** ~20 minutes · **Cost:** near zero (CPU worker, a handful of requests)

### Files

| File | Role |
|---|---|
| `handler.py` | The worker. `handler(job)` reads `job["input"]` and returns the result |
| `test_input.json` | Sample input used automatically by local runs |
| `requirements.txt` | Python dependencies (`runpod~=1.11.0`) |
| `Dockerfile` | Image definition (`python:3.11-slim`) |
| `.runpod/hub.json` | Runpod Hub listing metadata (only needed when publishing) |
| `.runpod/tests.json` | Test definitions run by Hub CI |

### Step 1 — Set up the environment

```bash
cd serverless/01-hello-worker
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Do not use the system `python3` on macOS — it is 3.9, and the SDK requires 3.10+.

Without `uv`, use any Python 3.10+: `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`

### Step 2 — Run the handler locally

```bash
.venv/bin/python handler.py
```

With no arguments the SDK picks up `test_input.json`, runs one job, and exits:

```
--- Starting Serverless Worker |  Version 1.11.0 ---
INFO   | Using test_input.json as job input.
INFO   | local_test | Started.
INFO   | Job local_test completed successfully.
INFO   | Job result: {'output': {'greeting': 'Hello, Runpod!', 'worker_id': 'local'}}
INFO   | Local testing complete, exiting.
```

This is the fastest edit-test loop — no container, no cloud. Change `test_input.json` and rerun.

### Step 3 — Run as a local API server

```bash
.venv/bin/python handler.py --rp_serve_api
```

This starts uvicorn on `http://localhost:8000`, mimicking the real endpoint. In another terminal:

```bash
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d '{"input": {"name": "Kee Hoon"}}'
```

```json
{"id":"test-1bec00ea-...","status":"COMPLETED","output":{"greeting":"Hello, Kee Hoon!","worker_id":"local"}}
```

Note the response shape — `id` / `status` / `output` — is exactly what the deployed endpoint returns. Interactive API docs are at `http://localhost:8000/docs`. Change the port with `--rp_api_port`.

### Step 4 — Build the image

```bash
docker build --platform linux/amd64 -t <YOUR_DOCKERHUB_USERNAME>/hello-worker:v1.0.0 .
```

`--platform linux/amd64` is mandatory on Apple Silicon. Runpod workers are amd64; an arm64 image will fail to start.

> **Build context.** The `COPY` paths in the Dockerfile are relative to this directory, which is what keeps the lab self-contained — you can copy the folder anywhere and it still builds. Runpod, however, defaults its build context to the **repo root**, so when deploying you must set the endpoint's **Build context** field (under Advanced settings) to `/serverless/01-hello-worker`. Skip it and the build fails with `"/handler.py": not found`. More on this in Step 5.

> **Do not tag this `:latest`.** Runpod caches images to speed up worker startup, and because `:latest` is mutable, workers can keep serving the previous build after you push a new one — with no obvious sign that they are. Use `v1.0.0`, `v1.0.1`, … so you always know what is running and can roll back. Runpod also validates the image reference when you create an endpoint and rejects a tag that does not resolve to a published image.

The slim base produces a ~106MB image in a few seconds. Verify it runs:

```bash
docker run --rm --platform linux/amd64 <YOUR_DOCKERHUB_USERNAME>/hello-worker:v1.0.0
```

You should see the same "Hello, Runpod!" output — `test_input.json` is not in the image, so the SDK reports it has no local input and waits; that is expected. Press Ctrl+C.

### Step 5 — Deploy

Two options.

**Option A — GitHub integration (recommended).** Runpod clones the repo, builds the image itself, stores it in **Runpod's own registry**, and deploys it. No local build, no Docker Hub account, and no slow emulated builds on Apple Silicon.

1. Console → [Settings](https://console.runpod.io/user/settings) → **Connections** → **GitHub** → **Connect**, and grant access to this repository.
2. [Serverless](https://console.runpod.io/serverless) → **New Endpoint** → **Import Git Repository** → select `runpod-hols`.
3. **Branch:** `main`. **Dockerfile Path:** `/serverless/01-hello-worker/Dockerfile`.
4. **Advanced settings → Build context:** `/serverless/01-hello-worker`. **This is the step that is easy to miss.**
5. Configure the endpoint (see the settings table below) and **Deploy Endpoint**.
6. Watch the **Builds** tab: Pending → Building → Uploading → Testing → Completed.

> **Redeploy behaviour — docs and observation disagree.** The docs say: *"When you make changes to your GitHub repository, they won't automatically be pushed to your endpoint. To trigger an update for the workers on your endpoint, create a new release."* In practice, two plain `git push`es to `main` each kicked off a build on this endpoint with no release involved — including an empty commit. Both happened while the endpoint had no successful build yet, so the documented behaviour may only apply once one exists. Treat a release as the reliable trigger and a push as a maybe. Either way, the Builds tab lets you roll back to an earlier build.

> **Set the Build context, and save it before triggering a build.** Runpod defaults the build context to the repo root and the main form only asks for a Dockerfile path, so a nested Dockerfile using bare `COPY handler.py .` fails:
>
> ```
> ERROR: failed to compute cache key: "/handler.py": not found
> ```
>
> The build log names the culprit — the context is the last positional argument, and by default it is the clone root:
>
> ```
> docker buildx build --file /app/<id>/temp/serverless/01-hello-worker/Dockerfile \
>                     /app/<id>/temp          <- context
> ```
>
> Setting **Advanced settings → Build context** to `/serverless/01-hello-worker` fixes it. **Verified: with the field saved and a build triggered afterwards, the build succeeds.**
>
> The trap is ordering. A build triggered by a `git push` that races the save still uses the old configuration, so it fails identically and looks like the field does nothing. Save first, then trigger.

This is also how Runpod structures its own repositories, which is why the Dockerfile here stays self-contained rather than using repo-root-relative `COPY` paths:

| Repo | Approach |
|---|---|
| [`runpod-workers/*`](https://github.com/orgs/runpod-workers/repositories) | One repo per worker, `Dockerfile` at the root |
| [`runpod/containers`](https://github.com/runpod/containers) | Monorepo; `docker-bake.hcl` sets `context = "official-templates/<name>"` per target, and shares files across directories with `COPY --from=<named-context>` |

Nothing in the Runpod org uses root-relative `COPY` paths. The console's Build context field is the deployment-time equivalent of bake's `context =`.

See [the GitHub integration guide](https://docs.runpod.io/serverless/github-integration).

**Option B — manual push.**

```bash
docker login
docker push <YOUR_DOCKERHUB_USERNAME>/hello-worker:v1.0.0
```

Then in the console: **Serverless → New Endpoint → import your Docker image.**

Endpoint settings for this lab:

| Setting | Value | Why |
|---|---|---|
| Endpoint Type | Queue | Standard request/response |
| GPU | smallest available, or CPU | No GPU work in this handler |
| Active Workers | **0** | Anything higher bills continuously |
| Max Workers | 1–3 | Enough to observe scale-out |

### Step 6 — Test the endpoint

Easiest path: the **Requests** tab on the endpoint detail page. Paste the `test_input.json` contents and Run.

From the CLI, fill in `.env` first, then:

```bash
source ../../.env
curl -X POST "https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"name": "Runpod"}}'
```

The `worker_id` in the response is the real worker ID now, not `local`:

```json
{"delayTime":3704,"executionTime":222,"status":"COMPLETED",
 "output":{"greeting":"Hello, Runpod!","worker_id":"fdvvjr22xrt5m7"},
 "workerId":"fdvvjr22xrt5m7"}
```

Measured on this endpoint, CPU workers, `workers_min = 0`:

| Request | `delayTime` | `executionTime` |
|---|---|---|
| First (cold) | 3,704 ms | 222 ms |
| Warm | 776–806 ms | 194–217 ms |

`delayTime` is queue plus worker startup; `executionTime` is your handler. The handler is a rounding error here — **almost all of the first request is cold start**, which is the whole reason `workers_min = 0` trades latency for cost. Fire several requests in a row and watch `worker_id` change as workers scale out.

> **`{"input": {}}` never returns.** An empty input object hung for 90 seconds with a zero-byte response and `retries: 1`, repeatedly. It is not the handler — `{"input": {"other": 1}}` takes the identical default path and returns `Hello, World!` immediately. Send at least one key. The `.runpod/tests.json` case for the default path uses `{"unused": true}` for exactly this reason.

> **`/runsync` does not always return `COMPLETED`.** It can return `IN_PROGRESS` with a job `id`, which you then poll at `/status/{id}`. Do not assume `output` is present in the first response.

### Step 7 — Clean up

Serverless with Active Workers at 0 costs nothing when idle, so you can leave the endpoint. To remove it entirely: **Endpoint → Settings → Delete**.

### Troubleshooting

| Symptom | Cause |
|---|---|
| Build fails: `"/handler.py": not found` | **Build context** not set. Put `/serverless/01-hello-worker` in Advanced settings |
| `runpod` will not install | Using Python 3.9. Use `uv venv --python 3.11` |
| Worker never starts, no logs | Image built for arm64. Rebuild with `--platform linux/amd64` |
| Console logs appear late or in bursts | Missing `-u` on the `python` command in the Dockerfile |
| `401 Unauthorized` | `RUNPOD_API_KEY` missing or wrong in `.env` |
| First request is slow, later ones fast | Normal cold start — the image pull and container boot |

### Next

Move heavy work out of the handler: load a model at module scope and observe the cold-start difference. That is the bridge to Lab 02 (vLLM endpoint).

---

## 한국어

**목표:** 최소 구성의 Serverless 워커를 만들어 로컬에서 검증하고, 컨테이너로 만들어 Runpod 엔드포인트로 배포합니다.

**소요 시간:** 약 20분 · **비용:** 거의 없음 (CPU 워커, 요청 몇 건)

### 파일 구성

| 파일 | 역할 |
|---|---|
| `handler.py` | 워커 본체. `handler(job)` 가 `job["input"]` 을 읽어 결과를 반환 |
| `test_input.json` | 로컬 실행 시 자동으로 사용되는 샘플 입력 |
| `requirements.txt` | Python 의존성 (`runpod~=1.11.0`) |
| `Dockerfile` | 이미지 정의 (`python:3.11-slim`) |
| `.runpod/hub.json` | Runpod Hub 게시용 메타데이터 (게시할 때만 필요) |
| `.runpod/tests.json` | Hub CI 가 실행하는 테스트 정의 |

### 1단계 — 환경 구성

```bash
cd serverless/01-hello-worker
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

macOS 시스템 `python3` 는 3.9 이므로 사용하지 마세요. SDK 가 3.10 이상을 요구합니다.

`uv` 가 없다면 3.10 이상 아무 Python 이나 쓰면 됩니다: `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`

### 2단계 — 로컬에서 handler 실행

```bash
.venv/bin/python handler.py
```

인자 없이 실행하면 SDK 가 `test_input.json` 을 읽어 작업 1건을 처리하고 종료합니다.

```
--- Starting Serverless Worker |  Version 1.11.0 ---
INFO   | Using test_input.json as job input.
INFO   | local_test | Started.
INFO   | Job local_test completed successfully.
INFO   | Job result: {'output': {'greeting': 'Hello, Runpod!', 'worker_id': 'local'}}
INFO   | Local testing complete, exiting.
```

컨테이너도 클라우드도 없이 도는 가장 빠른 수정-테스트 루프입니다. `test_input.json` 을 바꿔가며 반복하세요.

### 3단계 — 로컬 API 서버로 실행

```bash
.venv/bin/python handler.py --rp_serve_api
```

`http://localhost:8000` 에 uvicorn 이 뜨면서 실제 엔드포인트와 동일하게 동작합니다. 다른 터미널에서:

```bash
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d '{"input": {"name": "Kee Hoon"}}'
```

```json
{"id":"test-1bec00ea-...","status":"COMPLETED","output":{"greeting":"Hello, Kee Hoon!","worker_id":"local"}}
```

응답 형태(`id` / `status` / `output`)가 배포된 엔드포인트와 정확히 같다는 점을 눈여겨보세요. `http://localhost:8000/docs` 에서 인터랙티브 API 문서를 볼 수 있고, 포트는 `--rp_api_port` 로 변경합니다.

### 4단계 — 이미지 빌드

```bash
docker build --platform linux/amd64 -t <도커허브_사용자명>/hello-worker:v1.0.0 .
```

Apple Silicon 에서는 `--platform linux/amd64` 가 필수입니다. Runpod 워커는 amd64 이며 arm64 이미지는 기동에 실패합니다.

> **빌드 컨텍스트.** Dockerfile 의 `COPY` 경로는 이 디렉토리 기준입니다. 그래야 실습이 자체 완결적이어서 폴더를 어디로 옮겨도 빌드됩니다. 다만 Runpod 은 빌드 컨텍스트 기본값이 **저장소 루트**이므로, 배포할 때 엔드포인트의 **Build context** 필드(Advanced settings)에 `/serverless/01-hello-worker` 를 지정해야 합니다. 빠뜨리면 `"/handler.py": not found` 로 실패합니다. 자세한 내용은 5단계에 있습니다.

> **`:latest` 태그는 쓰지 마세요.** Runpod 은 워커 기동 속도를 위해 이미지를 캐시하는데, `:latest` 는 가변 태그이므로 새 이미지를 푸시해도 워커가 이전 빌드를 계속 서빙할 수 있습니다. 그것도 눈에 띄는 표시 없이요. `v1.0.0`, `v1.0.1` 처럼 버전을 붙이면 무엇이 돌고 있는지 항상 알 수 있고 롤백도 가능합니다. 또한 Runpod 은 엔드포인트 생성 시 이미지 참조를 검증하며, 실제로 게시되지 않은 태그는 거부합니다.

slim 베이스 기준으로 약 106MB 이미지가 수 초 만에 만들어집니다. 동작을 확인하려면:

```bash
docker run --rm --platform linux/amd64 <도커허브_사용자명>/hello-worker:v1.0.0
```

이미지 안에는 `test_input.json` 이 없으므로 SDK 가 로컬 입력이 없다고 알리고 대기 상태로 들어갑니다. 정상 동작이며 Ctrl+C 로 종료하면 됩니다.

### 5단계 — 배포

두 가지 방법이 있습니다.

**방법 A — GitHub 연동 (권장).** Runpod 이 저장소를 클론해 직접 이미지를 빌드하고, **Runpod 자체 레지스트리**에 저장한 뒤 배포합니다. 로컬 빌드도 Docker Hub 계정도 필요 없고, Apple Silicon 의 느린 에뮬레이션 빌드도 피할 수 있습니다.

1. 콘솔 → [Settings](https://console.runpod.io/user/settings) → **Connections** → **GitHub** → **Connect**, 이 저장소에 접근 권한 부여.
2. [Serverless](https://console.runpod.io/serverless) → **New Endpoint** → **Import Git Repository** → `runpod-hols` 선택.
3. **Branch:** `main`. **Dockerfile Path:** `/serverless/01-hello-worker/Dockerfile`.
4. **Advanced settings → Build context:** `/serverless/01-hello-worker`. **이 단계를 빠뜨리기 쉽습니다.**
5. 엔드포인트 설정(아래 표 참조) 후 **Deploy Endpoint**.
6. **Builds** 탭에서 진행 확인: Pending → Building → Uploading → Testing → Completed.

> **재배포 동작 — 문서와 실제가 다릅니다.** 문서에는 이렇게 적혀 있습니다. *"When you make changes to your GitHub repository, they won't automatically be pushed to your endpoint. To trigger an update for the workers on your endpoint, create a new release."* 그런데 실제로는 `main` 에 대한 일반 `git push` 두 번이 모두 빌드를 트리거했습니다. 빈 커밋도 마찬가지였습니다. 두 경우 모두 엔드포인트에 성공한 빌드가 아직 없던 상태였으므로, 문서의 설명은 성공한 빌드가 존재한 이후에만 적용될 수도 있습니다. 릴리스는 확실한 트리거, 푸시는 될 수도 있는 트리거로 보시면 됩니다. 어느 쪽이든 Builds 탭에서 이전 빌드로 롤백할 수 있습니다.

> **Build context 를 지정하고, 빌드를 트리거하기 전에 저장하세요.** Runpod 은 빌드 컨텍스트 기본값이 저장소 루트이고 기본 화면에서는 Dockerfile 경로만 물어봅니다. 그래서 하위 디렉토리의 Dockerfile 이 `COPY handler.py .` 를 쓰면 실패합니다.
>
> ```
> ERROR: failed to compute cache key: "/handler.py": not found
> ```
>
> 빌드 로그가 원인을 알려줍니다. 컨텍스트는 마지막 위치 인자이고, 기본값이 클론 루트입니다.
>
> ```
> docker buildx build --file /app/<id>/temp/serverless/01-hello-worker/Dockerfile \
>                     /app/<id>/temp          <- 컨텍스트
> ```
>
> **Advanced settings → Build context** 에 `/serverless/01-hello-worker` 를 넣으면 해결됩니다. **검증됨: 필드를 저장한 뒤 빌드를 트리거하면 성공합니다.**
>
> 함정은 순서입니다. 저장과 경쟁하듯 `git push` 로 트리거된 빌드는 이전 설정을 그대로 쓰기 때문에 똑같이 실패하고, 마치 필드가 동작하지 않는 것처럼 보입니다. 저장을 먼저, 트리거는 그 다음입니다.

Runpod 이 자기 저장소를 구성하는 방식도 이와 같습니다. 이 실습의 Dockerfile 이 루트 기준 `COPY` 경로 대신 자체 완결형을 유지하는 이유입니다.

| 저장소 | 방식 |
|---|---|
| [`runpod-workers/*`](https://github.com/orgs/runpod-workers/repositories) | 워커마다 저장소를 따로 두고 `Dockerfile` 을 루트에 배치 |
| [`runpod/containers`](https://github.com/runpod/containers) | 모노레포. `docker-bake.hcl` 이 타겟마다 `context = "official-templates/<name>"` 을 지정하고, 디렉토리를 넘나드는 파일은 `COPY --from=<named-context>` 로 공유 |

Runpod 조직 어디에도 루트 기준 `COPY` 경로는 없습니다. 콘솔의 Build context 필드가 bake 의 `context =` 에 해당하는 배포 시점 장치입니다.

[GitHub 연동 가이드](https://docs.runpod.io/serverless/github-integration) 참고.

**방법 B — 수동 푸시.**

```bash
docker login
docker push <도커허브_사용자명>/hello-worker:v1.0.0
```

이후 콘솔에서 **Serverless → New Endpoint → Docker 이미지 지정.**

이 실습의 엔드포인트 설정:

| 항목 | 값 | 이유 |
|---|---|---|
| Endpoint Type | Queue | 표준 요청/응답 방식 |
| GPU | 가장 작은 것 또는 CPU | 이 handler 는 GPU 연산이 없음 |
| Active Workers | **0** | 1 이상이면 상시 과금됨 |
| Max Workers | 1~3 | 스케일아웃을 관찰하기에 충분 |

### 6단계 — 엔드포인트 테스트

가장 쉬운 방법은 엔드포인트 상세 페이지의 **Requests** 탭입니다. `test_input.json` 내용을 붙여넣고 Run 을 누르면 됩니다.

CLI 로 하려면 `.env` 를 먼저 채우고:

```bash
source ../../.env
curl -X POST "https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"name": "Runpod"}}'
```

이제 응답의 `worker_id` 는 `local` 이 아니라 실제 워커 ID 입니다.

```json
{"delayTime":3704,"executionTime":222,"status":"COMPLETED",
 "output":{"greeting":"Hello, Runpod!","worker_id":"fdvvjr22xrt5m7"},
 "workerId":"fdvvjr22xrt5m7"}
```

이 엔드포인트에서 실측한 값입니다. CPU 워커, `workers_min = 0` 기준.

| 요청 | `delayTime` | `executionTime` |
|---|---|---|
| 첫 요청 (콜드) | 3,704 ms | 222 ms |
| 워밍 후 | 776~806 ms | 194~217 ms |

`delayTime` 은 큐 대기와 워커 기동, `executionTime` 은 핸들러 실행 시간입니다. 여기서 핸들러는 오차 수준이고 **첫 요청의 대부분이 콜드 스타트**입니다. `workers_min = 0` 이 지연시간과 비용을 맞바꾼다는 말의 실체가 이것입니다. 요청을 연속으로 보내면 워커가 늘어나며 `worker_id` 가 바뀌는 것도 볼 수 있습니다.

> **`{"input": {}}` 는 응답이 오지 않습니다.** 빈 입력 객체로 보내면 90초 동안 0바이트 응답에 `retries: 1` 이 붙은 채 멈췄고, 반복해도 같았습니다. 핸들러 문제가 아닙니다. `{"input": {"other": 1}}` 은 완전히 같은 기본값 경로를 타면서 즉시 `Hello, World!` 를 반환합니다. 키를 최소 하나는 넣으세요. `.runpod/tests.json` 의 기본값 테스트가 `{"unused": true}` 를 쓰는 이유입니다.

> **`/runsync` 가 항상 `COMPLETED` 를 반환하지는 않습니다.** 작업 `id` 와 함께 `IN_PROGRESS` 가 올 수 있고, 그때는 `/status/{id}` 로 폴링해야 합니다. 첫 응답에 `output` 이 있다고 가정하지 마세요.

### 7단계 — 정리

Active Worker 가 0 이면 유휴 상태에서 비용이 발생하지 않으므로 엔드포인트를 남겨둬도 됩니다. 완전히 제거하려면 **Endpoint → Settings → Delete**.

### 문제 해결

| 증상 | 원인 |
|---|---|
| 빌드 실패: `"/handler.py": not found` | **Build context** 미지정. Advanced settings 에 `/serverless/01-hello-worker` 입력 |
| `runpod` 설치 실패 | Python 3.9 사용 중. `uv venv --python 3.11` 로 해결 |
| 워커가 기동되지 않고 로그도 없음 | arm64 로 빌드된 이미지. `--platform linux/amd64` 로 재빌드 |
| 콘솔 로그가 늦게 또는 몰아서 출력됨 | Dockerfile 의 `python` 명령에 `-u` 가 빠짐 |
| `401 Unauthorized` | `.env` 의 `RUNPOD_API_KEY` 누락 또는 오류 |
| 첫 요청만 느리고 이후는 빠름 | 정상적인 콜드 스타트 (이미지 pull + 컨테이너 부팅) |

### 다음 단계

무거운 작업을 handler 밖으로 빼보세요. 모듈 스코프에서 모델을 로드하고 콜드 스타트 차이를 관찰하면 Lab 02 (vLLM 엔드포인트) 로 자연스럽게 이어집니다.
