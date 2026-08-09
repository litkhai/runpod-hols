---
layout: default
title: Handler
permalink: /handler/
---

# Handler Reference

<div class="lang" data-lang="en" markdown="1">

## English

Read out of the installed SDK source (`runpod` 1.11.0) and confirmed by running each case. Where the behaviour is surprising, the observed output is shown.

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

### Worth knowing

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

[Full reference in the repo →](https://github.com/litkhai/runpod-hols/blob/main/serverless/handler-reference.md)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

설치된 SDK 소스(`runpod` 1.11.0)를 직접 읽고 각 경우를 실행해 확인한 내용입니다. 동작이 직관과 다른 부분은 실제 출력을 함께 실었습니다.

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

### 알아두면 좋은 것

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

[저장소에서 전체 레퍼런스 보기 →](https://github.com/litkhai/runpod-hols/blob/main/serverless/handler-reference.md)

</div>
