# Worker SDK — Code That Runs Inside the Container

[English](#english) | [한국어](#한국어)

> The half of the SDK that runs **inside your worker container**. The other half — calling and managing Runpod from your own machine — is in [client.md](./client.md).
>
> Read out of the installed SDK source (`runpod` 1.11.0) and confirmed by running it. Where behaviour is surprising, the observed output is included.
>
> SDK 중 **워커 컨테이너 안에서 도는** 절반입니다. 나머지 절반, 즉 내 컴퓨터에서 Runpod 을 호출하고 관리하는 부분은 [client.md](./client.md) 에 있습니다.
>
> 설치된 SDK 소스(`runpod` 1.11.0)를 직접 읽고 실행해 확인했습니다. 동작이 직관과 다른 부분은 실제 출력을 함께 실었습니다.

---

## English

### What this half contains

| Area | Modules | Roughly |
|---|---|---|
| Handler contract | `rp_job`, `worker`, `serverless/__init__` | 580 lines |
| Startup fitness checks | `rp_fitness`, `rp_gpu_fitness`, `rp_system_fitness` | 1,125 lines |
| Handler utilities | `rp_validator`, `rp_download`, `rp_upload`, `rp_model_cache`, `rp_progress` | 740 lines |
| Internals | `rp_scale`, `worker_state`, `rp_ping`, `rp_http` | 800 lines |
| Local development | `rp_fastapi`, `rp_debugger`, `rp_local` | 700 lines |

### Startup fitness checks

Before your handler is ever called, the worker validates the machine it landed on. If a check fails the process is killed with `os._exit(1)`, and the orchestrator places the job on a different worker rather than letting it fail slowly on bad hardware.

This is the largest part of the worker half — about 1,125 lines — and it runs whether or not you ask for it.

**What runs automatically**

| Check | When |
|---|---|
| Memory availability | Always |
| Disk space | Always |
| Network connectivity | Always |
| CUDA version | Only if a GPU is detected |
| CUDA device initialization | Only if a GPU is detected |
| GPU compute benchmark | Only if a GPU is detected |
| GPU health via a bundled test binary | Only if a GPU is detected |

**Tuning them**

Every threshold is an environment variable, so you set them on the endpoint rather than in code:

| Variable | Default |
|---|---|
| `RUNPOD_MIN_MEMORY_GB` | `4.0` |
| `RUNPOD_MIN_DISK_PERCENT` | `10.0` |
| `RUNPOD_MIN_CUDA_VERSION` | `11.8` |
| `RUNPOD_NETWORK_CHECK_TIMEOUT` | `5` |
| `RUNPOD_GPU_BENCHMARK_TIMEOUT` | `2` |
| `RUNPOD_GPU_TEST_TIMEOUT` | `30` |
| `RUNPOD_SKIP_GPU_CHECK` | unset — `true` disables the GPU check |
| `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS` | unset — `true` disables the system checks |

**Adding your own**

```python
@runpod.serverless.register_fitness_check
def check_weights_present():
    if not os.path.exists("/runpod-volume/model.safetensors"):
        raise RuntimeError("model weights missing")
```

Async functions work too — the decorator detects them with `inspect.iscoroutinefunction()`. Raise to fail; returning normally passes.

> **Failure is `os._exit(1)`, not an exception.** No `finally` blocks, no cleanup handlers. That is deliberate — a worker that cannot serve should disappear immediately rather than linger and accept jobs.

> This is the difference between a job failing on your handler and never being routed to a broken worker at all. Worth a check for anything your handler assumes exists.

### Handler utilities

Small helpers that save writing the same code in every worker.

| Import | Use |
|---|---|
| `rp_validator.validate(input, schema)` | Types, defaults, `constraints` lambdas, rejects unexpected keys |
| `utils.download_files_from_urls(job_id, urls)` | Fetch caller-supplied URLs to local files |
| `utils.upload_file_to_bucket(name, path)` | Push a file to S3-compatible storage, get a URL back |
| `utils.upload_in_memory_object(name, bytes)` | Same, without touching disk |
| `rp_progress.progress_update(job, msg)` | Visible to the caller via `/status`, runs off-thread |
| `rp_cuda` | A little `torch.cuda`-shaped information without importing torch |

Upload reads its credentials from the environment, so the same handler works against any S3-compatible bucket:

```
BUCKET_ENDPOINT_URL
BUCKET_ACCESS_KEY_ID
BUCKET_SECRET_ACCESS_KEY
```

> **This is the answer to the 20 MB return limit.** Rather than returning a large payload, upload it and return the URL. If the bucket variables are absent the SDK falls back to writing locally, which is convenient in development and silently useless in production — check that they are set.

### Internals worth knowing

You do not call these, but they explain what you see in logs and billing.

| Module | What it does |
|---|---|
| `rp_ping` | Heartbeat to Runpod, carrying the jobs currently in flight. This is how the console knows a worker is alive |
| `worker_state` | Tracks jobs in progress and reads the `RUNPOD_*` environment variables. Source of `RUNPOD_POD_ID`, which the labs return as `worker_id` |
| `rp_scale` | The job-fetch loop and the concurrency the `concurrency_modifier` adjusts |
| `rp_http` | The worker's own HTTP path back to Runpod — separate from the client SDK's, and notably it does **not** carry the agent-detecting User-Agent |

### Local development

| Tool | Invocation |
|---|---|
| `rp_local` | Default. Reads `test_input.json`, runs one job, exits |
| `rp_fastapi` | `--rp_serve_api`. A uvicorn server mirroring the real endpoint's shape, with docs at `/docs` |
| `rp_debugger` | `--rp_debugger`. Attaches the SDK's timing debugger |

### The handler contract

```python
import runpod

def handler(job):
    return {"result": job["input"]["x"] * 2}

runpod.serverless.start({"handler": handler})
```

`start()` takes a config dict, not just a handler. `handler` is the only required key; the others are listed further down.

`start()` **does not return** — it takes over the process, polls Runpod's job queue, and calls your handler once per job. Anything after it never runs.

### What the handler receives

A dict with at least `id` and `input`. `job["input"]` is exactly the JSON object the caller sent under `"input"`.

```python
{"id": "abc-123", "input": {"name": "Runpod"}}
```

### What the handler returns — the part worth knowing

The SDK inspects your return value and **treats two dict keys as control signals**, not data. Verified by running each case:

| You return | SDK produces | Effect |
|---|---|---|
| `{"ok": True}` | `{"output": {"ok": True}}` | Normal success |
| `{"ok": False, "error": "bad input"}` | `{"output": {"ok": False}, "error": "bad input"}` | **Job is marked FAILED** |
| `{"ok": True, "refresh_worker": True}` | `{"output": {"ok": True}, "stopPod": True}` | Success, then the worker is recycled |
| `{}` | `{}` | The `output` key is dropped entirely |
| `"just a string"` | `{"output": "just a string"}` | Non-dicts are wrapped |

<br>

> **`error` is not a normal field.** Putting an `error` key anywhere in a returned dict fails the job:
>
> ```
> DEBUG | run_job return: {'output': {'ok': False}, 'error': 'bad input'}
> ERROR | Job local_test failed with error: bad input
> ```
>
> That is usually what you want for genuine failures. But it means you cannot use `error` as an ordinary output field — `{"error": None}` would be popped, and `{"error": "warning text"}` would fail an otherwise successful job. Name it something else.

> **`refresh_worker` recycles the worker after the job.** Useful when a job leaves the process in a bad state — leaked GPU memory, a wedged library. It is also expensive: the next request pays a full cold start.

### Raising an exception

The SDK catches it. The worker survives, and the job fails with a JSON blob:

```json
{"error_type": "<class 'ValueError'>",
 "error_message": "boom",
 "error_traceback": "Traceback (most recent call last): ...",
 "hostname": "...", "worker_id": "...", "runpod_version": "1.11.0"}
```

> **The full traceback is returned to the caller**, including absolute file paths and source lines. Fine for a lab, worth thinking about for anything public — catch expected failures and return a controlled `error` string instead.

### Streaming with a generator

Yield instead of returning, and each partial is sent as its own `{"output": ...}`. Both sync and async generators work.

```python
def handler(job):
    for token in generate():
        yield {"token": token}

runpod.serverless.start({"handler": handler, "return_aggregate_stream": True})
```

`return_aggregate_stream: True` also makes the collected output available from `/runsync` and `/status`, instead of only over `/stream`.

> **Local testing does not exercise this.** Running with `test_input.json` routes through the non-streaming path, and the generator object is returned unconsumed:
> ```
> DEBUG | run_job return: {'output': <generator object gen at 0x...>}
> ```
> Test generators against a real endpoint, or via `--rp_serve_api`.

### Config keys `start()` accepts

| Key | Purpose |
|---|---|
| `handler` | Required. Sync, async, generator or async generator |
| `return_aggregate_stream` | Collect generator output so `/runsync` and `/status` can return it |
| `concurrency_modifier` | `fn(current: int) -> int`, letting one worker take several jobs at once |
| `rp_args` | Populated from CLI flags; you rarely set this yourself |

`jobs_fetcher`, `jobs_handler`, `stop_signals_fetcher` and their timeouts also exist, but the SDK ignores overrides unless it is running as a local test.

### Concurrency

By default a worker handles one job at a time. For I/O-bound handlers that wastes the GPU:

```python
def concurrency_modifier(current: int) -> int:
    return 4

runpod.serverless.start({"handler": handler, "concurrency_modifier": concurrency_modifier})
```

The function is called by the scaler, so concurrency can react to load or memory rather than being fixed.

### Progress updates

```python
from runpod.serverless.modules.rp_progress import progress_update

def handler(job):
    progress_update(job, "loading model")
    ...
```

Callers see it in `/status`. It runs on a background thread, so it does not block the handler.

### Input validation

The SDK ships a schema validator, which saves hand-writing the same checks:

```python
from runpod.serverless.utils.rp_validator import validate

SCHEMA = {
    "name": {"type": str, "required": False, "default": "World"},
    "count": {"type": int, "required": True, "constraints": lambda c: 1 <= c <= 10},
}

def handler(job):
    v = validate(job["input"], SCHEMA)
    if "errors" in v:
        return {"error": v["errors"]}
    job_input = v["validated_input"]
```

It checks types, applies defaults, enforces `constraints` lambdas, and rejects unexpected keys.

### Other utilities

| Import | Purpose |
|---|---|
| `runpod.serverless.utils.download_files_from_urls` | Fetch caller-supplied URLs to local files |
| `runpod.serverless.utils.upload_file_to_bucket` | Push large results to S3 and return a URL |
| `runpod.serverless.register_fitness_check` | Startup checks; a failure exits the worker so the orchestrator restarts it |

> **Return bodies over 20 MB** trigger an SDK tip recommending S3 upload instead. It is a log line, not an enforced limit, but treat it as one.

### Local test flags

| Flag | Effect |
|---|---|
| *(none)* | Runs `test_input.json` once, then exits |
| `--rp_serve_api` | Serves a local API on `http://localhost:8000` matching the real endpoint's shape |
| `--rp_api_port` / `--rp_api_host` | Change where it binds |
| `--rp_api_concurrency` | Uvicorn workers |
| `--rp_log_level` | `ERROR`, `WARN`, `INFO`, `DEBUG` |
| `--rp_debugger` | Attach the SDK debugger |

---

## 한국어

### 이 절반에 무엇이 있는가

| 영역 | 모듈 | 대략 |
|---|---|---|
| Handler 계약 | `rp_job`, `worker`, `serverless/__init__` | 580줄 |
| 기동 시 fitness check | `rp_fitness`, `rp_gpu_fitness`, `rp_system_fitness` | 1,125줄 |
| Handler 유틸리티 | `rp_validator`, `rp_download`, `rp_upload`, `rp_model_cache`, `rp_progress` | 740줄 |
| 내부 동작 | `rp_scale`, `worker_state`, `rp_ping`, `rp_http` | 800줄 |
| 로컬 개발 | `rp_fastapi`, `rp_debugger`, `rp_local` | 700줄 |

### 기동 시 fitness check

핸들러가 호출되기 전에, 워커는 자기가 배치된 머신을 검증합니다. 검사가 실패하면 프로세스가 `os._exit(1)` 로 종료되고, 오케스트레이터는 그 작업을 다른 워커에 배치합니다. 불량 하드웨어 위에서 천천히 실패하게 두지 않는 것입니다.

워커 절반에서 가장 큰 부분(약 1,125줄)이며, 요청하지 않아도 실행됩니다.

**자동으로 실행되는 검사**

| 검사 | 조건 |
|---|---|
| 메모리 가용량 | 항상 |
| 디스크 여유 공간 | 항상 |
| 네트워크 연결 | 항상 |
| CUDA 버전 | GPU 가 감지될 때만 |
| CUDA 디바이스 초기화 | GPU 가 감지될 때만 |
| GPU 연산 벤치마크 | GPU 가 감지될 때만 |
| 번들 테스트 바이너리를 통한 GPU 헬스 | GPU 가 감지될 때만 |

**조정 방법**

모든 임계값이 환경변수라서, 코드가 아니라 엔드포인트에서 설정합니다.

| 변수 | 기본값 |
|---|---|
| `RUNPOD_MIN_MEMORY_GB` | `4.0` |
| `RUNPOD_MIN_DISK_PERCENT` | `10.0` |
| `RUNPOD_MIN_CUDA_VERSION` | `11.8` |
| `RUNPOD_NETWORK_CHECK_TIMEOUT` | `5` |
| `RUNPOD_GPU_BENCHMARK_TIMEOUT` | `2` |
| `RUNPOD_GPU_TEST_TIMEOUT` | `30` |
| `RUNPOD_SKIP_GPU_CHECK` | 미설정 — `true` 면 GPU 검사 비활성화 |
| `RUNPOD_SKIP_AUTO_SYSTEM_CHECKS` | 미설정 — `true` 면 시스템 검사 비활성화 |

**직접 추가하기**

```python
@runpod.serverless.register_fitness_check
def check_weights_present():
    if not os.path.exists("/runpod-volume/model.safetensors"):
        raise RuntimeError("model weights missing")
```

비동기 함수도 됩니다. 데코레이터가 `inspect.iscoroutinefunction()` 으로 판별합니다. 실패시키려면 예외를 던지고, 정상 반환하면 통과입니다.

> **실패는 예외가 아니라 `os._exit(1)` 입니다.** `finally` 블록도, 정리 핸들러도 실행되지 않습니다. 의도된 동작입니다. 서비스할 수 없는 워커는 남아서 작업을 받는 대신 즉시 사라져야 하니까요.

> 이것이 "핸들러에서 작업이 실패하는 것" 과 "망가진 워커로 아예 라우팅되지 않는 것" 의 차이입니다. 핸들러가 존재를 전제하는 것이 있다면 검사를 하나 추가할 가치가 있습니다.

### Handler 유틸리티

워커마다 같은 코드를 반복해서 쓰지 않게 해주는 작은 도구들입니다.

| import | 용도 |
|---|---|
| `rp_validator.validate(input, schema)` | 타입, 기본값, `constraints` 람다, 예상치 못한 키 거부 |
| `utils.download_files_from_urls(job_id, urls)` | 호출자가 준 URL 을 로컬 파일로 |
| `utils.upload_file_to_bucket(name, path)` | S3 호환 스토리지에 파일을 올리고 URL 을 받음 |
| `utils.upload_in_memory_object(name, bytes)` | 디스크를 거치지 않고 동일 작업 |
| `rp_progress.progress_update(job, msg)` | `/status` 로 호출자에게 노출. 별도 스레드에서 실행 |
| `rp_cuda` | torch 를 import 하지 않고 `torch.cuda` 형태의 정보를 조금 |

업로드는 자격 증명을 환경변수에서 읽으므로, 같은 핸들러가 어떤 S3 호환 버킷에서도 동작합니다.

```
BUCKET_ENDPOINT_URL
BUCKET_ACCESS_KEY_ID
BUCKET_SECRET_ACCESS_KEY
```

> **20MB 반환 제한에 대한 답이 이것입니다.** 큰 결과물을 반환하는 대신 업로드하고 URL 을 돌려주세요. 버킷 변수가 없으면 SDK 가 로컬 저장으로 폴백하는데, 개발에는 편하지만 프로덕션에서는 조용히 무용지물이 됩니다. 설정 여부를 확인하세요.

### 알아둘 내부 동작

직접 호출하지는 않지만, 로그와 과금에서 보이는 것들을 설명해 줍니다.

| 모듈 | 하는 일 |
|---|---|
| `rp_ping` | Runpod 으로 보내는 하트비트. 진행 중인 작업 정보를 함께 실어 보냄. 콘솔이 워커 생존을 아는 경로 |
| `worker_state` | 진행 중인 작업 추적과 `RUNPOD_*` 환경변수 읽기. 실습이 `worker_id` 로 반환하는 `RUNPOD_POD_ID` 의 출처 |
| `rp_scale` | 작업 가져오기 루프와, `concurrency_modifier` 가 조정하는 동시성 |
| `rp_http` | 워커가 Runpod 으로 되돌아가는 자체 HTTP 경로. 클라이언트 SDK 와 별개이며, 에이전트를 감지하는 User-Agent 를 **싣지 않음** |

### 로컬 개발

| 도구 | 실행 방법 |
|---|---|
| `rp_local` | 기본값. `test_input.json` 을 읽어 작업 1건 실행 후 종료 |
| `rp_fastapi` | `--rp_serve_api`. 실제 엔드포인트 형태를 그대로 흉내 내는 uvicorn 서버, `/docs` 제공 |
| `rp_debugger` | `--rp_debugger`. SDK 타이밍 디버거 연결 |

### Handler 계약

```python
import runpod

def handler(job):
    return {"result": job["input"]["x"] * 2}

runpod.serverless.start({"handler": handler})
```

`start()` 는 핸들러가 아니라 **설정 딕셔너리**를 받습니다. 필수 키는 `handler` 하나이고 나머지는 아래에 정리했습니다.

`start()` 는 **반환하지 않습니다.** 프로세스를 넘겨받아 Runpod 작업 큐를 폴링하며 작업마다 핸들러를 호출합니다. 이 줄 아래 코드는 실행되지 않습니다.

### 핸들러가 받는 것

최소한 `id` 와 `input` 을 가진 딕셔너리입니다. `job["input"]` 은 호출자가 `"input"` 아래에 보낸 JSON 객체 그대로입니다.

```python
{"id": "abc-123", "input": {"name": "Runpod"}}
```

### 핸들러가 반환하는 것 — 알아둬야 할 부분

SDK 는 반환값을 검사해서 **딕셔너리의 특정 키 두 개를 데이터가 아니라 제어 신호로 취급합니다.** 각 경우를 직접 실행해 확인했습니다.

| 반환값 | SDK 가 만드는 결과 | 효과 |
|---|---|---|
| `{"ok": True}` | `{"output": {"ok": True}}` | 정상 성공 |
| `{"ok": False, "error": "bad input"}` | `{"output": {"ok": False}, "error": "bad input"}` | **작업이 실패로 표시됨** |
| `{"ok": True, "refresh_worker": True}` | `{"output": {"ok": True}, "stopPod": True}` | 성공 후 워커 재활용 |
| `{}` | `{}` | `output` 키가 통째로 사라짐 |
| `"just a string"` | `{"output": "just a string"}` | 딕셔너리가 아니면 감싸짐 |

<br>

> **`error` 는 일반 필드가 아닙니다.** 반환 딕셔너리 어디에든 `error` 키가 있으면 작업이 실패합니다.
>
> ```
> DEBUG | run_job return: {'output': {'ok': False}, 'error': 'bad input'}
> ERROR | Job local_test failed with error: bad input
> ```
>
> 진짜 실패에는 보통 이게 원하는 동작입니다. 다만 `error` 를 평범한 출력 필드로 쓸 수 없다는 뜻이기도 합니다. `{"error": None}` 은 제거되고, `{"error": "경고 문구"}` 는 성공했어야 할 작업을 실패시킵니다. 다른 이름을 쓰세요.

> **`refresh_worker` 는 작업 후 워커를 재활용합니다.** GPU 메모리 누수나 라이브러리가 엉킨 상태처럼 프로세스가 망가졌을 때 유용합니다. 대신 비쌉니다. 다음 요청이 콜드 스타트를 온전히 부담합니다.

### 예외를 던지면

SDK 가 잡습니다. 워커는 살아남고 작업만 실패하며, JSON 덩어리가 반환됩니다.

```json
{"error_type": "<class 'ValueError'>",
 "error_message": "boom",
 "error_traceback": "Traceback (most recent call last): ...",
 "hostname": "...", "worker_id": "...", "runpod_version": "1.11.0"}
```

> **전체 트레이스백이 호출자에게 전달됩니다.** 절대 경로와 소스 코드 라인까지 포함해서요. 실습에서는 괜찮지만 외부에 노출되는 서비스라면 생각해볼 부분입니다. 예상 가능한 실패는 잡아서 통제된 `error` 문자열로 반환하세요.

### 제너레이터로 스트리밍

`return` 대신 `yield` 하면 각 조각이 개별 `{"output": ...}` 으로 전송됩니다. 동기·비동기 제너레이터 모두 동작합니다.

```python
def handler(job):
    for token in generate():
        yield {"token": token}

runpod.serverless.start({"handler": handler, "return_aggregate_stream": True})
```

`return_aggregate_stream: True` 를 주면 모아진 출력을 `/stream` 뿐 아니라 `/runsync` 와 `/status` 에서도 받을 수 있습니다.

> **로컬 테스트로는 검증되지 않습니다.** `test_input.json` 으로 실행하면 비스트리밍 경로를 타서 제너레이터 객체가 소비되지 않은 채 반환됩니다.
> ```
> DEBUG | run_job return: {'output': <generator object gen at 0x...>}
> ```
> 제너레이터는 실제 엔드포인트나 `--rp_serve_api` 로 테스트하세요.

### `start()` 가 받는 설정 키

| 키 | 용도 |
|---|---|
| `handler` | 필수. 동기 / 비동기 / 제너레이터 / 비동기 제너레이터 모두 가능 |
| `return_aggregate_stream` | 제너레이터 출력을 모아 `/runsync` 와 `/status` 에서 반환 |
| `concurrency_modifier` | `fn(current: int) -> int`. 워커 하나가 여러 작업을 동시에 처리 |
| `rp_args` | CLI 플래그로 채워짐. 직접 설정할 일은 거의 없음 |

`jobs_fetcher`, `jobs_handler`, `stop_signals_fetcher` 와 각 타임아웃도 존재하지만, 로컬 테스트로 실행 중이 아니면 SDK 가 덮어쓰기를 무시합니다.

### 동시성

기본적으로 워커는 한 번에 작업 하나를 처리합니다. I/O 바운드 핸들러에서는 GPU 가 놀게 됩니다.

```python
def concurrency_modifier(current: int) -> int:
    return 4

runpod.serverless.start({"handler": handler, "concurrency_modifier": concurrency_modifier})
```

스케일러가 이 함수를 호출하므로, 고정값 대신 부하나 메모리에 반응하도록 만들 수 있습니다.

### 진행 상황 보고

```python
from runpod.serverless.modules.rp_progress import progress_update

def handler(job):
    progress_update(job, "loading model")
    ...
```

호출자는 `/status` 에서 확인합니다. 백그라운드 스레드에서 실행되므로 핸들러를 막지 않습니다.

### 입력 검증

SDK 에 스키마 검증기가 들어 있어 같은 검사를 손으로 쓰지 않아도 됩니다.

```python
from runpod.serverless.utils.rp_validator import validate

SCHEMA = {
    "name": {"type": str, "required": False, "default": "World"},
    "count": {"type": int, "required": True, "constraints": lambda c: 1 <= c <= 10},
}

def handler(job):
    v = validate(job["input"], SCHEMA)
    if "errors" in v:
        return {"error": v["errors"]}
    job_input = v["validated_input"]
```

타입 확인, 기본값 적용, `constraints` 람다 검사, 예상치 못한 키 거부를 함께 수행합니다.

### 그 외 유틸리티

| import | 용도 |
|---|---|
| `runpod.serverless.utils.download_files_from_urls` | 호출자가 준 URL 을 로컬 파일로 내려받기 |
| `runpod.serverless.utils.upload_file_to_bucket` | 큰 결과물을 S3 에 올리고 URL 반환 |
| `runpod.serverless.register_fitness_check` | 기동 시 점검. 실패하면 워커가 종료되어 오케스트레이터가 재시작 |

> **반환 본문이 20MB 를 넘으면** SDK 가 S3 업로드를 권하는 팁을 남깁니다. 강제되는 제한이 아니라 로그 한 줄이지만, 제한으로 취급하는 편이 좋습니다.

### 로컬 테스트 플래그

| 플래그 | 효과 |
|---|---|
| *(없음)* | `test_input.json` 을 1회 실행하고 종료 |
| `--rp_serve_api` | `http://localhost:8000` 에 실제 엔드포인트와 같은 형태의 로컬 API 제공 |
| `--rp_api_port` / `--rp_api_host` | 바인딩 위치 변경 |
| `--rp_api_concurrency` | uvicorn 워커 수 |
| `--rp_log_level` | `ERROR`, `WARN`, `INFO`, `DEBUG` |
| `--rp_debugger` | SDK 디버거 연결 |
