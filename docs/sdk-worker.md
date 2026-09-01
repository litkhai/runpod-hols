---
layout: default
title: Worker SDK
permalink: /sdk/worker/
---

# Worker SDK

<div class="lang" data-lang="en" markdown="1">

## English

The half of the SDK that runs **inside your worker container**. The other half is [Client SDK]({{ '/sdk/client/' | relative_url }}).

Read out of the installed source at 1.11.0 and 1.12.0, and confirmed by running each case. Where behaviour is surprising, the observed output is shown.

### Startup fitness checks

Before your handler is ever called, the worker validates the machine it landed on. A failed check kills the process with `os._exit(1)` and the orchestrator routes the job elsewhere, rather than letting it fail slowly on bad hardware. At ~1,125 lines this is the largest part of the worker half, and it runs whether you ask for it or not.

| Always | Only when a GPU is present |
|---|---|
| Memory, disk, network | CUDA version, CUDA init, compute benchmark, GPU health binary |

Thresholds are environment variables, so you set them on the endpoint: `RUNPOD_MIN_MEMORY_GB` (4.0), `RUNPOD_MIN_DISK_PERCENT` (10.0), `RUNPOD_MIN_CUDA_VERSION` (11.8), and `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS` to turn groups off.

Add your own with a decorator — sync or async, raise to fail:

```python
@runpod.serverless.register_fitness_check
def check_weights_present():
    if not os.path.exists("/runpod-volume/model.safetensors"):
        raise RuntimeError("model weights missing")
```

<div class="warn" markdown="1">
**Failure is `os._exit(1)`, not an exception** — no `finally`, no cleanup. Deliberate: a worker that cannot serve should vanish rather than linger and accept jobs.
</div>

### The local API server

`--rp_serve_api` starts a FastAPI app that mimics the endpoint. Read off the running server's own OpenAPI document:

| Route | Method |
|---|---|
| `/run` | POST |
| `/runsync` | POST |
| `/status/{job_id}` | **POST** |
| `/stream/{job_id}` | **POST** |

Docs are at `/`, not `/docs` — that path is a 307 redirect.

<div class="warn" markdown="1">
**`/status` takes POST locally and GET on the platform.** `GET /status/{id}` against the local server returns **405**; `POST` returns 200. The real API documents GET. Pick the method by target, not from memory.
</div>

### How the SDK knows it is not in production

```python
IS_LOCAL_TEST = os.environ.get("RUNPOD_WEBHOOK_GET_JOB", None) is None
```

One variable decides it. The platform sets it; its absence means local. `rp_scale` reads the flag to decide whether `jobs_fetcher` / `jobs_handler` overrides are honoured — outside a local test they are ignored, which is why those config keys look inert in production.

### Environment variables

Platform-set, readable from your handler: `RUNPOD_POD_ID` (worker id, a random UUID locally), `RUNPOD_POD_HOSTNAME`, `RUNPOD_ENDPOINT_ID`, `RUNPOD_AI_API_KEY`, and four webhook URLs — `GET_JOB`, `PING`, `POST_OUTPUT`, `POST_STREAM`.

Yours to tune:

| Variable | Default |
|---|---|
| `RUNPOD_PING_INTERVAL` | `10000` ms |
| `RUNPOD_MIN_MEMORY_GB` | `4.0` |
| `RUNPOD_MIN_DISK_PERCENT` | `10.0` |
| `RUNPOD_MIN_CUDA_VERSION` | `11.8` |
| `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS` | unset |
| `RUNPOD_LOG_LEVEL` / `RUNPOD_DEBUG_LEVEL` / `UVICORN_LOG_LEVEL` | — |

The heartbeat posts `{"job_id": <ids in flight>, "runpod_version": …}` to `RUNPOD_WEBHOOK_PING`. The console's view of what a worker is doing comes from that, not from your handler.

### The worker loop

`JobScaler` runs three coroutines for the life of the worker: `get_jobs` fills a bounded queue, `run_jobs` hands each to your handler, `monitor_stop_signals` watches for cancellations.

**Concurrency changes wait for the worker to drain.** `set_scale` polls once a second until nothing is in flight before resizing the queue, so a load-reactive `concurrency_modifier` takes effect at the next idle moment rather than immediately.

**Cancelling a job cancels its task, not the worker.** `job.cancel()` from the client raises `CancelledError` inside your handler at its next `await`; other jobs on the same worker keep running. A synchronous handler with no `await` points cannot be interrupted this way.

SIGTERM and SIGINT set a shutdown event, so the loops finish rather than dying mid-job.

### Logging

Six levels — `NOTSET`, `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR` — default `DEBUG`, set by `RUNPOD_LOG_LEVEL`.

**The format switches on its own.** With `RUNPOD_ENDPOINT_ID` set, which it is on the platform, every line is JSON:

```json
{"requestId": "<job id>", "message": "...", "level": "INFO"}
```

Locally you get `INFO   | message`. Same call, different shape — which is why console and local logs do not look alike. Messages over **4096 characters** are truncated from the middle — the SDK's comment says 10MB, but the constant is 4096. Easy to hit with a stack trace.

<div class="note" markdown="1">
`log.secret(name, value)` masks all but the first and last character. It does not redact very short values: `"ab"` prints as `ab` and `"a"` as `aa`, because the mask is `"*" * (len - 2)`.
</div>

### A fourth place a model can live

SDK 1.12.0 added `VolumeCache`, which sits between "download every cold start" and "bake it into the image". It mirrors chosen directories onto a mounted network volume:

```python
from runpod.serverless import VolumeCache

with VolumeCache(dirs=["/root/.cache/huggingface"]):
    model = load_model()      # downloads land in the cached directory
```

On enter it hydrates the container from the volume; on exit it syncs new files back. It needs a network volume at `/runpod-volume` and scopes the mirror by `RUNPOD_ENDPOINT_ID`.

| | Endpoint **Model** field | `VolumeCache` |
|---|---|---|
| Scope | Hugging Face model ids | Any directory |
| Storage | Runpod's host cache | A network volume you attach |
| Set up | One console field | A network volume plus code |

With no volume attached every operation is a no-op, and it is best-effort throughout — a failure degrades to a cold worker rather than raising into your handler.

### Downloading caller-supplied URLs

`download_files_from_urls(job_id, urls)` fetches URLs from the job input to local files. Since 1.12.0 it refuses private address space: loopback, link-local — including the `169.254.169.254` metadata endpoint — RFC1918, and CGNAT `100.64.0.0/10`. The connection is pinned to the validated IP, so a hostname resolving to a private address is rejected rather than followed.

<div class="warn" markdown="1">
If your handler legitimately fetched from an internal host, that stops working on 1.12.0. A job input is attacker-controlled: without this, a caller could point your worker at instance metadata.
</div>

### Timing your handler

`--rp_debugger` collects timings with `LineTimer` (context manager) and `FunctionTimer` (decorator), returning them as an `rp_debugger` key inside `output` alongside `system_info` and `ready_delay_ms`.

<div class="warn" markdown="1">
**It does nothing locally.** The injection lives in `handle_job`, which only the production loop calls. Plain `python handler.py` and `--rp_serve_api` both call `run_job` directly and skip it — verified: the output is byte-identical with and without the flag. Use it on a deployed endpoint.
</div>

### Handler utilities

| Import | Use |
|---|---|
| `rp_validator.validate` | Types, defaults, constraint lambdas, rejects unknown keys |
| `utils.download_files_from_urls` | Caller-supplied URLs to local files |
| `utils.upload_file_to_bucket` / `upload_in_memory_object` | S3-compatible storage, returns a URL |
| `rp_progress.progress_update` | Visible via `/status`, runs off-thread |

<div class="note" markdown="1">
**This is the answer to the 20 MB return limit** — upload the payload and return its URL. Credentials come from `BUCKET_ENDPOINT_URL`, `BUCKET_ACCESS_KEY_ID` and `BUCKET_SECRET_ACCESS_KEY`. With those unset the SDK writes locally instead: convenient in development, silently useless in production.
</div>

### The contract

```python
import runpod

def handler(job):
    return {"result": job["input"]["x"] * 2}

runpod.serverless.start({"handler": handler})
```

`start()` takes a config dict, not just a handler, and **does not return** — it takes over the process and calls your handler once per job. The handler receives at least `id` and `input`; `job["input"]` is exactly what the caller sent.

### Return values — two keys are control signals

The SDK inspects your return value and pulls two keys out as control signals rather than data:

| You return | SDK produces | Effect |
|---|---|---|
| `{"ok": True}` | `{"output": {"ok": True}}` | Normal success |
| `{"ok": False, "error": "bad input"}` | `{"output": {"ok": False}, "error": "bad input"}` | **Job marked FAILED** |
| `{"ok": True, "refresh_worker": True}` | `{"output": {"ok": True}, "stopPod": True}` | Success, worker recycled |
| `{}` | `{}` | `output` dropped entirely |
| `"just a string"` | `{"output": "just a string"}` | Non-dicts wrapped |

<div class="warn" markdown="1">
**`error` is not a normal field.** An `error` key anywhere in a returned dict fails the job:

```
DEBUG | run_job return: {'output': {'ok': False}, 'error': 'bad input'}
ERROR | Job local_test failed with error: bad input
```

So you cannot use `error` as ordinary output — `{"error": "just a warning"}` would fail an otherwise successful job. Name it something else.
</div>

### Exceptions

The SDK catches them, the worker survives, and the job fails with a JSON blob containing `error_type`, `error_message`, `error_traceback`, `hostname`, `worker_id` and `runpod_version`.

<div class="warn" markdown="1">
**The full traceback goes to the caller**, absolute paths and source lines included. Catch expected failures and return a controlled `error` string instead.
</div>

### Streaming

`yield` instead of `return`, and each partial is sent as its own `{"output": ...}`. Sync and async generators both work. Add `return_aggregate_stream: True` so `/runsync` and `/status` can return the collected output, not just `/stream`.

<div class="note" markdown="1">
Local `test_input.json` runs do **not** exercise streaming — the generator comes back unconsumed as `{'output': <generator object ...>}`. Test against a real endpoint or `--rp_serve_api`.
</div>

### Other config keys

| Key | Purpose |
|---|---|
| `handler` | Required. Sync, async, generator or async generator |
| `return_aggregate_stream` | Collect generator output for `/runsync` and `/status` |
| `concurrency_modifier` | `fn(current: int) -> int` — one worker takes several jobs at once |

### Also in the toolbox

- **`progress_update(job, msg)`** — visible to callers via `/status`, runs on a background thread.
- **`rp_validator.validate(input, schema)`** — type checks, defaults, `constraints` lambdas, rejects unexpected keys.
- **`download_files_from_urls` / `upload_file_to_bucket`** — for caller-supplied URLs and large results.
- **`register_fitness_check`** — startup checks; a failure exits the worker so the orchestrator restarts it.
- **Return bodies over 20 MB** trigger an SDK tip recommending S3 instead. A log line, not enforced — treat it as a limit anyway.

### Local test flags

| Flag | Effect |
|---|---|
| *(none)* | Runs `test_input.json` once, then exits |
| `--rp_serve_api` | Local API on `http://localhost:8000`, same shape as the real endpoint |
| `--rp_api_port` / `--rp_api_host` / `--rp_api_concurrency` | Bind and worker settings |
| `--rp_log_level` | `ERROR`, `WARN`, `INFO`, `DEBUG` |
| `--rp_debugger` | Attach the SDK debugger |

[Full reference in the repo →](https://github.com/litkhai/runpod-hols/blob/main/sdk/worker.md)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

1.11.0 과 1.12.0 의 설치된 SDK 소스를 직접 읽고 각 경우를 실행해 확인한 내용입니다. 동작이 직관과 다른 부분은 실제 출력을 함께 실었습니다.

### 기동 시 fitness check

핸들러가 호출되기 전에 워커가 자기가 배치된 머신을 검증합니다. 검사가 실패하면 `os._exit(1)` 로 프로세스를 종료하고 오케스트레이터가 작업을 다른 곳으로 보냅니다. 불량 하드웨어 위에서 천천히 실패하게 두지 않는 것입니다. 약 1,125줄로 워커 절반에서 가장 큰 부분이며, 요청하지 않아도 실행됩니다.

| 항상 | GPU 가 있을 때만 |
|---|---|
| 메모리, 디스크, 네트워크 | CUDA 버전, CUDA 초기화, 연산 벤치마크, GPU 헬스 바이너리 |

임계값은 환경변수라 엔드포인트에서 설정합니다. `RUNPOD_MIN_MEMORY_GB` (4.0), `RUNPOD_MIN_DISK_PERCENT` (10.0), `RUNPOD_MIN_CUDA_VERSION` (11.8), 그리고 그룹을 끄려면 `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS`.

데코레이터로 직접 추가할 수 있습니다. 동기·비동기 모두 되고, 실패시키려면 예외를 던집니다.

```python
@runpod.serverless.register_fitness_check
def check_weights_present():
    if not os.path.exists("/runpod-volume/model.safetensors"):
        raise RuntimeError("model weights missing")
```

<div class="warn" markdown="1">
**실패는 예외가 아니라 `os._exit(1)` 입니다.** `finally` 도 정리 코드도 실행되지 않습니다. 의도된 동작입니다. 서비스할 수 없는 워커는 남아서 작업을 받는 대신 사라져야 합니다.
</div>

### 로컬 API 서버

`--rp_serve_api` 는 엔드포인트를 흉내 내는 FastAPI 앱을 띄웁니다. 실행 중인 서버의 OpenAPI 문서에서 읽은 내용입니다.

| 경로 | 메서드 |
|---|---|
| `/run` | POST |
| `/runsync` | POST |
| `/status/{job_id}` | **POST** |
| `/stream/{job_id}` | **POST** |

문서는 `/docs` 가 아니라 `/` 에 있습니다. `/docs` 는 307 리다이렉트입니다.

<div class="warn" markdown="1">
**`/status` 는 로컬에서 POST, 플랫폼에서 GET 입니다.** 로컬 서버에 `GET /status/{id}` 는 **405**, `POST` 는 200 입니다. 실제 API 는 GET 으로 문서화돼 있습니다. 메서드는 기억이 아니라 대상에 맞춰 고르세요.
</div>

### SDK 는 프로덕션이 아님을 어떻게 아는가

```python
IS_LOCAL_TEST = os.environ.get("RUNPOD_WEBHOOK_GET_JOB", None) is None
```

변수 하나로 판별합니다. 플랫폼이 설정하고, 없으면 로컬입니다. `rp_scale` 이 이 플래그를 보고 `jobs_fetcher` / `jobs_handler` 덮어쓰기 반영 여부를 결정합니다. 로컬 테스트가 아니면 무시되며, 그래서 프로덕션에서 이 설정 키들이 죽은 것처럼 보입니다.

### 환경변수

플랫폼이 설정하며 핸들러에서 읽을 수 있는 것: `RUNPOD_POD_ID` (워커 id, 로컬에서는 랜덤 UUID), `RUNPOD_POD_HOSTNAME`, `RUNPOD_ENDPOINT_ID`, `RUNPOD_AI_API_KEY`, 그리고 webhook URL 네 개 — `GET_JOB`, `PING`, `POST_OUTPUT`, `POST_STREAM`.

내가 조정하는 것:

| 변수 | 기본값 |
|---|---|
| `RUNPOD_PING_INTERVAL` | `10000` ms |
| `RUNPOD_MIN_MEMORY_GB` | `4.0` |
| `RUNPOD_MIN_DISK_PERCENT` | `10.0` |
| `RUNPOD_MIN_CUDA_VERSION` | `11.8` |
| `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS` | 미설정 |
| `RUNPOD_LOG_LEVEL` / `RUNPOD_DEBUG_LEVEL` / `UVICORN_LOG_LEVEL` | — |

하트비트는 `RUNPOD_WEBHOOK_PING` 으로 `{"job_id": <진행 중인 id 들>, "runpod_version": …}` 를 보냅니다. 콘솔이 워커 상태를 아는 경로는 핸들러가 아니라 이 하트비트입니다.

### 워커 루프

`JobScaler` 는 워커가 사는 동안 코루틴 세 개를 돌립니다. `get_jobs` 가 크기 제한된 큐를 채우고, `run_jobs` 가 각각을 핸들러에 넘기며, `monitor_stop_signals` 가 취소 요청을 감시합니다.

**동시성 변경은 워커가 빌 때까지 기다립니다.** `set_scale` 이 진행 중인 작업이 없어질 때까지 1초 간격으로 확인한 뒤 큐 크기를 바꾸므로, 부하에 반응하는 `concurrency_modifier` 는 즉시가 아니라 다음 유휴 시점에 적용됩니다.

**작업 취소는 워커가 아니라 그 작업의 태스크만 취소합니다.** 클라이언트의 `job.cancel()` 은 핸들러의 다음 `await` 지점에서 `CancelledError` 를 일으키고, 같은 워커의 다른 작업은 계속 돕니다. `await` 지점이 없는 동기 핸들러는 이 방식으로 중단되지 않습니다.

SIGTERM 과 SIGINT 는 종료 이벤트를 세팅하므로 루프가 작업 중간에 죽지 않고 마무리됩니다.

### 로깅

레벨 여섯 개 — `NOTSET`, `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR` — 기본값 `DEBUG`, `RUNPOD_LOG_LEVEL` 로 설정합니다.

**형식이 스스로 바뀝니다.** 플랫폼에서는 설정돼 있는 `RUNPOD_ENDPOINT_ID` 가 있으면 모든 줄이 JSON 입니다.

```json
{"requestId": "<job id>", "message": "...", "level": "INFO"}
```

로컬에서는 `INFO   | message` 입니다. 같은 호출인데 형태가 달라, 콘솔 로그와 로컬 로그가 달라 보입니다. **4096자**를 넘는 메시지는 가운데가 잘립니다. SDK 주석은 10MB 라고 하지만 상수는 4096 입니다. 스택 트레이스면 쉽게 넘습니다.

<div class="note" markdown="1">
`log.secret(name, value)` 는 첫 글자와 마지막 글자만 남기고 가립니다. 아주 짧은 값은 가리지 못합니다. 마스크가 `"*" * (len - 2)` 라서 `"ab"` 는 `ab`, `"a"` 는 `aa` 로 나옵니다.
</div>

### 모델이 있을 수 있는 네 번째 장소

SDK 1.12.0 에 `VolumeCache` 가 추가됐습니다. "콜드 스타트마다 다운로드" 와 "이미지에 굽기" 사이의 선택지로, 지정한 디렉토리를 마운트된 네트워크 볼륨에 미러링합니다.

```python
from runpod.serverless import VolumeCache

with VolumeCache(dirs=["/root/.cache/huggingface"]):
    model = load_model()      # 다운로드가 캐시 디렉토리에 떨어진다
```

진입 시 볼륨에서 컨테이너로 채우고, 종료 시 새 파일을 볼륨으로 되돌립니다. `/runpod-volume` 에 마운트된 네트워크 볼륨이 필요하며, 미러 범위는 `RUNPOD_ENDPOINT_ID` 로 나눕니다.

| | 엔드포인트 **Model** 필드 | `VolumeCache` |
|---|---|---|
| 범위 | Hugging Face 모델 ID | 임의의 디렉토리 |
| 저장 위치 | Runpod 호스트 캐시 | 내가 붙인 네트워크 볼륨 |
| 설정 | 콘솔 필드 하나 | 네트워크 볼륨 + 코드 |

볼륨이 없으면 모든 동작이 no-op 이고, 전 구간이 best-effort 라서 실패해도 핸들러로 예외가 올라오지 않고 콜드 워커로 떨어집니다.

### 호출자가 준 URL 다운로드

`download_files_from_urls(job_id, urls)` 는 작업 입력의 URL 을 로컬 파일로 받아옵니다. 1.12.0 부터 사설 주소 대역을 거부합니다 — 루프백, 링크로컬(`169.254.169.254` 메타데이터 포함), RFC1918, CGNAT `100.64.0.0/10`. 검증된 IP 로 연결을 고정하므로 사설 주소로 해석되는 호스트명은 따라가지 않고 거부합니다.

<div class="warn" markdown="1">
내부 호스트에서 정당하게 받아오던 핸들러라면 1.12.0 에서 동작이 멈춥니다. 작업 입력은 공격자가 제어할 수 있는 값이라, 이것이 없으면 호출자가 워커를 인스턴스 메타데이터로 향하게 할 수 있습니다.
</div>

### 핸들러 시간 재기

`--rp_debugger` 는 `LineTimer`(컨텍스트 매니저)와 `FunctionTimer`(데코레이터)로 타이밍을 수집해, `output` 안에 `rp_debugger` 키로 `system_info`, `ready_delay_ms` 와 함께 반환합니다.

<div class="warn" markdown="1">
**로컬에서는 아무 효과가 없습니다.** 주입 코드가 프로덕션 루프만 호출하는 `handle_job` 안에 있습니다. `python handler.py` 도 `--rp_serve_api` 도 `run_job` 을 직접 호출해 이 경로를 건너뜁니다. 확인 결과 플래그 유무에 관계없이 출력이 완전히 같았습니다. 배포된 엔드포인트에서 쓰세요.
</div>

### Handler 유틸리티

| import | 용도 |
|---|---|
| `rp_validator.validate` | 타입, 기본값, 제약 람다, 알 수 없는 키 거부 |
| `utils.download_files_from_urls` | 호출자가 준 URL 을 로컬 파일로 |
| `utils.upload_file_to_bucket` / `upload_in_memory_object` | S3 호환 스토리지, URL 반환 |
| `rp_progress.progress_update` | `/status` 로 노출, 별도 스레드 실행 |

<div class="note" markdown="1">
**20MB 반환 제한에 대한 답이 이것입니다** — 결과물을 업로드하고 URL 을 반환하세요. 자격 증명은 `BUCKET_ENDPOINT_URL`, `BUCKET_ACCESS_KEY_ID`, `BUCKET_SECRET_ACCESS_KEY` 에서 옵니다. 이 값들이 없으면 SDK 가 로컬에 씁니다. 개발에는 편하지만 프로덕션에서는 조용히 무용지물입니다.
</div>

### 계약

```python
import runpod

def handler(job):
    return {"result": job["input"]["x"] * 2}

runpod.serverless.start({"handler": handler})
```

`start()` 는 핸들러가 아니라 설정 딕셔너리를 받고, **반환하지 않습니다.** 프로세스를 넘겨받아 작업마다 핸들러를 호출합니다. 핸들러는 최소 `id` 와 `input` 을 받으며, `job["input"]` 은 호출자가 보낸 그대로입니다.

### 반환값 — 키 두 개는 제어 신호입니다

SDK 가 반환값을 검사해 두 키를 데이터가 아닌 제어 신호로 꺼냅니다.

| 반환값 | SDK 결과 | 효과 |
|---|---|---|
| `{"ok": True}` | `{"output": {"ok": True}}` | 정상 성공 |
| `{"ok": False, "error": "bad input"}` | `{"output": {"ok": False}, "error": "bad input"}` | **작업 실패 처리** |
| `{"ok": True, "refresh_worker": True}` | `{"output": {"ok": True}, "stopPod": True}` | 성공 후 워커 재활용 |
| `{}` | `{}` | `output` 이 통째로 사라짐 |
| `"just a string"` | `{"output": "just a string"}` | 딕셔너리가 아니면 감싸짐 |

<div class="warn" markdown="1">
**`error` 는 일반 필드가 아닙니다.** 반환 딕셔너리 어디에든 `error` 키가 있으면 작업이 실패합니다.

```
DEBUG | run_job return: {'output': {'ok': False}, 'error': 'bad input'}
ERROR | Job local_test failed with error: bad input
```

따라서 `error` 를 평범한 출력 필드로 쓸 수 없습니다. `{"error": "단순 경고"}` 는 성공했어야 할 작업을 실패시킵니다. 다른 이름을 쓰세요.
</div>

### 예외

SDK 가 잡습니다. 워커는 살아남고 작업만 실패하며, `error_type`, `error_message`, `error_traceback`, `hostname`, `worker_id`, `runpod_version` 이 담긴 JSON 이 반환됩니다.

<div class="warn" markdown="1">
**전체 트레이스백이 호출자에게 전달됩니다.** 절대 경로와 소스 라인까지 포함해서요. 예상 가능한 실패는 잡아서 통제된 `error` 문자열로 반환하세요.
</div>

### 스트리밍

`return` 대신 `yield` 하면 각 조각이 개별 `{"output": ...}` 으로 전송됩니다. 동기·비동기 제너레이터 모두 됩니다. `return_aggregate_stream: True` 를 주면 `/stream` 뿐 아니라 `/runsync` 와 `/status` 에서도 모아진 출력을 받습니다.

<div class="note" markdown="1">
로컬 `test_input.json` 실행은 스트리밍을 검증하지 **못합니다.** 제너레이터가 소비되지 않은 채 `{'output': <generator object ...>}` 로 돌아옵니다. 실제 엔드포인트나 `--rp_serve_api` 로 테스트하세요.
</div>

### 그 외 설정 키

| 키 | 용도 |
|---|---|
| `handler` | 필수. 동기 / 비동기 / 제너레이터 / 비동기 제너레이터 |
| `return_aggregate_stream` | 제너레이터 출력을 모아 `/runsync`·`/status` 에서 반환 |
| `concurrency_modifier` | `fn(current: int) -> int` — 워커 하나가 여러 작업을 동시에 |

### 도구 상자의 나머지

- **`progress_update(job, msg)`** — 호출자가 `/status` 에서 확인. 백그라운드 스레드에서 실행되어 핸들러를 막지 않음
- **`rp_validator.validate(input, schema)`** — 타입 검사, 기본값, `constraints` 람다, 예상치 못한 키 거부
- **`download_files_from_urls` / `upload_file_to_bucket`** — 호출자가 준 URL 처리와 큰 결과물 업로드
- **`register_fitness_check`** — 기동 시 점검. 실패하면 워커가 종료되어 오케스트레이터가 재시작
- **반환 본문 20MB 초과** 시 SDK 가 S3 사용을 권하는 팁을 남김. 강제는 아니지만 제한으로 취급할 것

### 로컬 테스트 플래그

| 플래그 | 효과 |
|---|---|
| *(없음)* | `test_input.json` 1회 실행 후 종료 |
| `--rp_serve_api` | `http://localhost:8000` 로컬 API. 실제 엔드포인트와 같은 형태 |
| `--rp_api_port` / `--rp_api_host` / `--rp_api_concurrency` | 바인딩 및 워커 설정 |
| `--rp_log_level` | `ERROR`, `WARN`, `INFO`, `DEBUG` |
| `--rp_debugger` | SDK 디버거 연결 |

[저장소에서 전체 레퍼런스 보기 →](https://github.com/litkhai/runpod-hols/blob/main/sdk/worker.md)

</div>
