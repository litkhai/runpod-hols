# Python SDK Reference — Driving Runpod from Code

[English](#english) | [한국어](#한국어)

> Read out of the installed SDK source (`runpod` 1.11.0) and exercised against a live endpoint. Outputs shown are real.
>
> 설치된 SDK 소스(`runpod` 1.11.0)를 읽고 실제 엔드포인트에 실행해 확인했습니다. 아래 출력은 실제 결과입니다.

---

## English

### The SDK is two halves

| Half | You use it | Covered in |
|---|---|---|
| **Worker runtime** | Inside the container, to *be* an endpoint | [handler-reference.md](../serverless/handler-reference.md) |
| **Client API** | Outside, to *call and manage* Runpod | This document |

They share a package but never meet: `runpod.serverless.start()` runs in the worker, everything below runs on your machine.

### Authentication

```python
import runpod
runpod.api_key = os.environ["RUNPOD_API_KEY"]
```

Everything else fails without it. The error is explicit about the fix:

```
Expected `run_pod.api_key` to be initialized. …
An API key can be generated at https://console.runpod.io/user/settings
```

### Calling an endpoint

```python
ep = runpod.Endpoint("ku3jultxavac2v")
```

**`run_sync(input, timeout=86400)`** — blocks and hands back the output:

```python
ep.run_sync({"name": "SDK"}, timeout=180)
# {'greeting': 'Hello, SDK!', 'worker_id': 'rrlm8trcnfn5of'}
```

Two conveniences are easy to miss:

- **It wraps your input.** `{"name": "SDK"}` becomes `{"input": {"name": "SDK"}}`. Pass `{"input": {...}}` yourself and it is left alone, so both forms work.
- **It falls back to polling.** `/runsync` does not always return a finished job — it can hand back `IN_PROGRESS`. `run_sync` notices the non-final status and polls until the job settles. Doing this over raw HTTP means writing that loop yourself.

> **The default timeout is 86,400 seconds — a full day.** A wedged job will block your script until tomorrow. Pass something realistic.

**`run(input)`** — returns immediately with a `Job`:

```python
job = ep.run({"name": "async"})
job.job_id          # '6778d623-0e9c-4214-a4c3-a18926d8d21c-e1'
job.status()        # 'IN_QUEUE'
job.output(timeout=180)
# {'greeting': 'Hello, async!', 'worker_id': 'rrlm8trcnfn5of'}
job.status()        # 'COMPLETED'
```

| Method | Behaviour |
|---|---|
| `job.status()` | Current state, cached once final |
| `job.output(timeout=0)` | `0` returns whatever is there now; above `0` polls once a second and raises `TimeoutError` |
| `job.stream()` | Generator yielding partials from a generator handler; polls once a second |
| `job.cancel()` | Cancels the job |

**`health()`** — what the endpoint is actually doing:

```python
ep.health()
{'jobs': {'completed': 7, 'failed': 5, 'inProgress': 0, 'inQueue': 0, 'retried': 5},
 'workers': {'idle': 2, 'initializing': 0, 'ready': 2, 'running': 0,
             'throttled': 0, 'unhealthy': 0}}
```

Worth checking when something looks wrong. The `failed: 5, retried: 5` above is a real record of the `{"input": {}}` requests that hung during these labs — the platform retried and failed them, which the HTTP call never told us.

**`purge_queue()`** — drops queued jobs. Useful after firing a bad batch.

### Job states

```python
FINAL_STATES = ["COMPLETED", "FAILED", "TIMED_OUT"]
is_completed(s) -> s in ["COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED"]
```

> **These two disagree**: `CANCELLED` is final for `is_completed()` but not for `FINAL_STATES`. `run_sync` checks the list without it, while `job.output()` polls on the function that has it. If you cancel a job you are waiting on, prefer `output()`.

### Async

`AsyncioEndpoint` and `AsyncioJob` mirror the above for `asyncio`, taking an `aiohttp` session. Use them when firing many requests at once; the sync client blocks per call.

### Managing infrastructure

The same functions the console calls:

| Area | Functions |
|---|---|
| Pods | `create_pod`, `get_pods`, `get_pod`, `stop_pod`, `resume_pod`, `terminate_pod` |
| Endpoints | `create_endpoint`, `get_endpoints`, `update_endpoint_template` |
| Templates | `create_template` |
| Hardware | `get_gpus`, `get_gpu` |
| Account | `get_user`, `update_user_settings` |
| Registries | `create_container_registry_auth`, `update_…`, `delete_…` |

```python
runpod.get_gpus()          # 48 entries at time of writing
runpod.get_pods()          # everything currently costing you money
runpod.terminate_pod(pod_id)
```

`get_pods()` is the cheapest habit worth having — [`verify-auth.py`](./verify-auth.py) calls it precisely to surface Pods you forgot to stop.

These wrap Runpod's GraphQL API, so responses come back shaped by GraphQL rather than by REST.

### The bundled `runpod` CLI

Installing the SDK also installs a `runpod` command. **This is not `runpodctl`** — that is a separate Go binary from a Homebrew tap. Both exist, and they are not the same tool.

```
runpod config    # store your API key
runpod pod       # create / list / connect / sync
runpod exec      # run commands on a pod
runpod ssh       # manage SSH keys
runpod project   # new / start / deploy
```

`runpod project` is the most interesting and the least advertised: `new` scaffolds a worker (there are `default` and `llama2` starter templates), `start` brings up a development Pod described by a `runpod.toml`, and `deploy` ships it. It is a hot-reload loop against real GPU hardware, which is a different workflow from the image-build cycle these labs use.

### Gotchas worth remembering

| Thing | Why it matters |
|---|---|
| `run_sync` default timeout is 24h | A hung job blocks your script all day |
| `run_sync` auto-wraps input | Both `{"x": 1}` and `{"input": {"x": 1}}` work; helpful, but obscures the wire format |
| `/runsync` may return `IN_PROGRESS` | The SDK polls for you; raw HTTP callers must handle it |
| `CANCELLED` is inconsistent between the two state checks | Prefer `job.output()` when cancellation is possible |
| `job.output()` and `stream()` poll every second | Fine for labs; a tight loop for latency-sensitive work |
| The `runpod` CLI ≠ `runpodctl` | Different tools, overlapping names |

---

## 한국어

### SDK 는 두 부분입니다

| 구분 | 사용하는 위치 | 문서 |
|---|---|---|
| **워커 런타임** | 컨테이너 안에서, 엔드포인트가 *되기* 위해 | [handler-reference.md](../serverless/handler-reference.md) |
| **클라이언트 API** | 바깥에서, Runpod 을 *호출하고 관리*하기 위해 | 이 문서 |

같은 패키지에 있지만 서로 만나지 않습니다. `runpod.serverless.start()` 는 워커에서 돌고, 아래 내용은 내 컴퓨터에서 돕니다.

### 인증

```python
import runpod
runpod.api_key = os.environ["RUNPOD_API_KEY"]
```

이게 없으면 나머지가 전부 실패합니다. 오류 메시지가 해결 방법까지 알려줍니다.

```
Expected `run_pod.api_key` to be initialized. …
An API key can be generated at https://console.runpod.io/user/settings
```

### 엔드포인트 호출

```python
ep = runpod.Endpoint("ku3jultxavac2v")
```

**`run_sync(input, timeout=86400)`** — 완료까지 대기하고 출력을 돌려줍니다.

```python
ep.run_sync({"name": "SDK"}, timeout=180)
# {'greeting': 'Hello, SDK!', 'worker_id': 'rrlm8trcnfn5of'}
```

놓치기 쉬운 편의 기능이 두 가지 있습니다.

- **입력을 자동으로 감쌉니다.** `{"name": "SDK"}` 가 `{"input": {"name": "SDK"}}` 로 바뀝니다. 직접 `{"input": {...}}` 를 넘기면 그대로 두므로 두 형태 모두 동작합니다.
- **폴링으로 자동 전환합니다.** `/runsync` 가 항상 완료된 작업을 돌려주지는 않습니다. `IN_PROGRESS` 가 올 수 있는데, `run_sync` 는 이를 알아채고 작업이 끝날 때까지 폴링합니다. 순수 HTTP 로 호출하면 이 루프를 직접 작성해야 합니다.

> **기본 타임아웃이 86,400초, 즉 하루입니다.** 멈춘 작업 하나가 스크립트를 내일까지 붙잡습니다. 현실적인 값을 넘기세요.

**`run(input)`** — 즉시 `Job` 을 반환합니다.

```python
job = ep.run({"name": "async"})
job.job_id          # '6778d623-0e9c-4214-a4c3-a18926d8d21c-e1'
job.status()        # 'IN_QUEUE'
job.output(timeout=180)
# {'greeting': 'Hello, async!', 'worker_id': 'rrlm8trcnfn5of'}
job.status()        # 'COMPLETED'
```

| 메서드 | 동작 |
|---|---|
| `job.status()` | 현재 상태. 최종 상태가 되면 캐시됨 |
| `job.output(timeout=0)` | `0` 이면 현재 값을 즉시 반환, `0` 초과면 1초 간격 폴링 후 `TimeoutError` |
| `job.stream()` | 제너레이터 핸들러의 조각을 순차 반환. 1초 간격 폴링 |
| `job.cancel()` | 작업 취소 |

**`health()`** — 엔드포인트가 실제로 무엇을 하고 있는지 보여줍니다.

```python
ep.health()
{'jobs': {'completed': 7, 'failed': 5, 'inProgress': 0, 'inQueue': 0, 'retried': 5},
 'workers': {'idle': 2, 'initializing': 0, 'ready': 2, 'running': 0,
             'throttled': 0, 'unhealthy': 0}}
```

뭔가 이상할 때 확인할 가치가 있습니다. 위의 `failed: 5, retried: 5` 는 이 실습 중 멈췄던 `{"input": {}}` 요청들의 실제 기록입니다. 플랫폼이 재시도하고 실패시켰는데, HTTP 호출만으로는 알 수 없던 사실입니다.

**`purge_queue()`** — 대기 중인 작업을 비웁니다. 잘못된 배치를 던진 뒤에 유용합니다.

### 작업 상태

```python
FINAL_STATES = ["COMPLETED", "FAILED", "TIMED_OUT"]
is_completed(s) -> s in ["COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED"]
```

> **이 둘이 서로 다릅니다.** `CANCELLED` 는 `is_completed()` 에서는 최종 상태지만 `FINAL_STATES` 에는 없습니다. `run_sync` 는 `CANCELLED` 가 빠진 목록을 확인하고, `job.output()` 은 포함된 함수로 폴링합니다. 대기 중인 작업을 취소할 가능성이 있다면 `output()` 쪽이 안전합니다.

### 비동기

`AsyncioEndpoint` 와 `AsyncioJob` 이 위 내용을 `asyncio` 용으로 제공하며 `aiohttp` 세션을 받습니다. 요청을 많이 동시에 던질 때 사용하세요. 동기 클라이언트는 호출마다 블로킹합니다.

### 인프라 관리

콘솔이 호출하는 것과 같은 함수들입니다.

| 영역 | 함수 |
|---|---|
| Pod | `create_pod`, `get_pods`, `get_pod`, `stop_pod`, `resume_pod`, `terminate_pod` |
| 엔드포인트 | `create_endpoint`, `get_endpoints`, `update_endpoint_template` |
| 템플릿 | `create_template` |
| 하드웨어 | `get_gpus`, `get_gpu` |
| 계정 | `get_user`, `update_user_settings` |
| 레지스트리 | `create_container_registry_auth`, `update_…`, `delete_…` |

```python
runpod.get_gpus()          # 작성 시점 기준 48개
runpod.get_pods()          # 지금 비용이 나가고 있는 모든 것
runpod.terminate_pod(pod_id)
```

`get_pods()` 는 습관으로 삼을 만합니다. [`verify-auth.py`](./verify-auth.py) 가 이 함수를 호출하는 이유도 끄는 것을 잊은 Pod 를 드러내기 위해서입니다.

이들은 Runpod 의 GraphQL API 를 감싼 것이라, 응답이 REST 가 아니라 GraphQL 형태로 돌아옵니다.

### 함께 설치되는 `runpod` CLI

SDK 를 설치하면 `runpod` 명령도 함께 설치됩니다. **`runpodctl` 과 다릅니다.** 그쪽은 Homebrew tap 으로 설치하는 별도의 Go 바이너리입니다. 둘 다 존재하고, 같은 도구가 아닙니다.

```
runpod config    # API 키 저장
runpod pod       # 생성 / 목록 / 접속 / 동기화
runpod exec      # Pod 에서 명령 실행
runpod ssh       # SSH 키 관리
runpod project   # new / start / deploy
```

`runpod project` 가 가장 흥미로우면서 가장 덜 알려져 있습니다. `new` 는 워커를 스캐폴딩하고(`default`, `llama2` 스타터 템플릿 제공), `start` 는 `runpod.toml` 에 기술된 개발용 Pod 를 띄우고, `deploy` 는 배포합니다. 실제 GPU 하드웨어를 상대로 하는 핫 리로드 루프이며, 이 실습들이 사용하는 이미지 빌드 주기와는 다른 워크플로입니다.

### 기억해둘 함정

| 항목 | 이유 |
|---|---|
| `run_sync` 기본 타임아웃 24시간 | 멈춘 작업이 스크립트를 하루 종일 붙잡음 |
| `run_sync` 가 입력을 자동으로 감쌈 | `{"x": 1}` 과 `{"input": {"x": 1}}` 모두 동작. 편하지만 실제 전송 형식이 가려짐 |
| `/runsync` 가 `IN_PROGRESS` 를 반환할 수 있음 | SDK 는 대신 폴링해주지만, 순수 HTTP 호출자는 직접 처리해야 함 |
| 두 상태 검사에서 `CANCELLED` 취급이 다름 | 취소 가능성이 있으면 `job.output()` 사용 |
| `job.output()` 과 `stream()` 은 1초 간격 폴링 | 실습에는 충분하지만 지연에 민감한 작업에는 촘촘한 루프 |
| `runpod` CLI ≠ `runpodctl` | 이름이 겹치는 서로 다른 도구 |
