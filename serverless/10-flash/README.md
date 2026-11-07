# Serverless Lab 10 — Runpod Flash

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** deploy a Python function to Serverless with **Flash** — no Dockerfile, no handler, no image registry — and compare the workflow, the cold start and what ends up in the account with the handler-and-image flow of [lab 01](../01-hello-worker).

**Time:** ~15 minutes · **Cost:** under one cent on a CPU endpoint (2026-11-07)

### What Flash is now

Flash began as a separate package, `runpod-flash`, with a `flash` CLI and an `@Endpoint` decorator. Its docs now say that package stopped receiving fixes on 2026-10-29 and that Flash is part of the main SDK: **`runpod` 2.x** ships an `rp` CLI and a `runpod.App` with decorators. This lab uses `runpod` **2.1.0** on Python 3.12 (Flash needs 3.10–3.14). The worker labs 01–08 still use the 1.12 serverless SDK; the two coexist because Flash builds its own workers.

### Files

| File | Role |
|---|---|
| `main.py` | One app, one CPU queue function (`cpu3c-2-4`, 0–2 workers, `numpy` as a dependency) and a local entrypoint that calls it three times |
| `results/dev1.log` | `rp flash dev main.py --once` output |
| `results/deploy1.log` | `rp flash deploy` output |
| `results/http_cold.jsonl` | Three plain-HTTP `/runsync` calls to the deployed endpoint, 90 s apart |

### Run

```bash
uv venv -p 3.12 && uv pip install runpod==2.1.0
export RUNPOD_API_KEY=...            # or: rp login
rp flash dev main.py --once          # temporary endpoint, runs main(), deletes it
rp flash deploy                      # persistent endpoint, prints its id
curl -X POST https://api.runpod.ai/v2/<id>/runsync -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H 'Content-Type: application/json' -d '{"input":{"n":300}}'
rp flash undeploy --app lab10-flash -y && rp flash app delete lab10-flash -y
```

The function's keyword arguments are the job's `input`. Imports go inside the function: code at the top of the file runs on your machine.

### What the runs showed (2026-11-07)

| Step | Flash | Lab 01 (handler + Dockerfile) |
|---|---|---|
| What you write | A decorated function | Handler, Dockerfile, requirements, image push or GitHub build |
| Build and deploy | Dependencies resolved locally (29 packages), a 27.9 MB artifact uploaded, endpoint live in **24 s** | Image build and push, or a GitHub build of several minutes |
| Worker image | Runpod's prebuilt `runpod/queue:py3.12-latest`; the artifact is extracted to `/app` at boot (1.1 s) | Your own image |
| First call, fresh dev endpoint | 74.5 s | — |
| First call, just-deployed endpoint | `delayTime` 7.9 s | — |
| After 90 s idle (idle timeout 5 s) | `delayTime` 1.4–1.7 s, same container | — |
| Warm calls through `.remote()` | 2.2–3.2 s round trip | — |

The deployed endpoint was an ordinary queue endpoint — `/run`, `/runsync`, `/status` work with plain JSON — with FlashBoot on (`flashBootType: FLASHBOOT`), queue-delay scaling, `workersStandby: 2`, and all CPU datacenters allowed.

> **Flash copies your account API key into every endpoint it creates.** The template env holds `RUNPOD_API_KEY` set to the exact key that ran `rp flash deploy` (also in dev sessions), so code on the worker — your function and every dependency — can act on the whole account. The SDK source says it is there so a worker can call other Flash functions. Use a key you can revoke, and check what stays behind: after `undeploy` and `app delete` the deploy template still existed with the key in it, "held by deleted endpoint … pending cleanup" for up to 90 minutes; this lab overwrote the key in its env right away. The dev session's template has no name and could not be found to check.

Two more things to know:

- **Execution timeout is off by default** (`executionTimeoutMs: 0`). A job sent with `"input": {}` was rejected by the worker ("Job has missing field(s): id or input") yet stayed `IN_PROGRESS` for over two minutes and was retried, until cancelled. Set `execution_timeout_ms` and never send an empty input.
- The dev session's progress lines showed up to five workers initializing for a function limited to two.

---

## 한국어

**목표:** **Flash** 로 Python 함수를 Serverless 에 배포하고 — Dockerfile, 핸들러, 이미지 레지스트리 없이 — 작업 흐름, 콜드 스타트, 계정에 남는 것을 [실습 01](../01-hello-worker) 의 핸들러·이미지 방식과 비교한다.

**시간:** 약 15분 · **비용:** CPU 엔드포인트에서 1센트 미만 (2026-11-07)

### 지금의 Flash

Flash 는 `flash` CLI 와 `@Endpoint` 데코레이터를 가진 별도 패키지 `runpod-flash` 로 시작했다. 지금 문서는 그 패키지가 2026-10-29 부터 수정을 받지 않으며 Flash 가 메인 SDK 에 들어갔다고 한다: **`runpod` 2.x** 에 `rp` CLI 와 데코레이터를 쓰는 `runpod.App` 이 있다. 이 실습은 Python 3.12 에서 `runpod` **2.1.0** 을 쓴다 (Flash 는 3.10–3.14 필요). 실습 01–08 의 워커는 여전히 1.12 serverless SDK 를 쓴다. Flash 는 자기 워커를 따로 만들기 때문에 둘이 함께 있어도 된다.

### 파일

| 파일 | 역할 |
|---|---|
| `main.py` | 앱 하나, CPU 큐 함수 하나 (`cpu3c-2-4`, 워커 0–2, 의존성 `numpy`), 그것을 세 번 부르는 로컬 진입점 |
| `results/dev1.log` | `rp flash dev main.py --once` 출력 |
| `results/deploy1.log` | `rp flash deploy` 출력 |
| `results/http_cold.jsonl` | 배포된 엔드포인트에 90초 간격으로 보낸 일반 HTTP `/runsync` 세 번 |

### 실행

```bash
uv venv -p 3.12 && uv pip install runpod==2.1.0
export RUNPOD_API_KEY=...            # 또는: rp login
rp flash dev main.py --once          # 임시 엔드포인트, main() 실행 후 삭제
rp flash deploy                      # 계속 남는 엔드포인트, id 출력
curl -X POST https://api.runpod.ai/v2/<id>/runsync -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H 'Content-Type: application/json' -d '{"input":{"n":300}}'
rp flash undeploy --app lab10-flash -y && rp flash app delete lab10-flash -y
```

함수의 키워드 인자가 작업의 `input` 이다. import 는 함수 안에 둔다 — 파일 맨 위의 코드는 내 컴퓨터에서 돈다.

### 실행 결과 (2026-11-07)

| 단계 | Flash | 실습 01 (핸들러 + Dockerfile) |
|---|---|---|
| 작성하는 것 | 데코레이터를 단 함수 | 핸들러, Dockerfile, requirements, 이미지 push 또는 GitHub 빌드 |
| 빌드와 배포 | 의존성을 로컬에서 풀고 (29개 패키지), 27.9 MB 아티팩트를 올려 **24초** 만에 엔드포인트 가동 | 이미지 빌드·push, 또는 몇 분 걸리는 GitHub 빌드 |
| 워커 이미지 | Runpod 의 기성 `runpod/queue:py3.12-latest`; 부팅 때 아티팩트를 `/app` 에 풂 (1.1초) | 내 이미지 |
| 첫 호출, 새 dev 엔드포인트 | 74.5초 | — |
| 첫 호출, 막 배포한 엔드포인트 | `delayTime` 7.9초 | — |
| 90초 유휴 뒤 (유휴 타임아웃 5초) | `delayTime` 1.4–1.7초, 같은 컨테이너 | — |
| `.remote()` 웜 호출 | 왕복 2.2–3.2초 | — |

배포된 엔드포인트는 평범한 큐 엔드포인트였다 — `/run`, `/runsync`, `/status` 가 일반 JSON 으로 동작 — FlashBoot 켬 (`flashBootType: FLASHBOOT`), queue delay 스케일링, `workersStandby: 2`, 모든 CPU 데이터센터 허용.

> **Flash 는 만드는 모든 엔드포인트에 계정 API 키를 복사한다.** 템플릿 env 에 `rp flash deploy` 를 실행한 바로 그 키가 `RUNPOD_API_KEY` 로 들어가므로 (dev 세션도 마찬가지), 워커에서 도는 코드 — 내 함수와 모든 의존성 — 가 계정 전체를 다룰 수 있다. SDK 소스는 워커가 다른 Flash 함수를 부르기 위해서라고 설명한다. 폐기할 수 있는 키를 쓰고, 남는 것을 확인하자: `undeploy` 와 `app delete` 뒤에도 배포 템플릿이 키를 담은 채 남아 최대 90분간 "held by deleted endpoint … pending cleanup" 상태였다. 이 실습은 곧바로 env 의 키를 덮어썼다. dev 세션의 템플릿은 이름이 없어 찾아 확인할 수 없었다.

알아 둘 것 두 가지:

- **실행 시간 제한이 기본으로 꺼져 있다** (`executionTimeoutMs: 0`). `"input": {}` 로 보낸 작업은 워커가 거부했는데도 ("Job has missing field(s): id or input") 2분 넘게 `IN_PROGRESS` 로 남았고 재시도됐다 — 취소할 때까지. `execution_timeout_ms` 를 정하고, 빈 input 은 보내지 않는다.
- dev 세션의 진행 표시는 워커 2개로 제한한 함수에 최대 5개의 워커가 초기화되는 것을 보여 줬다.
