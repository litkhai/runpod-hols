---
layout: default
title: Client SDK
permalink: /sdk/client/
---

# Client SDK

<div class="lang" data-lang="en" markdown="1">

## English

The half of the SDK that runs **on your own machine**. The other half is [Worker SDK]({{ '/sdk/worker/' | relative_url }}).

Read out of the installed source at 1.11.0 and 1.12.0, and exercised against a live endpoint. Outputs shown are real. What 2.1.0 changes is in its own section, read from source.

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

- **Input is auto-wrapped.** `{"name": "SDK"}` becomes `{"input": {"name": "SDK"}}`. Passing `{"input": {...}}` yourself also works.
- **`run_sync` falls back to polling.** `/runsync` can return `IN_PROGRESS` rather than a finished job; the SDK notices and waits. Over raw HTTP you write that loop yourself.

<div class="warn" markdown="1">
**`run_sync`'s default timeout is 86,400 seconds — a full day.** A wedged job blocks your script until tomorrow. Pass a realistic value.
</div>

`AsyncioEndpoint` / `AsyncioJob` cover the same ground for `asyncio`, but are not a drop-in swap: there is no `run_sync`, and `output(timeout=0)` raises `TimeoutError` instead of returning what exists — `asyncio.wait_for(coro, 0)` times out even on a coroutine that returns immediately. Always pass a timeout.

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

<figure class="shot"><a href="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}"><img src="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}" alt="Workers tab of 01-hello-world: two idle cpu5g-2-8 workers in EUR-IS-1" loading="lazy" width="1400" height="998"></a><figcaption>The console view behind <code>health()</code>'s <code>workers</code>: two idle workers, cpu5g-2-8 in EUR-IS-1, both on the latest release. The tab hides idle workers by default ("2 workers hidden by filters"); clear the filter to see them.</figcaption></figure>

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

### What changed in 2.x

`runpod` 2.0.0 reached PyPI on 2026-10-30 and 2.1.0 on 2026-11-03. Read from the installed 2.1.0 source on 2026-11-05 and compared with 1.12.0; `get_gpus`, `get_gpu`, `get_endpoints` and `get_pods` were called read-only against a real account. Nothing was created with 2.x.

| | 1.12.0 | 2.1.0 |
|---|---|---|
| `Endpoint`, `Job`, `AsyncioEndpoint` | | Unchanged — the `runpod/endpoint/` package is identical |
| Pod, template, endpoint and GPU calls | GraphQL | REST on `https://api.runpod.io/v2` — `/v2/pods`, `/v2/templates`, `/v2/serverless`, `/v2/catalog/gpus`. `get_user` and `update_container_registry_auth` stay on GraphQL |
| A `get_gpus()` item | `id`, `displayName`, `memoryInGb` | `id`, `name`, `memory`, `price`, `maxCount`, `pool`, … |
| A `get_endpoints()` item | GraphQL fields | `gpu.pools`, `workers.min` / `max` / `idleTimeout`, `flashboot` as `"OFF"` or `"FLASHBOOT"`, `requestUrls` |
| A Pod | `desiredStatus`, `imageName`, `costPerHr`, `uptimeSeconds`, `runtime.ports[].publicPort` | `status`, `image`, `cost`, `runtime.uptime`, `runtime.ports[].public` — from the 2.1.0 CLI's own code; no Pod existed to fetch |
| `create_pod` for a CPU Pod | Sent as given | Needs `instance_id` as `<flavor>-<vCPU>-<memory>`; rejects `volume_mount_path` without a network volume, `support_public_ip`, `country_code`, `min_download` and `min_upload` before sending anything |
| `create_endpoint` | `gpu_ids` passed through to GraphQL | `-<type>` entries in `gpu_ids` become `gpu.excludedTypes` |
| The `runpod` command | The click CLI below | A new CLI, `rp`, with `runpod` as an alias: `catalog`, `endpoint`, `flash`, `pod`, `volume`, `secret`, `registry`, `logs`, `ssh`, `login`, `update`. `runpod project` and `runpod exec` are gone |
| User-Agent | `RunPod-Python-SDK/1.12.0 …` | Same format with `2.1.0`; agent detection unchanged |

<div class="warn" markdown="1">
**Code written for 1.x can fail silently on 2.x.** A Pod no longer has `desiredStatus`, so a filter such as `p.get("desiredStatus") == "RUNNING"` returns nothing — and a guard built on it stops guarding. The Pod lab is pinned to `runpod~=1.12.0` for that reason.
</div>

The base REST path is not the published OpenAPI spec's `https://rest.runpod.io/v1`. Both hosts answer; the SDK uses the `/v2` paths on `api.runpod.io`.

The upstream `CHANGELOG.md` labels the 2.0.0 notes as a second `2.1.0` section dated 2026-10-28. The GitHub release `v2.0.0` carries those notes under `2.0.0`, and PyPI and the tags agree on 2.0.0 for 2026-10-30.

### Pointing the SDK somewhere else

| Variable | Default | Used by |
|---|---|---|
| `RUNPOD_ENDPOINT_BASE_URL` | `https://api.runpod.ai/v2` | `Endpoint` / `Job` |
| `RUNPOD_API_BASE_URL` | `https://api.runpod.io` | GraphQL control plane |

`RUNPOD_UA_INTEGRATION` appends `Integration/<value>` to the User-Agent.

### The SDK reports which AI agent is driving it

Every client call carries a User-Agent, and the SDK inspects the environment to see whether a coding agent is at the keyboard. Run from this repository, under Claude Code:

```python
>>> from runpod import agent, user_agent
>>> agent.detect()
'claude-code'
>>> user_agent.USER_AGENT
'RunPod-Python-SDK/1.12.0 (Darwin 25.6.0; arm64) Language/Python 3.11.14 (via claude-code)'
```

`CLAUDECODE=1` was the trigger. The registry covers 21 harnesses — Claude Code, Codex, Cursor, Gemini CLI, Copilot, Cline, Zed, Replit and others — and mirrors [Hugging Face's public agent-harnesses list](https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/src/agent-harnesses.ts) so identifiers match across tools. Any tool can self-identify with `AI_AGENT`; the value is sanitised and capped at 64 characters so it cannot forge a header. A bare `AGENT` is deliberately ignored — too common in CI to mean anything.

<div class="note" markdown="1">
**Client-side only.** The worker's own HTTP path does not use it, so traffic from inside a running worker is untagged. It is the calls from your machine that get attributed.
</div>

### The bundled `runpod` CLI

Installing the SDK also installs a `runpod` command. **This is not `runpodctl`**, which is a separate Go binary from a Homebrew tap.

```
runpod config    runpod pod    runpod exec    runpod ssh    runpod project
```

`runpod project` is the least advertised and most interesting: `new` scaffolds a worker (`default` and `llama2` templates), `start` brings up a dev Pod from `runpod.toml`, `deploy` ships it. A hot-reload loop against real GPUs — a different workflow from the image-build cycle these labs use.

In 2.x the `runpod` command is the new `rp` CLI instead — see the table above.

[Full reference in the repo →](https://github.com/litkhai/runpod-hols/blob/main/sdk/client.md)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

SDK 중 **내 컴퓨터에서 도는** 절반입니다. 나머지 절반은 [Worker SDK]({{ '/sdk/worker/' | relative_url }}) 에 있습니다.

1.11.0 과 1.12.0 의 설치된 소스를 읽고 실제 엔드포인트에 실행해 확인했습니다. 아래 출력은 실제 결과입니다. 2.1.0 에서 바뀐 것은 소스를 읽어 별도 섹션에 정리했습니다.

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

- **입력이 자동으로 감싸집니다.** `{"name": "SDK"}` 가 `{"input": {"name": "SDK"}}` 로 바뀝니다. 직접 `{"input": {...}}` 를 넘겨도 동작합니다.
- **`run_sync` 가 폴링으로 전환합니다.** `/runsync` 는 완료된 작업 대신 `IN_PROGRESS` 를 반환할 수 있는데, SDK 가 이를 감지해 기다립니다. 순수 HTTP 로는 이 루프를 직접 짜야 합니다.

<div class="warn" markdown="1">
**`run_sync` 의 기본 타임아웃은 86,400초, 하루입니다.** 멈춘 작업 하나가 스크립트를 내일까지 붙잡습니다. 현실적인 값을 넘기세요.
</div>

`AsyncioEndpoint` / `AsyncioJob` 이 같은 영역을 `asyncio` 용으로 제공하지만 그대로 바꿔 끼울 수는 없습니다. `run_sync` 가 없고, `output(timeout=0)` 은 현재 값을 반환하는 대신 `TimeoutError` 를 냅니다 — `asyncio.wait_for(coro, 0)` 은 즉시 반환하는 코루틴에도 타임아웃을 냅니다. 타임아웃을 반드시 넘기세요.

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

<figure class="shot"><a href="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}"><img src="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}" alt="01-hello-world 의 Workers 탭: EUR-IS-1 의 유휴 cpu5g-2-8 워커 두 개" loading="lazy" width="1400" height="998"></a><figcaption><code>health()</code> 의 <code>workers</code> 에 해당하는 콘솔 화면: 유휴 워커 두 개, EUR-IS-1 의 cpu5g-2-8, 둘 다 최신 릴리스. 이 탭은 기본으로 유휴 워커를 숨긴다 ("2 workers hidden by filters"). 필터를 지워야 보인다.</figcaption></figure>

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

### 2.x 에서 바뀐 것

`runpod` 2.0.0 은 2026-10-30, 2.1.0 은 2026-11-03 에 PyPI 에 올라왔습니다. 2026-11-05 에 설치된 2.1.0 소스를 읽고 1.12.0 과 비교했으며, `get_gpus`, `get_gpu`, `get_endpoints`, `get_pods` 는 실제 계정에 읽기 전용으로 호출했습니다. 2.x 로 생성한 것은 없습니다.

| | 1.12.0 | 2.1.0 |
|---|---|---|
| `Endpoint`, `Job`, `AsyncioEndpoint` | | 그대로 — `runpod/endpoint/` 패키지가 동일 |
| Pod, 템플릿, 엔드포인트, GPU 호출 | GraphQL | `https://api.runpod.io/v2` 의 REST — `/v2/pods`, `/v2/templates`, `/v2/serverless`, `/v2/catalog/gpus`. `get_user` 와 `update_container_registry_auth` 는 GraphQL 그대로 |
| `get_gpus()` 항목 | `id`, `displayName`, `memoryInGb` | `id`, `name`, `memory`, `price`, `maxCount`, `pool`, … |
| `get_endpoints()` 항목 | GraphQL 필드 | `gpu.pools`, `workers.min` / `max` / `idleTimeout`, `"OFF"` 또는 `"FLASHBOOT"` 인 `flashboot`, `requestUrls` |
| Pod | `desiredStatus`, `imageName`, `costPerHr`, `uptimeSeconds`, `runtime.ports[].publicPort` | `status`, `image`, `cost`, `runtime.uptime`, `runtime.ports[].public` — 2.1.0 CLI 자체 코드 기준. 조회할 Pod 이 없었음 |
| CPU Pod 의 `create_pod` | 주어진 대로 전송 | `<flavor>-<vCPU>-<메모리>` 형식의 `instance_id` 필수. 네트워크 볼륨 없는 `volume_mount_path`, `support_public_ip`, `country_code`, `min_download`, `min_upload` 는 전송 전에 거부 |
| `create_endpoint` | `gpu_ids` 를 GraphQL 에 그대로 전달 | `gpu_ids` 의 `-<type>` 항목이 `gpu.excludedTypes` 가 됨 |
| `runpod` 명령 | 아래의 click CLI | 새 CLI `rp`, `runpod` 은 별칭: `catalog`, `endpoint`, `flash`, `pod`, `volume`, `secret`, `registry`, `logs`, `ssh`, `login`, `update`. `runpod project` 와 `runpod exec` 는 사라짐 |
| User-Agent | `RunPod-Python-SDK/1.12.0 …` | 같은 형식에 `2.1.0`. 에이전트 감지는 그대로 |

<div class="warn" markdown="1">
**1.x 용 코드가 2.x 에서 조용히 틀릴 수 있습니다.** Pod 에 더는 `desiredStatus` 가 없으므로 `p.get("desiredStatus") == "RUNNING"` 같은 필터는 아무것도 돌려주지 않고, 그 위에 세운 안전장치는 작동을 멈춥니다. 그래서 Pod 실습은 `runpod~=1.12.0` 으로 고정합니다.
</div>

REST 기본 경로는 발행된 OpenAPI 스펙의 `https://rest.runpod.io/v1` 가 아닙니다. 두 호스트 모두 응답하며, SDK 는 `api.runpod.io` 의 `/v2` 경로를 씁니다.

상류 `CHANGELOG.md` 는 2.0.0 의 노트를 2026-10-28 날짜의 두 번째 `2.1.0` 섹션으로 표기합니다. GitHub 릴리스 `v2.0.0` 에는 같은 노트가 `2.0.0` 으로 올라 있고, PyPI 와 태그도 2026-10-30 의 2.0.0 으로 일치합니다.

### SDK 를 다른 곳으로 향하게 하기

| 변수 | 기본값 | 사용처 |
|---|---|---|
| `RUNPOD_ENDPOINT_BASE_URL` | `https://api.runpod.ai/v2` | `Endpoint` / `Job` |
| `RUNPOD_API_BASE_URL` | `https://api.runpod.io` | GraphQL 컨트롤 플레인 |

`RUNPOD_UA_INTEGRATION` 은 User-Agent 에 `Integration/<값>` 을 덧붙입니다.

### SDK 는 자기를 구동하는 AI 에이전트를 보고합니다

모든 클라이언트 호출에는 User-Agent 가 실리고, SDK 가 환경을 검사해 코딩 에이전트가 키보드를 잡고 있는지 확인합니다. 이 저장소에서 Claude Code 로 실행한 결과입니다.

```python
>>> from runpod import agent, user_agent
>>> agent.detect()
'claude-code'
>>> user_agent.USER_AGENT
'RunPod-Python-SDK/1.12.0 (Darwin 25.6.0; arm64) Language/Python 3.11.14 (via claude-code)'
```

트리거는 `CLAUDECODE=1` 이었습니다. 레지스트리는 21개 하니스를 다루며 — Claude Code, Codex, Cursor, Gemini CLI, Copilot, Cline, Zed, Replit 등 — 도구 간 식별자를 맞추기 위해 [Hugging Face 의 공개 agent-harnesses 목록](https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/src/agent-harnesses.ts)을 따릅니다. 어떤 도구든 `AI_AGENT` 로 스스로를 식별할 수 있고, 값은 정제 후 64자로 잘려 헤더를 위조할 수 없습니다. 밋밋한 `AGENT` 는 일부러 무시합니다. CI 에서 너무 흔해 의미가 없기 때문입니다.

<div class="note" markdown="1">
**클라이언트 쪽에만 적용됩니다.** 워커 자체의 HTTP 경로는 이를 쓰지 않으므로 실행 중인 워커 내부 트래픽에는 태그가 붙지 않습니다. 집계되는 것은 내 컴퓨터에서 하는 호출입니다.
</div>

### 함께 설치되는 `runpod` CLI

SDK 를 설치하면 `runpod` 명령도 함께 설치됩니다. **`runpodctl` 과 다릅니다** — 그쪽은 Homebrew tap 으로 설치하는 별도의 Go 바이너리입니다.

```
runpod config    runpod pod    runpod exec    runpod ssh    runpod project
```

`runpod project` 가 가장 덜 알려져 있으면서 흥미롭습니다. `new` 는 워커를 스캐폴딩하고(`default`, `llama2` 템플릿), `start` 는 `runpod.toml` 기반 개발용 Pod 를 띄우고, `deploy` 는 배포합니다. 실제 GPU 를 상대로 하는 핫 리로드 루프이며, 이 실습들의 이미지 빌드 주기와는 다른 워크플로입니다.

2.x 에서는 `runpod` 명령이 새 `rp` CLI 로 바뀝니다. 위의 표를 보세요.

[저장소에서 전체 레퍼런스 보기 →](https://github.com/litkhai/runpod-hols/blob/main/sdk/client.md)

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

SDK 中**在你自己的机器上**运行的那一半。另一半是 [Worker SDK]({{ '/sdk/worker/' | relative_url }})。

内容读自 1.11.0 和 1.12.0 已安装的源码，并在真实的 endpoint 上实际调用过。展示的输出都是真实的。2.1.0 的变化单独成节，同样读自源码。

### 认证

```python
import runpod
runpod.api_key = os.environ["RUNPOD_API_KEY"]
```

### 调用 endpoint

```python
ep = runpod.Endpoint("ku3jultxavac2v")

ep.run_sync({"name": "SDK"}, timeout=180)
# {'greeting': 'Hello, SDK!', 'worker_id': 'rrlm8trcnfn5of'}
```

- **输入会被自动包装。** `{"name": "SDK"}` 会变成 `{"input": {"name": "SDK"}}`。自己传入 `{"input": {...}}` 也可以。
- **`run_sync` 会退回到轮询。** `/runsync` 可能返回 `IN_PROGRESS` 而不是已完成的 job；SDK 会察觉并等待。如果直接用 HTTP，这个循环需要你自己写。

<div class="warn" markdown="1">
**`run_sync` 的默认超时是 86,400 秒——整整一天。** 一个卡住的 job 会把你的脚本阻塞到明天。请传入一个现实的值。
</div>

`AsyncioEndpoint` / `AsyncioJob` 为 `asyncio` 提供同样的功能，但不能直接替换：没有 `run_sync`，而且 `output(timeout=0)` 会抛出 `TimeoutError`，而不是返回已有的结果——`asyncio.wait_for(coro, 0)` 即使对立即返回的协程也会超时。请始终传入 timeout。

异步形式返回一个 `Job`：

```python
job = ep.run({"name": "async"})
job.status()               # 'IN_QUEUE'
job.output(timeout=180)    # {'greeting': 'Hello, async!', ...}
job.status()               # 'COMPLETED'
```

| 方法 | 行为 |
|---|---|
| `job.status()` | 当前状态，到达最终状态后会被缓存 |
| `job.output(timeout=0)` | `0` 返回当前已有的结果；大于 `0` 时每秒轮询一次，超时抛出 `TimeoutError` |
| `job.stream()` | 从 generator handler 逐个产出部分结果 |
| `job.cancel()` | 取消 job |

### 查看 endpoint 在做什么

```python
ep.health()
{'jobs': {'completed': 7, 'failed': 5, 'inProgress': 0, 'inQueue': 0, 'retried': 5},
 'workers': {'idle': 2, 'initializing': 0, 'ready': 2, 'running': 0,
             'throttled': 0, 'unhealthy': 0}}
```

其中的 `failed: 5, retried: 5` 真实记录了这些实验期间卡住的 `{"input": {}}` 请求——平台对它们进行了重试并判定失败，而 HTTP 调用本身从未报告这一点。`purge_queue()` 会丢弃仍在队列中的所有内容。

<figure class="shot"><a href="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}"><img src="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}" alt="01-hello-world 的 Workers 标签页：EUR-IS-1 中两个空闲的 cpu5g-2-8 worker" loading="lazy" width="1400" height="998"></a><figcaption>对应 <code>health()</code> 中 <code>workers</code> 的控制台视图：两个空闲 worker，EUR-IS-1 的 cpu5g-2-8，都在最新 release 上。该标签页默认隐藏空闲 worker（"2 workers hidden by filters"），清除筛选后才能看到。</figcaption></figure>

### Job 状态

```python
FINAL_STATES = ["COMPLETED", "FAILED", "TIMED_OUT"]
is_completed(s) -> s in ["COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED"]
```

<div class="warn" markdown="1">
**两者对 `CANCELLED` 的看法不一致。** `run_sync` 检查的是不含它的列表；`job.output()` 轮询时用的是包含它的函数。如果可能发生取消，优先使用 `output()`。
</div>

### 管理基础设施

| 领域 | 函数 |
|---|---|
| Pod | `create_pod`、`get_pods`、`get_pod`、`stop_pod`、`resume_pod`、`terminate_pod` |
| Endpoint | `create_endpoint`、`get_endpoints`、`update_endpoint_template` |
| Template | `create_template` |
| 硬件 | `get_gpus`、`get_gpu` |
| 账号 | `get_user`、`update_user_settings` |
| Registry | `create_container_registry_auth`、`update_…`、`delete_…` |

`get_pods()` 是值得养成的习惯——它会列出当前所有正在花钱的东西。

### 2.x 中的变化

`runpod` 2.0.0 于 2026-10-30 发布到 PyPI，2.1.0 于 2026-11-03 发布。2026-11-05 读取了已安装的 2.1.0 源码并与 1.12.0 对比；`get_gpus`、`get_gpu`、`get_endpoints` 和 `get_pods` 在真实账号上以只读方式调用过。没有用 2.x 创建任何资源。

| | 1.12.0 | 2.1.0 |
|---|---|---|
| `Endpoint`、`Job`、`AsyncioEndpoint` | | 未变——`runpod/endpoint/` 包完全相同 |
| Pod、template、endpoint 和 GPU 调用 | GraphQL | `https://api.runpod.io/v2` 上的 REST——`/v2/pods`、`/v2/templates`、`/v2/serverless`、`/v2/catalog/gpus`。`get_user` 和 `update_container_registry_auth` 仍使用 GraphQL |
| `get_gpus()` 的一个条目 | `id`、`displayName`、`memoryInGb` | `id`、`name`、`memory`、`price`、`maxCount`、`pool`、… |
| `get_endpoints()` 的一个条目 | GraphQL 字段 | `gpu.pools`、`workers.min` / `max` / `idleTimeout`、取值为 `"OFF"` 或 `"FLASHBOOT"` 的 `flashboot`、`requestUrls` |
| 一个 Pod | `desiredStatus`、`imageName`、`costPerHr`、`uptimeSeconds`、`runtime.ports[].publicPort` | `status`、`image`、`cost`、`runtime.uptime`、`runtime.ports[].public`——取自 2.1.0 CLI 自身的代码；当时没有可获取的 Pod |
| 为 CPU Pod 调用 `create_pod` | 按原样发送 | 需要 `<flavor>-<vCPU>-<memory>` 形式的 `instance_id`；在发送任何内容之前就拒绝没有 network volume 的 `volume_mount_path`、`support_public_ip`、`country_code`、`min_download` 和 `min_upload` |
| `create_endpoint` | `gpu_ids` 原样传给 GraphQL | `gpu_ids` 中的 `-<type>` 条目变为 `gpu.excludedTypes` |
| `runpod` 命令 | 下文的 click CLI | 新的 CLI `rp`，`runpod` 作为别名：`catalog`、`endpoint`、`flash`、`pod`、`volume`、`secret`、`registry`、`logs`、`ssh`、`login`、`update`。`runpod project` 和 `runpod exec` 已移除 |
| User-Agent | `RunPod-Python-SDK/1.12.0 …` | 格式相同，版本为 `2.1.0`；agent 检测未变 |

<div class="warn" markdown="1">
**为 1.x 编写的代码在 2.x 上可能静默失败。** Pod 不再有 `desiredStatus`，所以像 `p.get("desiredStatus") == "RUNNING"` 这样的过滤条件什么也不返回——基于它构建的防护也就不再起作用。正因如此，Pod 实验固定使用 `runpod~=1.12.0`。
</div>

基础 REST 路径并不是已发布的 OpenAPI 规范中的 `https://rest.runpod.io/v1`。两个主机都会响应；SDK 使用的是 `api.runpod.io` 上的 `/v2` 路径。

上游的 `CHANGELOG.md` 把 2.0.0 的说明标成了第二个 `2.1.0` 小节，日期为 2026-10-28。GitHub release `v2.0.0` 在 `2.0.0` 下记载了这些说明，PyPI 和 tag 也一致表明 2.0.0 发布于 2026-10-30。

### 让 SDK 指向其他地址

| 变量 | 默认值 | 使用者 |
|---|---|---|
| `RUNPOD_ENDPOINT_BASE_URL` | `https://api.runpod.ai/v2` | `Endpoint` / `Job` |
| `RUNPOD_API_BASE_URL` | `https://api.runpod.io` | GraphQL 控制平面 |

`RUNPOD_UA_INTEGRATION` 会在 User-Agent 后追加 `Integration/<value>`。

### SDK 会报告是哪个 AI agent 在驱动它

每次客户端调用都带有 User-Agent，SDK 会检查环境，判断是否有 coding agent 在操作。在本仓库中、于 Claude Code 下运行：

```python
>>> from runpod import agent, user_agent
>>> agent.detect()
'claude-code'
>>> user_agent.USER_AGENT
'RunPod-Python-SDK/1.12.0 (Darwin 25.6.0; arm64) Language/Python 3.11.14 (via claude-code)'
```

触发条件是 `CLAUDECODE=1`。注册表涵盖 21 种 harness——Claude Code、Codex、Cursor、Gemini CLI、Copilot、Cline、Zed、Replit 等——并与 [Hugging Face's public agent-harnesses list](https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/src/agent-harnesses.ts) 保持一致，使各工具之间的标识符相同。任何工具都可以通过 `AI_AGENT` 自报身份；该值会被清洗并限制在 64 个字符以内，因此无法伪造 header。单独的 `AGENT` 被刻意忽略——它在 CI 中太常见，没有意义。

<div class="note" markdown="1">
**仅限客户端。** worker 自身的 HTTP 路径不使用它，因此来自运行中 worker 内部的流量不会被打标记。被归因的是从你的机器发出的调用。
</div>

### 附带的 `runpod` CLI

安装 SDK 时也会安装一个 `runpod` 命令。**它不是 `runpodctl`**，后者是来自 Homebrew tap 的独立 Go 二进制程序。

```
runpod config    runpod pod    runpod exec    runpod ssh    runpod project
```

`runpod project` 宣传最少，却最有意思：`new` 搭建一个 worker 脚手架（`default` 和 `llama2` 模板），`start` 依据 `runpod.toml` 启动一个开发用 Pod，`deploy` 将其发布。这是一个针对真实 GPU 的热重载循环——与这些实验所用的镜像构建循环是不同的工作流。

在 2.x 中，`runpod` 命令改为新的 `rp` CLI——见上表。

[仓库中的完整参考 →](https://github.com/litkhai/runpod-hols/blob/main/sdk/client.md)

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

SDK のうち**自分のマシンで**動く側の半分です。もう半分は [Worker SDK]({{ '/sdk/worker/' | relative_url }}) です。

1.11.0 と 1.12.0 のインストール済みソースから読み取り、実際の endpoint に対して動かしました。示している出力は本物です。2.1.0 での変更は、ソースから読み取って別のセクションにまとめています。

### 認証

```python
import runpod
runpod.api_key = os.environ["RUNPOD_API_KEY"]
```

### endpoint の呼び出し

```python
ep = runpod.Endpoint("ku3jultxavac2v")

ep.run_sync({"name": "SDK"}, timeout=180)
# {'greeting': 'Hello, SDK!', 'worker_id': 'rrlm8trcnfn5of'}
```

- **入力は自動でラップされます**：`{"name": "SDK"}` は `{"input": {"name": "SDK"}}` になります。自分で `{"input": {...}}` を渡しても動きます。
- **`run_sync` はポーリングにフォールバックします**：`/runsync` は完了した job ではなく `IN_PROGRESS` を返すことがあり、SDK はそれに気づいて待ちます。生の HTTP ではこのループを自分で書くことになります。

<div class="warn" markdown="1">
**`run_sync` のデフォルトのタイムアウトは 86,400 秒、つまり丸 1 日です。** 固まった job があるとスクリプトは明日までブロックされます。現実的な値を渡してください。
</div>

`AsyncioEndpoint` / `AsyncioJob` は `asyncio` 向けに同じ機能を提供しますが、そのまま置き換えられるわけではありません。`run_sync` はなく、`output(timeout=0)` は既にある結果を返すのではなく `TimeoutError` を送出します。`asyncio.wait_for(coro, 0)` は即座に返るコルーチンでもタイムアウトするためです。タイムアウトは必ず渡してください。

非同期形式は `Job` を返します。

```python
job = ep.run({"name": "async"})
job.status()               # 'IN_QUEUE'
job.output(timeout=180)    # {'greeting': 'Hello, async!', ...}
job.status()               # 'COMPLETED'
```

| メソッド | 動作 |
|---|---|
| `job.status()` | 現在の状態。最終状態になるとキャッシュされる |
| `job.output(timeout=0)` | `0` なら今ある結果を返す。`0` より大きければ毎秒ポーリングし、`TimeoutError` を送出 |
| `job.stream()` | generator handler からの部分結果を順に返す |
| `job.cancel()` | job をキャンセル |

### endpoint が何をしているかを見る

```python
ep.health()
{'jobs': {'completed': 7, 'failed': 5, 'inProgress': 0, 'inQueue': 0, 'retried': 5},
 'workers': {'idle': 2, 'initializing': 0, 'ready': 2, 'running': 0,
             'throttled': 0, 'unhealthy': 0}}
```

この `failed: 5, retried: 5` は、これらのラボの途中で固まった `{"input": {}}` リクエストの実際の記録です。プラットフォームはそれらをリトライして失敗としましたが、HTTP 呼び出し自体はそれを一切報告しませんでした。`purge_queue()` はキューに残っているものをすべて破棄します。

<figure class="shot"><a href="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}"><img src="{{ '/assets/img/sdk-client/workers-tab.webp' | relative_url }}" alt="01-hello-world の Workers タブ：EUR-IS-1 のアイドルな cpu5g-2-8 ワーカー 2 つ" loading="lazy" width="1400" height="998"></a><figcaption><code>health()</code> の <code>workers</code> に当たるコンソール画面：アイドルなワーカー 2 つ、EUR-IS-1 の cpu5g-2-8、どちらも最新リリース。このタブは既定でアイドルなワーカーを隠します（"2 workers hidden by filters"）。フィルターを外すと見えます。</figcaption></figure>

### Job の状態

```python
FINAL_STATES = ["COMPLETED", "FAILED", "TIMED_OUT"]
is_completed(s) -> s in ["COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED"]
```

<div class="warn" markdown="1">
**この 2 つは `CANCELLED` の扱いが食い違っています。** `run_sync` はそれを含まないリストを確認し、`job.output()` はそれを含む関数でポーリングします。キャンセルがありうるなら `output()` を使ってください。
</div>

### インフラの管理

| 分野 | 関数 |
|---|---|
| Pod | `create_pod`、`get_pods`、`get_pod`、`stop_pod`、`resume_pod`、`terminate_pod` |
| Endpoint | `create_endpoint`、`get_endpoints`、`update_endpoint_template` |
| Template | `create_template` |
| ハードウェア | `get_gpus`、`get_gpu` |
| アカウント | `get_user`、`update_user_settings` |
| Registry | `create_container_registry_auth`、`update_…`、`delete_…` |

`get_pods()` は身につけておく価値のある習慣です。今お金がかかっているものをすべて一覧できます。

### 2.x で変わったこと

`runpod` 2.0.0 は 2026-10-30 に、2.1.0 は 2026-11-03 に PyPI に公開されました。2026-11-05 にインストール済みの 2.1.0 のソースを読んで 1.12.0 と比較し、`get_gpus`、`get_gpu`、`get_endpoints`、`get_pods` を実際のアカウントに対して読み取り専用で呼び出しました。2.x では何も作成していません。

| | 1.12.0 | 2.1.0 |
|---|---|---|
| `Endpoint`、`Job`、`AsyncioEndpoint` | | 変更なし。`runpod/endpoint/` パッケージは同一 |
| Pod、template、endpoint、GPU の呼び出し | GraphQL | `https://api.runpod.io/v2` 上の REST。`/v2/pods`、`/v2/templates`、`/v2/serverless`、`/v2/catalog/gpus`。`get_user` と `update_container_registry_auth` は GraphQL のまま |
| `get_gpus()` の 1 項目 | `id`、`displayName`、`memoryInGb` | `id`、`name`、`memory`、`price`、`maxCount`、`pool`、… |
| `get_endpoints()` の 1 項目 | GraphQL のフィールド | `gpu.pools`、`workers.min` / `max` / `idleTimeout`、`"OFF"` または `"FLASHBOOT"` を取る `flashboot`、`requestUrls` |
| Pod | `desiredStatus`、`imageName`、`costPerHr`、`uptimeSeconds`、`runtime.ports[].publicPort` | `status`、`image`、`cost`、`runtime.uptime`、`runtime.ports[].public`。2.1.0 の CLI 自身のコードから。取得できる Pod はなかった |
| CPU Pod の `create_pod` | 指定どおりに送信 | `<flavor>-<vCPU>-<memory>` 形式の `instance_id` が必要。network volume なしの `volume_mount_path`、`support_public_ip`、`country_code`、`min_download`、`min_upload` は何かを送信する前に拒否 |
| `create_endpoint` | `gpu_ids` をそのまま GraphQL に渡す | `gpu_ids` 内の `-<type>` の項目は `gpu.excludedTypes` になる |
| `runpod` コマンド | 後述の click CLI | 新しい CLI の `rp` で、`runpod` はエイリアス：`catalog`、`endpoint`、`flash`、`pod`、`volume`、`secret`、`registry`、`logs`、`ssh`、`login`、`update`。`runpod project` と `runpod exec` はなくなった |
| User-Agent | `RunPod-Python-SDK/1.12.0 …` | 同じ形式で `2.1.0`。agent の検出は変更なし |

<div class="warn" markdown="1">
**1.x 向けに書いたコードは 2.x で黙って失敗することがあります。** Pod にはもう `desiredStatus` がないため、`p.get("desiredStatus") == "RUNNING"` のようなフィルタは何も返さず、それに基づくガードは機能しなくなります。Pod のラボが `runpod~=1.12.0` に固定されているのはこのためです。
</div>

ベースの REST パスは、公開されている OpenAPI 仕様の `https://rest.runpod.io/v1` ではありません。どちらのホストも応答しますが、SDK は `api.runpod.io` 上の `/v2` パスを使います。

上流の `CHANGELOG.md` は 2.0.0 のノートを、日付 2026-10-28 の 2 つ目の `2.1.0` セクションとしてラベル付けしています。GitHub リリースの `v2.0.0` はそのノートを `2.0.0` として載せており、PyPI とタグも 2.0.0 が 2026-10-30 であることで一致しています。

### SDK の向き先を変える

| 変数 | デフォルト | 使用箇所 |
|---|---|---|
| `RUNPOD_ENDPOINT_BASE_URL` | `https://api.runpod.ai/v2` | `Endpoint` / `Job` |
| `RUNPOD_API_BASE_URL` | `https://api.runpod.io` | GraphQL コントロールプレーン |

`RUNPOD_UA_INTEGRATION` は User-Agent に `Integration/<value>` を付け加えます。

### SDK はどの AI agent が操作しているかを報告する

クライアントの呼び出しにはすべて User-Agent が付き、SDK は環境を調べてコーディング agent がキーボードの前にいるかどうかを判定します。このリポジトリから Claude Code 上で実行した結果：

```python
>>> from runpod import agent, user_agent
>>> agent.detect()
'claude-code'
>>> user_agent.USER_AGENT
'RunPod-Python-SDK/1.12.0 (Darwin 25.6.0; arm64) Language/Python 3.11.14 (via claude-code)'
```

きっかけは `CLAUDECODE=1` でした。レジストリは 21 種類のハーネス（Claude Code、Codex、Cursor、Gemini CLI、Copilot、Cline、Zed、Replit など）をカバーしており、ツール間で識別子が一致するよう [Hugging Face's public agent-harnesses list](https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/src/agent-harnesses.ts) を反映しています。どのツールも `AI_AGENT` で自己申告できます。値はサニタイズされ 64 文字に制限されるため、ヘッダを偽造することはできません。単独の `AGENT` は意図的に無視されます。CI ではありふれすぎていて意味をなさないためです。

<div class="note" markdown="1">
**クライアント側のみです。** worker 自身の HTTP 経路はこれを使わないため、実行中の worker の中からのトラフィックにはタグが付きません。帰属が記録されるのは自分のマシンからの呼び出しです。
</div>

### 同梱の `runpod` CLI

SDK をインストールすると `runpod` コマンドもインストールされます。**これは `runpodctl` ではありません**。`runpodctl` は Homebrew tap から入る別の Go バイナリです。

```
runpod config    runpod pod    runpod exec    runpod ssh    runpod project
```

`runpod project` は最も宣伝されていませんが、最も興味深いものです。`new` で worker の雛形を作り（`default` と `llama2` のテンプレート）、`start` で `runpod.toml` から開発用の Pod を立ち上げ、`deploy` でデプロイします。実際の GPU に対するホットリロードのループで、これらのラボで使うイメージビルドのサイクルとは別のワークフローです。

2.x では `runpod` コマンドは新しい `rp` CLI に置き換わっています。上の表を参照してください。

[リポジトリのリファレンス全体 →](https://github.com/litkhai/runpod-hols/blob/main/sdk/client.md)

</div>
