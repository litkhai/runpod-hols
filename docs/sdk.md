---
layout: default
title: SDK
permalink: /sdk/
---

# Python SDK

<div class="lang" data-lang="en" markdown="1">

## English

Read out of the installed SDK source (`runpod` 1.11.0) and exercised against a live endpoint. Outputs shown are real.

### Two halves that never meet

| Half | Runs | Documented in |
|---|---|---|
| **Worker runtime** | Inside the container, to *be* an endpoint | [Handler]({{ '/handler/' | relative_url }}) |
| **Client API** | On your machine, to *call and manage* Runpod | This page |

### Authentication

```python
import runpod
runpod.api_key = os.environ["RUNPOD_API_KEY"]
```

### Calling an endpoint

```python
ep = runpod.Endpoint("ku3jultxavac2v")

ep.run_sync({"name": "SDK"}, timeout=180)
# {'greeting': 'Hello, SDK!', 'worker_id': 'rrlm8trcnfn5of'}
```

Two conveniences worth knowing about:

- **Input is auto-wrapped.** `{"name": "SDK"}` becomes `{"input": {"name": "SDK"}}`. Passing `{"input": {...}}` yourself also works.
- **`run_sync` falls back to polling.** `/runsync` can return `IN_PROGRESS` rather than a finished job; the SDK notices and waits. Over raw HTTP you write that loop yourself.

<div class="warn" markdown="1">
**`run_sync`'s default timeout is 86,400 seconds — a full day.** A wedged job blocks your script until tomorrow. Pass a realistic value.
</div>

Async form returns a `Job`:

```python
job = ep.run({"name": "async"})
job.status()               # 'IN_QUEUE'
job.output(timeout=180)    # {'greeting': 'Hello, async!', ...}
job.status()               # 'COMPLETED'
```

| Method | Behaviour |
|---|---|
| `job.status()` | Current state, cached once final |
| `job.output(timeout=0)` | `0` returns what exists now; above `0` polls every second, raises `TimeoutError` |
| `job.stream()` | Yields partials from a generator handler |
| `job.cancel()` | Cancels the job |

### Seeing what the endpoint is doing

```python
ep.health()
{'jobs': {'completed': 7, 'failed': 5, 'inProgress': 0, 'inQueue': 0, 'retried': 5},
 'workers': {'idle': 2, 'initializing': 0, 'ready': 2, 'running': 0,
             'throttled': 0, 'unhealthy': 0}}
```

That `failed: 5, retried: 5` is a real record of the `{"input": {}}` requests that hung during these labs — the platform retried and failed them, which the HTTP call itself never reported. `purge_queue()` drops anything still queued.

### Job states

```python
FINAL_STATES = ["COMPLETED", "FAILED", "TIMED_OUT"]
is_completed(s) -> s in ["COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED"]
```

<div class="warn" markdown="1">
**The two disagree on `CANCELLED`.** `run_sync` checks the list without it; `job.output()` polls on the function that has it. If cancellation is possible, prefer `output()`.
</div>

### Managing infrastructure

| Area | Functions |
|---|---|
| Pods | `create_pod`, `get_pods`, `get_pod`, `stop_pod`, `resume_pod`, `terminate_pod` |
| Endpoints | `create_endpoint`, `get_endpoints`, `update_endpoint_template` |
| Templates | `create_template` |
| Hardware | `get_gpus`, `get_gpu` |
| Account | `get_user`, `update_user_settings` |
| Registries | `create_container_registry_auth`, `update_…`, `delete_…` |

`get_pods()` is the habit worth keeping — it lists everything currently costing money.

### The bundled `runpod` CLI

Installing the SDK also installs a `runpod` command. **This is not `runpodctl`**, which is a separate Go binary from a Homebrew tap.

```
runpod config    runpod pod    runpod exec    runpod ssh    runpod project
```

`runpod project` is the least advertised and most interesting: `new` scaffolds a worker (`default` and `llama2` templates), `start` brings up a dev Pod from `runpod.toml`, `deploy` ships it. A hot-reload loop against real GPUs — a different workflow from the image-build cycle these labs use.

[Full reference in the repo →](https://github.com/litkhai/runpod-hols/blob/main/setup/sdk-reference.md)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

설치된 SDK 소스(`runpod` 1.11.0)를 읽고 실제 엔드포인트에 실행해 확인했습니다. 아래 출력은 실제 결과입니다.

### 서로 만나지 않는 두 부분

| 구분 | 실행 위치 | 문서 |
|---|---|---|
| **워커 런타임** | 컨테이너 안. 엔드포인트가 *되기* 위해 | [Handler]({{ '/handler/' | relative_url }}) |
| **클라이언트 API** | 내 컴퓨터. Runpod 을 *호출하고 관리*하기 위해 | 이 페이지 |

### 인증

```python
import runpod
runpod.api_key = os.environ["RUNPOD_API_KEY"]
```

### 엔드포인트 호출

```python
ep = runpod.Endpoint("ku3jultxavac2v")

ep.run_sync({"name": "SDK"}, timeout=180)
# {'greeting': 'Hello, SDK!', 'worker_id': 'rrlm8trcnfn5of'}
```

알아둘 편의 기능 두 가지입니다.

- **입력이 자동으로 감싸집니다.** `{"name": "SDK"}` 가 `{"input": {"name": "SDK"}}` 로 바뀝니다. 직접 `{"input": {...}}` 를 넘겨도 동작합니다.
- **`run_sync` 가 폴링으로 전환합니다.** `/runsync` 는 완료된 작업 대신 `IN_PROGRESS` 를 반환할 수 있는데, SDK 가 이를 감지해 기다립니다. 순수 HTTP 로는 이 루프를 직접 짜야 합니다.

<div class="warn" markdown="1">
**`run_sync` 의 기본 타임아웃은 86,400초, 하루입니다.** 멈춘 작업 하나가 스크립트를 내일까지 붙잡습니다. 현실적인 값을 넘기세요.
</div>

비동기 형태는 `Job` 을 반환합니다.

```python
job = ep.run({"name": "async"})
job.status()               # 'IN_QUEUE'
job.output(timeout=180)    # {'greeting': 'Hello, async!', ...}
job.status()               # 'COMPLETED'
```

| 메서드 | 동작 |
|---|---|
| `job.status()` | 현재 상태. 최종 상태가 되면 캐시 |
| `job.output(timeout=0)` | `0` 이면 현재 값 즉시 반환, 초과면 1초 간격 폴링 후 `TimeoutError` |
| `job.stream()` | 제너레이터 핸들러의 조각을 순차 반환 |
| `job.cancel()` | 작업 취소 |

### 엔드포인트 상태 확인

```python
ep.health()
{'jobs': {'completed': 7, 'failed': 5, 'inProgress': 0, 'inQueue': 0, 'retried': 5},
 'workers': {'idle': 2, 'initializing': 0, 'ready': 2, 'running': 0,
             'throttled': 0, 'unhealthy': 0}}
```

여기 `failed: 5, retried: 5` 는 이 실습 중 멈췄던 `{"input": {}}` 요청들의 실제 기록입니다. 플랫폼이 재시도하고 실패시켰지만 HTTP 호출 자체로는 알 수 없던 사실입니다. `purge_queue()` 는 대기 중인 작업을 비웁니다.

### 작업 상태

```python
FINAL_STATES = ["COMPLETED", "FAILED", "TIMED_OUT"]
is_completed(s) -> s in ["COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED"]
```

<div class="warn" markdown="1">
**둘이 `CANCELLED` 취급을 다르게 합니다.** `run_sync` 는 `CANCELLED` 가 빠진 목록을 확인하고, `job.output()` 은 포함된 함수로 폴링합니다. 취소 가능성이 있으면 `output()` 을 쓰세요.
</div>

### 인프라 관리

| 영역 | 함수 |
|---|---|
| Pod | `create_pod`, `get_pods`, `get_pod`, `stop_pod`, `resume_pod`, `terminate_pod` |
| 엔드포인트 | `create_endpoint`, `get_endpoints`, `update_endpoint_template` |
| 템플릿 | `create_template` |
| 하드웨어 | `get_gpus`, `get_gpu` |
| 계정 | `get_user`, `update_user_settings` |
| 레지스트리 | `create_container_registry_auth`, `update_…`, `delete_…` |

`get_pods()` 는 습관으로 삼을 만합니다. 지금 비용이 나가고 있는 모든 것을 나열해 줍니다.

### 함께 설치되는 `runpod` CLI

SDK 를 설치하면 `runpod` 명령도 함께 설치됩니다. **`runpodctl` 과 다릅니다** — 그쪽은 Homebrew tap 으로 설치하는 별도의 Go 바이너리입니다.

```
runpod config    runpod pod    runpod exec    runpod ssh    runpod project
```

`runpod project` 가 가장 덜 알려져 있으면서 흥미롭습니다. `new` 는 워커를 스캐폴딩하고(`default`, `llama2` 템플릿), `start` 는 `runpod.toml` 기반 개발용 Pod 를 띄우고, `deploy` 는 배포합니다. 실제 GPU 를 상대로 하는 핫 리로드 루프이며, 이 실습들의 이미지 빌드 주기와는 다른 워크플로입니다.

[저장소에서 전체 레퍼런스 보기 →](https://github.com/litkhai/runpod-hols/blob/main/setup/sdk-reference.md)

</div>
