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

### What changed in 2.x

Read from the installed 2.1.0 source on 2026-11-05 and compared with 1.12.0. No worker was built or run on 2.x; the labs' workers stay on `runpod~=1.12.0`, the version they were deployed and measured with.

| | 2.1.0 |
|---|---|
| The handler contract | Unchanged — `runpod.serverless.start({"handler": ...})`, the same `error` and `refresh_worker` handling, the same error payload fields |
| `register_prestart_hook(fn)` | New. Hooks run once before handler execution in queue, local-test and hosted-API modes, with an optional `prestart_timeout` in the `start()` config. Production queue intake continues while they run. Realtime mode rejects them; hosted-API mode needs `rp_api_concurrency=1` |
| Fitness checks at import | `import runpod` runs the startup fitness checks inside a Serverless worker process — not under `--test_input` or `--rp_serve_api`, and not in realtime mode |
| Handler logs in errors | `RUNPOD_LOG_CAPTURE=all` adds the last 16 KiB of stdout and stderr as `logs` in the error payload. The default, `auto`, does not for handlers |

Moving a worker to 2.x is a rebuild and a run, not a version bump: the image changes, so the measurements on these pages no longer describe it.

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

### 2.x 에서 바뀐 것

2026-11-05 에 설치된 2.1.0 소스를 읽고 1.12.0 과 비교했습니다. 2.x 로 워커를 빌드하거나 실행하지는 않았습니다. 실습 워커는 배포하고 측정한 버전인 `runpod~=1.12.0` 에 그대로 둡니다.

| | 2.1.0 |
|---|---|
| 핸들러 계약 | 그대로 — `runpod.serverless.start({"handler": ...})`, 같은 `error` · `refresh_worker` 처리, 같은 오류 페이로드 필드 |
| `register_prestart_hook(fn)` | 신규. 큐, 로컬 테스트, 호스팅 API 모드에서 핸들러 실행 전에 한 번 실행되며, `start()` 설정에 `prestart_timeout` 을 줄 수 있습니다. 프로덕션에서는 훅이 도는 동안에도 큐에서 작업을 받습니다. realtime 모드는 거부하고, 호스팅 API 모드는 `rp_api_concurrency=1` 이 필요합니다 |
| import 시 fitness check | Serverless 워커 프로세스 안에서는 `import runpod` 가 기동 fitness check 를 실행합니다. `--test_input`, `--rp_serve_api`, realtime 모드에서는 하지 않습니다 |
| 오류에 담기는 핸들러 로그 | `RUNPOD_LOG_CAPTURE=all` 이면 stdout · stderr 의 마지막 16 KiB 가 오류 페이로드에 `logs` 로 들어갑니다. 기본값 `auto` 는 핸들러에 대해 하지 않습니다 |

워커를 2.x 로 옮기는 것은 버전 숫자만 바꾸는 일이 아니라 재빌드와 재실행입니다. 이미지가 바뀌므로 이 페이지의 측정값은 더 이상 그 워커를 설명하지 않습니다.

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

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

SDK 中**在你的 worker 容器内部运行**的那一半。另一半见 [Client SDK]({{ '/sdk/client/' | relative_url }})。

内容读自已安装的 1.11.0 和 1.12.0 源码，并逐一运行确认。行为出人意料之处，附上了实际输出。

### 2.x 中的变化

于 2026-11-05 读取已安装的 2.1.0 源码，并与 1.12.0 对比。没有在 2.x 上构建或运行任何 worker；实验的 worker 仍停留在 `runpod~=1.12.0`，即部署和测量时所用的版本。

| | 2.1.0 |
|---|---|
| handler 契约 | 不变——`runpod.serverless.start({"handler": ...})`，同样的 `error` 和 `refresh_worker` 处理，同样的错误负载字段 |
| `register_prestart_hook(fn)` | 新增。在队列、本地测试和托管 API 模式下，钩子在 handler 执行前运行一次，可在 `start()` 配置中设置可选的 `prestart_timeout`。生产环境中钩子运行期间队列仍继续接收作业。realtime 模式拒绝钩子；托管 API 模式需要 `rp_api_concurrency=1` |
| import 时的 fitness check | 在 Serverless worker 进程内，`import runpod` 会运行启动 fitness check——在 `--test_input` 或 `--rp_serve_api` 下不会，在 realtime 模式下也不会 |
| 错误中的 handler 日志 | `RUNPOD_LOG_CAPTURE=all` 会把 stdout 和 stderr 的最后 16 KiB 作为 `logs` 加入错误负载。默认值 `auto` 对 handler 不这样做 |

把 worker 迁移到 2.x 是重新构建并重新运行，而不只是改版本号：镜像变了，这些页面上的测量值就不再描述它。

### 启动 fitness check

在你的 handler 被调用之前，worker 会先验证它所落到的机器。检查失败时以 `os._exit(1)` 终止进程，由编排器把作业路由到别处，而不是让它在坏硬件上慢慢失败。约 1,125 行，是 worker 这一半中最大的部分，无论你是否要求都会运行。

| 始终 | 仅在有 GPU 时 |
|---|---|
| 内存、磁盘、网络 | CUDA 版本、CUDA 初始化、计算基准、GPU 健康检查二进制 |

阈值是环境变量，所以在端点上设置：`RUNPOD_MIN_MEMORY_GB`（4.0）、`RUNPOD_MIN_DISK_PERCENT`（10.0）、`RUNPOD_MIN_CUDA_VERSION`（11.8），以及用来关闭整组检查的 `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS`。

用装饰器添加自己的检查——同步或异步均可，抛出异常即失败：

```python
@runpod.serverless.register_fitness_check
def check_weights_present():
    if not os.path.exists("/runpod-volume/model.safetensors"):
        raise RuntimeError("model weights missing")
```

<div class="warn" markdown="1">
**失败是 `os._exit(1)`，不是异常**——没有 `finally`，没有清理。这是有意为之：无法提供服务的 worker 应当消失，而不是留下来继续接收作业。
</div>

### 本地 API 服务器

`--rp_serve_api` 会启动一个模仿端点的 FastAPI 应用。以下读自运行中服务器自身的 OpenAPI 文档：

| 路由 | 方法 |
|---|---|
| `/run` | POST |
| `/runsync` | POST |
| `/status/{job_id}` | **POST** |
| `/stream/{job_id}` | **POST** |

文档位于 `/`，不是 `/docs`——该路径是 307 重定向。

<div class="warn" markdown="1">
**`/status` 在本地用 POST，在平台上用 GET。** 对本地服务器 `GET /status/{id}` 返回 **405**；`POST` 返回 200。真实 API 文档写的是 GET。请按目标选择方法，而不是凭记忆。
</div>

### SDK 如何知道自己不在生产环境

```python
IS_LOCAL_TEST = os.environ.get("RUNPOD_WEBHOOK_GET_JOB", None) is None
```

由一个变量决定。平台会设置它；没有它就意味着本地。`rp_scale` 读取这个标志来决定是否采用 `jobs_fetcher` / `jobs_handler` 覆盖——在本地测试之外它们会被忽略，这就是这些配置键在生产环境中看似无效的原因。

### 环境变量

由平台设置、可在 handler 中读取：`RUNPOD_POD_ID`（worker id，本地为随机 UUID）、`RUNPOD_POD_HOSTNAME`、`RUNPOD_ENDPOINT_ID`、`RUNPOD_AI_API_KEY`，以及四个 webhook URL——`GET_JOB`、`PING`、`POST_OUTPUT`、`POST_STREAM`。

由你调整：

| 变量 | 默认值 |
|---|---|
| `RUNPOD_PING_INTERVAL` | `10000` ms |
| `RUNPOD_MIN_MEMORY_GB` | `4.0` |
| `RUNPOD_MIN_DISK_PERCENT` | `10.0` |
| `RUNPOD_MIN_CUDA_VERSION` | `11.8` |
| `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS` | 未设置 |
| `RUNPOD_LOG_LEVEL` / `RUNPOD_DEBUG_LEVEL` / `UVICORN_LOG_LEVEL` | — |

心跳会向 `RUNPOD_WEBHOOK_PING` 发送 `{"job_id": <ids in flight>, "runpod_version": …}`。控制台对 worker 正在做什么的了解来自这里，而不是来自你的 handler。

### worker 循环

`JobScaler` 在 worker 的整个生命周期中运行三个协程：`get_jobs` 填充一个有界队列，`run_jobs` 把每个作业交给你的 handler，`monitor_stop_signals` 监视取消请求。

**并发变更要等 worker 排空。** `set_scale` 每秒轮询一次，直到没有进行中的作业才调整队列大小，因此随负载变化的 `concurrency_modifier` 会在下一个空闲时刻生效，而不是立即生效。

**取消作业取消的是它的任务，而不是 worker。** 客户端的 `job.cancel()` 会在你的 handler 下一个 `await` 处抛出 `CancelledError`；同一 worker 上的其他作业继续运行。没有 `await` 点的同步 handler 无法以这种方式中断。

SIGTERM 和 SIGINT 会设置一个关闭事件，因此循环会收尾结束，而不是在作业中途死掉。

### 日志

六个级别——`NOTSET`、`TRACE`、`DEBUG`、`INFO`、`WARN`、`ERROR`——默认 `DEBUG`，通过 `RUNPOD_LOG_LEVEL` 设置。

**格式会自行切换。** 设置了 `RUNPOD_ENDPOINT_ID` 时（在平台上就是如此），每一行都是 JSON：

```json
{"requestId": "<job id>", "message": "...", "level": "INFO"}
```

在本地你得到的是 `INFO   | message`。同样的调用，不同的形态——这就是控制台日志和本地日志看起来不一样的原因。超过 **4096 个字符**的消息会从中间截断——SDK 的注释写的是 10MB，但常量是 4096。一个堆栈跟踪就很容易超过。

<div class="note" markdown="1">
`log.secret(name, value)` 会遮盖除首尾字符以外的所有内容。它无法遮盖非常短的值：`"ab"` 打印为 `ab`，`"a"` 打印为 `aa`，因为掩码是 `"*" * (len - 2)`。
</div>

### 模型可以存放的第四个位置

SDK 1.12.0 新增了 `VolumeCache`，介于“每次冷启动都下载”和“打包进镜像”之间。它把选定的目录镜像到已挂载的 Network Volume 上：

```python
from runpod.serverless import VolumeCache

with VolumeCache(dirs=["/root/.cache/huggingface"]):
    model = load_model()      # downloads land in the cached directory
```

进入时从卷填充容器；退出时把新文件同步回去。它需要挂载在 `/runpod-volume` 的 Network Volume，并按 `RUNPOD_ENDPOINT_ID` 划分镜像范围。

| | 端点 **Model** 字段 | `VolumeCache` |
|---|---|---|
| 范围 | Hugging Face 模型 id | 任意目录 |
| 存储 | Runpod 的主机缓存 | 你挂载的 Network Volume |
| 配置 | 一个控制台字段 | Network Volume 加代码 |

未挂载卷时，所有操作都是 no-op，并且全程尽力而为——失败会降级为冷 worker，而不会向你的 handler 抛出异常。

### 下载调用方提供的 URL

`download_files_from_urls(job_id, urls)` 把作业输入中的 URL 下载为本地文件。从 1.12.0 起它拒绝私有地址空间：回环、链路本地——包括 `169.254.169.254` 元数据端点——RFC1918，以及 CGNAT `100.64.0.0/10`。连接被固定到经过验证的 IP，因此解析到私有地址的主机名会被拒绝，而不是被跟随。

<div class="warn" markdown="1">
如果你的 handler 原本合法地从内部主机获取数据，在 1.12.0 上会失效。作业输入由攻击者控制：没有这项限制，调用方就能让你的 worker 指向实例元数据。
</div>

### 为 handler 计时

`--rp_debugger` 用 `LineTimer`（上下文管理器）和 `FunctionTimer`（装饰器）收集耗时，并在 `output` 中以 `rp_debugger` 键返回，与 `system_info` 和 `ready_delay_ms` 并列。

<div class="warn" markdown="1">
**它在本地不起任何作用。** 注入逻辑位于 `handle_job`，只有生产循环才会调用它。普通的 `python handler.py` 和 `--rp_serve_api` 都直接调用 `run_job`，跳过了它——已验证：有无该标志，输出逐字节相同。请在已部署的端点上使用。
</div>

### handler 工具

| 导入 | 用途 |
|---|---|
| `rp_validator.validate` | 类型、默认值、约束 lambda，拒绝未知键 |
| `utils.download_files_from_urls` | 把调用方提供的 URL 下载为本地文件 |
| `utils.upload_file_to_bucket` / `upload_in_memory_object` | S3 兼容存储，返回 URL |
| `rp_progress.progress_update` | 可通过 `/status` 查看，在后台线程运行 |

<div class="note" markdown="1">
**这就是应对 20 MB 返回限制的办法**——上传负载并返回其 URL。凭据来自 `BUCKET_ENDPOINT_URL`、`BUCKET_ACCESS_KEY_ID` 和 `BUCKET_SECRET_ACCESS_KEY`。未设置这些时，SDK 会改为写到本地：开发时方便，在生产环境中却悄无声息地毫无用处。
</div>

### 契约

```python
import runpod

def handler(job):
    return {"result": job["input"]["x"] * 2}

runpod.serverless.start({"handler": handler})
```

`start()` 接收的是配置字典，而不只是一个 handler，并且**不会返回**——它接管进程，每个作业调用一次你的 handler。handler 至少会收到 `id` 和 `input`；`job["input"]` 就是调用方发送的原样内容。

### 返回值——有两个键是控制信号

SDK 会检查你的返回值，把两个键作为控制信号而不是数据取出：

| 你返回 | SDK 生成 | 效果 |
|---|---|---|
| `{"ok": True}` | `{"output": {"ok": True}}` | 正常成功 |
| `{"ok": False, "error": "bad input"}` | `{"output": {"ok": False}, "error": "bad input"}` | **作业标记为 FAILED** |
| `{"ok": True, "refresh_worker": True}` | `{"output": {"ok": True}, "stopPod": True}` | 成功，worker 被回收 |
| `{}` | `{}` | `output` 被整个丢弃 |
| `"just a string"` | `{"output": "just a string"}` | 非字典会被包装 |

<div class="warn" markdown="1">
**`error` 不是普通字段。** 返回字典中任何位置出现 `error` 键都会使作业失败：

```
DEBUG | run_job return: {'output': {'ok': False}, 'error': 'bad input'}
ERROR | Job local_test failed with error: bad input
```

所以不能把 `error` 当作普通输出——`{"error": "just a warning"}` 会让一个本应成功的作业失败。请换个名字。
</div>

### 异常

SDK 会捕获异常，worker 存活，作业失败并返回一个 JSON，其中包含 `error_type`、`error_message`、`error_traceback`、`hostname`、`worker_id` 和 `runpod_version`。

<div class="warn" markdown="1">
**完整的堆栈跟踪会发给调用方**，包括绝对路径和源代码行。请捕获预期中的失败，改为返回一个受控的 `error` 字符串。
</div>

### 流式输出

用 `yield` 代替 `return`，每个部分结果都会作为单独的 `{"output": ...}` 发送。同步和异步生成器都可以。加上 `return_aggregate_stream: True`，`/runsync` 和 `/status` 也能返回汇总后的输出，而不只是 `/stream`。

<div class="note" markdown="1">
本地 `test_input.json` 运行**不会**测试到流式输出——生成器未被消费，原样返回为 `{'output': <generator object ...>}`。请针对真实端点或 `--rp_serve_api` 测试。
</div>

### 其他配置键

| 键 | 用途 |
|---|---|
| `handler` | 必需。同步、异步、生成器或异步生成器 |
| `return_aggregate_stream` | 汇总生成器输出，供 `/runsync` 和 `/status` 返回 |
| `concurrency_modifier` | `fn(current: int) -> int`——一个 worker 同时处理多个作业 |

### 工具箱中的其他内容

- **`progress_update(job, msg)`**——调用方可通过 `/status` 看到，在后台线程运行。
- **`rp_validator.validate(input, schema)`**——类型检查、默认值、`constraints` lambda，拒绝意外的键。
- **`download_files_from_urls` / `upload_file_to_bucket`**——用于调用方提供的 URL 和大型结果。
- **`register_fitness_check`**——启动检查；失败会让 worker 退出，由编排器重启。
- **超过 20 MB 的返回体**会触发一条 SDK 提示，建议改用 S3。只是一行日志，并不强制——但仍应把它当作限制。

### 本地测试标志

| 标志 | 效果 |
|---|---|
| *（无）* | 运行一次 `test_input.json` 后退出 |
| `--rp_serve_api` | 位于 `http://localhost:8000` 的本地 API，形态与真实端点相同 |
| `--rp_api_port` / `--rp_api_host` / `--rp_api_concurrency` | 绑定和 worker 设置 |
| `--rp_log_level` | `ERROR`、`WARN`、`INFO`、`DEBUG` |
| `--rp_debugger` | 挂接 SDK 调试器 |

[在仓库中查看完整参考 →](https://github.com/litkhai/runpod-hols/blob/main/sdk/worker.md)

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

SDK のうち、**worker コンテナの中で動く**半分です。もう半分は [Client SDK]({{ '/sdk/client/' | relative_url }}) です。

インストール済みの 1.11.0 と 1.12.0 のソースを読み、各ケースを実行して確認しました。挙動が意外な箇所には、実際の出力を載せています。

### 2.x での変更点

2026-11-05 にインストール済みの 2.1.0 のソースを読み、1.12.0 と比較しました。2.x で worker をビルド・実行はしていません。ラボの worker は、デプロイと計測に使ったバージョンである `runpod~=1.12.0` のままです。

| | 2.1.0 |
|---|---|
| handler の契約 | 変更なし。`runpod.serverless.start({"handler": ...})`、同じ `error` と `refresh_worker` の扱い、同じエラーペイロードのフィールド |
| `register_prestart_hook(fn)` | 新規。キュー、ローカルテスト、ホスト型 API の各モードで handler 実行前に一度だけ実行され、`start()` の設定で任意の `prestart_timeout` を指定できます。本番ではフックの実行中もキューからのジョブ受け付けが続きます。realtime モードは拒否し、ホスト型 API モードでは `rp_api_concurrency=1` が必要です |
| import 時の fitness check | Serverless worker プロセス内では `import runpod` が起動時の fitness check を実行します。`--test_input` や `--rp_serve_api` の下では実行されず、realtime モードでも実行されません |
| エラーに含まれる handler ログ | `RUNPOD_LOG_CAPTURE=all` にすると、stdout と stderr の最後の 16 KiB がエラーペイロードに `logs` として追加されます。デフォルトの `auto` は handler に対してはこれを行いません |

worker を 2.x に移すのはバージョン番号の変更ではなく、再ビルドと再実行です。イメージが変わるので、これらのページの計測値はもうその worker を表しません。

### 起動時の fitness check

handler が呼ばれる前に、worker は自分が配置されたマシンを検証します。チェックに失敗すると `os._exit(1)` でプロセスを終了し、オーケストレーターがジョブを別の場所に回します。不良ハードウェアの上でゆっくり失敗させないためです。約 1,125 行と worker 側で最大の部分で、求めなくても実行されます。

| 常に | GPU がある場合のみ |
|---|---|
| メモリ、ディスク、ネットワーク | CUDA バージョン、CUDA 初期化、演算ベンチマーク、GPU ヘルスバイナリ |

しきい値は環境変数なので、エンドポイントで設定します：`RUNPOD_MIN_MEMORY_GB`（4.0）、`RUNPOD_MIN_DISK_PERCENT`（10.0）、`RUNPOD_MIN_CUDA_VERSION`（11.8）、グループ単位で無効にするには `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS`。

デコレーターで独自のチェックを追加できます。同期でも非同期でもよく、例外を投げれば失敗になります。

```python
@runpod.serverless.register_fitness_check
def check_weights_present():
    if not os.path.exists("/runpod-volume/model.safetensors"):
        raise RuntimeError("model weights missing")
```

<div class="warn" markdown="1">
**失敗は例外ではなく `os._exit(1)` です。** `finally` もクリーンアップも実行されません。意図的な動作です。サービスできない worker は、居残ってジョブを受け付けるのではなく消えるべきだからです。
</div>

### ローカル API サーバー

`--rp_serve_api` はエンドポイントを模した FastAPI アプリを起動します。以下は実行中のサーバー自身の OpenAPI ドキュメントから読み取ったものです。

| ルート | メソッド |
|---|---|
| `/run` | POST |
| `/runsync` | POST |
| `/status/{job_id}` | **POST** |
| `/stream/{job_id}` | **POST** |

ドキュメントは `/docs` ではなく `/` にあります。`/docs` は 307 リダイレクトです。

<div class="warn" markdown="1">
**`/status` はローカルでは POST、プラットフォームでは GET です。** ローカルサーバーに `GET /status/{id}` を送ると **405**、`POST` なら 200 が返ります。実際の API は GET と文書化されています。メソッドは記憶ではなく対象に合わせて選んでください。
</div>

### SDK はどうやって本番でないと判断するか

```python
IS_LOCAL_TEST = os.environ.get("RUNPOD_WEBHOOK_GET_JOB", None) is None
```

変数ひとつで決まります。プラットフォームが設定し、なければローカルです。`rp_scale` はこのフラグを見て `jobs_fetcher` / `jobs_handler` の上書きを反映するかどうかを決めます。ローカルテスト以外では無視されるため、本番ではこれらの設定キーが効いていないように見えます。

### 環境変数

プラットフォームが設定し、handler から読めるもの：`RUNPOD_POD_ID`（worker id、ローカルではランダムな UUID）、`RUNPOD_POD_HOSTNAME`、`RUNPOD_ENDPOINT_ID`、`RUNPOD_AI_API_KEY`、そして 4 つの webhook URL（`GET_JOB`、`PING`、`POST_OUTPUT`、`POST_STREAM`）。

自分で調整するもの：

| 変数 | デフォルト |
|---|---|
| `RUNPOD_PING_INTERVAL` | `10000` ms |
| `RUNPOD_MIN_MEMORY_GB` | `4.0` |
| `RUNPOD_MIN_DISK_PERCENT` | `10.0` |
| `RUNPOD_MIN_CUDA_VERSION` | `11.8` |
| `RUNPOD_SKIP_GPU_CHECK` / `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS` | 未設定 |
| `RUNPOD_LOG_LEVEL` / `RUNPOD_DEBUG_LEVEL` / `UVICORN_LOG_LEVEL` | — |

ハートビートは `RUNPOD_WEBHOOK_PING` に `{"job_id": <ids in flight>, "runpod_version": …}` を送ります。worker が何をしているかというコンソールの表示は、handler ではなくこれに基づいています。

### worker ループ

`JobScaler` は worker が生きている間、3 つのコルーチンを動かします。`get_jobs` がサイズ上限のあるキューを埋め、`run_jobs` が各ジョブを handler に渡し、`monitor_stop_signals` がキャンセルを監視します。

**並行数の変更は worker が空くのを待ちます。** `set_scale` は処理中のジョブがなくなるまで 1 秒ごとにポーリングしてからキューのサイズを変えるため、負荷に反応する `concurrency_modifier` は即座ではなく次のアイドル時点で反映されます。

**ジョブのキャンセルは worker ではなく、そのジョブのタスクをキャンセルします。** クライアントからの `job.cancel()` は handler の次の `await` で `CancelledError` を発生させ、同じ worker 上の他のジョブは動き続けます。`await` ポイントのない同期 handler はこの方法では中断できません。

SIGTERM と SIGINT はシャットダウンイベントをセットするので、ループはジョブの途中で落ちるのではなく処理を終えてから終了します。

### ロギング

レベルは 6 つ（`NOTSET`、`TRACE`、`DEBUG`、`INFO`、`WARN`、`ERROR`）で、デフォルトは `DEBUG`、`RUNPOD_LOG_LEVEL` で設定します。

**フォーマットは自動で切り替わります。** `RUNPOD_ENDPOINT_ID` が設定されていると（プラットフォーム上では設定されています）、すべての行が JSON になります。

```json
{"requestId": "<job id>", "message": "...", "level": "INFO"}
```

ローカルでは `INFO   | message` になります。同じ呼び出しでも形が違うので、コンソールのログとローカルのログは見た目が異なります。**4096 文字**を超えるメッセージは中央が切り詰められます。SDK のコメントには 10MB とありますが、定数は 4096 です。スタックトレースなら簡単に超えます。

<div class="note" markdown="1">
`log.secret(name, value)` は先頭と末尾の 1 文字以外をマスクします。非常に短い値は伏せられません。マスクが `"*" * (len - 2)` なので、`"ab"` は `ab`、`"a"` は `aa` と出力されます。
</div>

### モデルを置ける 4 つ目の場所

SDK 1.12.0 で `VolumeCache` が追加されました。「コールドスタートのたびにダウンロード」と「イメージに焼き込む」の中間に位置し、指定したディレクトリをマウントされた Network Volume にミラーします。

```python
from runpod.serverless import VolumeCache

with VolumeCache(dirs=["/root/.cache/huggingface"]):
    model = load_model()      # downloads land in the cached directory
```

開始時にボリュームからコンテナへ展開し、終了時に新しいファイルを書き戻します。`/runpod-volume` にマウントされた Network Volume が必要で、ミラーの範囲は `RUNPOD_ENDPOINT_ID` で分けられます。

| | エンドポイントの **Model** フィールド | `VolumeCache` |
|---|---|---|
| 範囲 | Hugging Face のモデル id | 任意のディレクトリ |
| 保存先 | Runpod のホストキャッシュ | 自分でアタッチする Network Volume |
| 設定 | コンソールのフィールドひとつ | Network Volume とコード |

ボリュームがアタッチされていなければすべての操作は no-op で、全体がベストエフォートです。失敗しても handler に例外が上がることはなく、コールドな worker に格下げされるだけです。

### 呼び出し元が渡す URL のダウンロード

`download_files_from_urls(job_id, urls)` はジョブ入力の URL をローカルファイルに取得します。1.12.0 以降はプライベートアドレス空間を拒否します：ループバック、リンクローカル（`169.254.169.254` のメタデータエンドポイントを含む）、RFC1918、CGNAT `100.64.0.0/10`。接続は検証済みの IP に固定されるため、プライベートアドレスに解決されるホスト名は追従されずに拒否されます。

<div class="warn" markdown="1">
handler が正当な理由で内部ホストから取得していた場合、1.12.0 では動かなくなります。ジョブ入力は攻撃者が制御できる値です。これがなければ、呼び出し元が worker をインスタンスメタデータに向けることができてしまいます。
</div>

### handler の計時

`--rp_debugger` は `LineTimer`（コンテキストマネージャー）と `FunctionTimer`（デコレーター）で時間を計測し、`output` 内の `rp_debugger` キーとして `system_info`、`ready_delay_ms` と並べて返します。

<div class="warn" markdown="1">
**ローカルでは何もしません。** 注入処理は本番ループだけが呼ぶ `handle_job` の中にあります。素の `python handler.py` も `--rp_serve_api` も `run_job` を直接呼ぶためこれを通りません。検証済みで、フラグの有無にかかわらず出力はバイト単位で同一でした。デプロイ済みのエンドポイントで使ってください。
</div>

### handler ユーティリティ

| import | 用途 |
|---|---|
| `rp_validator.validate` | 型、デフォルト値、制約 lambda、未知のキーを拒否 |
| `utils.download_files_from_urls` | 呼び出し元が渡す URL をローカルファイルに |
| `utils.upload_file_to_bucket` / `upload_in_memory_object` | S3 互換ストレージ、URL を返す |
| `rp_progress.progress_update` | `/status` から見える、別スレッドで実行 |

<div class="note" markdown="1">
**これが 20 MB の返却上限への答えです。** ペイロードをアップロードして、その URL を返してください。認証情報は `BUCKET_ENDPOINT_URL`、`BUCKET_ACCESS_KEY_ID`、`BUCKET_SECRET_ACCESS_KEY` から取得されます。これらが未設定だと SDK は代わりにローカルへ書き込みます。開発中は便利ですが、本番では黙って役に立ちません。
</div>

### 契約

```python
import runpod

def handler(job):
    return {"result": job["input"]["x"] * 2}

runpod.serverless.start({"handler": handler})
```

`start()` は handler だけでなく設定の dict を受け取り、**戻りません。** プロセスを引き継ぎ、ジョブごとに handler を 1 回呼び出します。handler は少なくとも `id` と `input` を受け取り、`job["input"]` は呼び出し元が送ったものそのままです。

### 戻り値：2 つのキーは制御シグナルです

SDK は戻り値を検査し、2 つのキーをデータではなく制御シグナルとして取り出します。

| 返す値 | SDK が生成 | 効果 |
|---|---|---|
| `{"ok": True}` | `{"output": {"ok": True}}` | 通常の成功 |
| `{"ok": False, "error": "bad input"}` | `{"output": {"ok": False}, "error": "bad input"}` | **ジョブが FAILED になる** |
| `{"ok": True, "refresh_worker": True}` | `{"output": {"ok": True}, "stopPod": True}` | 成功、worker はリサイクルされる |
| `{}` | `{}` | `output` がまるごと消える |
| `"just a string"` | `{"output": "just a string"}` | dict 以外はラップされる |

<div class="warn" markdown="1">
**`error` は普通のフィールドではありません。** 返す dict のどこかに `error` キーがあると、ジョブは失敗します。

```
DEBUG | run_job return: {'output': {'ok': False}, 'error': 'bad input'}
ERROR | Job local_test failed with error: bad input
```

そのため `error` を通常の出力には使えません。`{"error": "just a warning"}` は本来成功するはずのジョブを失敗させます。別の名前にしてください。
</div>

### 例外

SDK が捕捉し、worker は生き残り、ジョブは `error_type`、`error_message`、`error_traceback`、`hostname`、`worker_id`、`runpod_version` を含む JSON で失敗します。

<div class="warn" markdown="1">
**完全なトレースバックが呼び出し元に渡ります。** 絶対パスやソース行も含めてです。想定内の失敗は捕捉し、代わりに制御された `error` 文字列を返してください。
</div>

### ストリーミング

`return` の代わりに `yield` すると、部分結果がそれぞれ個別の `{"output": ...}` として送られます。同期・非同期のジェネレーターどちらも使えます。`return_aggregate_stream: True` を加えると、`/stream` だけでなく `/runsync` と `/status` でも集約された出力を返せます。

<div class="note" markdown="1">
ローカルの `test_input.json` 実行ではストリーミングは検証**できません。** ジェネレーターは消費されないまま `{'output': <generator object ...>}` として返ってきます。実際のエンドポイントか `--rp_serve_api` でテストしてください。
</div>

### その他の設定キー

| キー | 用途 |
|---|---|
| `handler` | 必須。同期、非同期、ジェネレーター、非同期ジェネレーター |
| `return_aggregate_stream` | ジェネレーターの出力を集約し `/runsync` と `/status` で返す |
| `concurrency_modifier` | `fn(current: int) -> int`：1 つの worker が複数のジョブを同時に処理 |

### ツールボックスのその他

- **`progress_update(job, msg)`**：呼び出し元が `/status` で確認でき、バックグラウンドスレッドで実行されます。
- **`rp_validator.validate(input, schema)`**：型チェック、デフォルト値、`constraints` の lambda、想定外のキーの拒否。
- **`download_files_from_urls` / `upload_file_to_bucket`**：呼び出し元が渡す URL と大きな結果のために。
- **`register_fitness_check`**：起動時チェック。失敗すると worker が終了し、オーケストレーターが再起動します。
- **20 MB を超える返却ボディ**では、代わりに S3 を勧める SDK のヒントが出ます。ログ行であって強制ではありませんが、それでも上限として扱ってください。

### ローカルテストのフラグ

| フラグ | 効果 |
|---|---|
| *（なし）* | `test_input.json` を 1 回実行して終了 |
| `--rp_serve_api` | `http://localhost:8000` のローカル API。実際のエンドポイントと同じ形 |
| `--rp_api_port` / `--rp_api_host` / `--rp_api_concurrency` | バインドと worker の設定 |
| `--rp_log_level` | `ERROR`、`WARN`、`INFO`、`DEBUG` |
| `--rp_debugger` | SDK デバッガーをアタッチ |

[リポジトリで完全なリファレンスを見る →](https://github.com/litkhai/runpod-hols/blob/main/sdk/worker.md)

</div>
