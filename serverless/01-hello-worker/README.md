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
docker build --platform linux/amd64 -t <YOUR_DOCKERHUB_USERNAME>/hello-worker:latest .
```

`--platform linux/amd64` is mandatory on Apple Silicon. Runpod workers are amd64; an arm64 image will fail to start.

The slim base produces a ~106MB image in a few seconds. Verify it runs:

```bash
docker run --rm --platform linux/amd64 <YOUR_DOCKERHUB_USERNAME>/hello-worker:latest
```

You should see the same "Hello, Runpod!" output — `test_input.json` is not in the image, so the SDK reports it has no local input and waits; that is expected. Press Ctrl+C.

### Step 5 — Deploy

Two options.

**Option A — GitHub integration (recommended).** Connect this repo in the Runpod console and Runpod builds the image on every push. No local build, no registry, and no slow emulated builds on Apple Silicon. See [the GitHub integration guide](https://docs.runpod.io/serverless/github-integration).

**Option B — manual push.**

```bash
docker login
docker push <YOUR_DOCKERHUB_USERNAME>/hello-worker:latest
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

The `worker_id` in the response is the real worker ID now, not `local`. Fire several requests in a row and watch it change as workers scale out.

### Step 7 — Clean up

Serverless with Active Workers at 0 costs nothing when idle, so you can leave the endpoint. To remove it entirely: **Endpoint → Settings → Delete**.

### Troubleshooting

| Symptom | Cause |
|---|---|
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
docker build --platform linux/amd64 -t <도커허브_사용자명>/hello-worker:latest .
```

Apple Silicon 에서는 `--platform linux/amd64` 가 필수입니다. Runpod 워커는 amd64 이며 arm64 이미지는 기동에 실패합니다.

slim 베이스 기준으로 약 106MB 이미지가 수 초 만에 만들어집니다. 동작을 확인하려면:

```bash
docker run --rm --platform linux/amd64 <도커허브_사용자명>/hello-worker:latest
```

이미지 안에는 `test_input.json` 이 없으므로 SDK 가 로컬 입력이 없다고 알리고 대기 상태로 들어갑니다. 정상 동작이며 Ctrl+C 로 종료하면 됩니다.

### 5단계 — 배포

두 가지 방법이 있습니다.

**방법 A — GitHub 연동 (권장).** 콘솔에서 이 저장소를 연결하면 푸시할 때마다 Runpod 이 이미지를 빌드합니다. 로컬 빌드도, 레지스트리도 필요 없고 Apple Silicon 의 느린 에뮬레이션 빌드도 피할 수 있습니다. [GitHub 연동 가이드](https://docs.runpod.io/serverless/github-integration) 참고.

**방법 B — 수동 푸시.**

```bash
docker login
docker push <도커허브_사용자명>/hello-worker:latest
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

이제 응답의 `worker_id` 는 `local` 이 아니라 실제 워커 ID 입니다. 요청을 연속으로 여러 번 보내면 워커가 늘어나면서 값이 바뀌는 것을 볼 수 있습니다.

### 7단계 — 정리

Active Worker 가 0 이면 유휴 상태에서 비용이 발생하지 않으므로 엔드포인트를 남겨둬도 됩니다. 완전히 제거하려면 **Endpoint → Settings → Delete**.

### 문제 해결

| 증상 | 원인 |
|---|---|
| `runpod` 설치 실패 | Python 3.9 사용 중. `uv venv --python 3.11` 로 해결 |
| 워커가 기동되지 않고 로그도 없음 | arm64 로 빌드된 이미지. `--platform linux/amd64` 로 재빌드 |
| 콘솔 로그가 늦게 또는 몰아서 출력됨 | Dockerfile 의 `python` 명령에 `-u` 가 빠짐 |
| `401 Unauthorized` | `.env` 의 `RUNPOD_API_KEY` 누락 또는 오류 |
| 첫 요청만 느리고 이후는 빠름 | 정상적인 콜드 스타트 (이미지 pull + 컨테이너 부팅) |

### 다음 단계

무거운 작업을 handler 밖으로 빼보세요. 모듈 스코프에서 모델을 로드하고 콜드 스타트 차이를 관찰하면 Lab 02 (vLLM 엔드포인트) 로 자연스럽게 이어집니다.
