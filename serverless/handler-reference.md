# Handler Reference

[English](#english) | [한국어](#한국어)

> Everything here was read out of the installed SDK source (`runpod` 1.11.0) and confirmed by running it locally. Where behaviour is surprising, the observed output is included.
>
> 이 문서의 내용은 설치된 SDK 소스(`runpod` 1.11.0)를 직접 읽고 로컬에서 실행해 확인한 것입니다. 동작이 직관과 다른 부분은 실제 출력을 함께 실었습니다.

---

## English

### The contract

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

### 계약

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
