# Serverless Lab 08 — Job Lifecycle

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** take jobs on one queue endpoint through every way they can end — completed, failed, cancelled, timed out, expired, purged, retried — and record exactly what the API returns for each.

**Time:** ~10 minutes · **Cost:** a fraction of a cent on a CPU endpoint (2026-11-07)

### Files

| File | Role |
|---|---|
| `lifecycle.py` | Runs every case below in order and saves each raw response |
| `results/lifecycle.json` | The responses, with the time each status was first seen |
| `results/retention.log` | `/status` of finished jobs every two minutes until they were gone |

Worker: the probe from [`../06-autoscaling`](../06-autoscaling) (modes `sleep`, `fail`, `error_output`), CPU 2 vCPU, two workers taking four jobs each.

```bash
python3 lifecycle.py <endpoint_id> --out results/lifecycle.json
```

### What each case returned (2026-11-07)

| Case | How | Final `/status` |
|---|---|---|
| Short `/runsync` | 1 s job | `COMPLETED` with `output`, after 5.6 s including a 4.1 s start |
| Long `/runsync` | 100 s job | Returned after **90.5 s** with `IN_PROGRESS` and the id; `/status` showed `COMPLETED` later |
| Handler returns `{"error": ...}` | `error_output` | `FAILED`, `error` = the string as returned |
| Handler raises | `fail` | `FAILED`, `error` = JSON with type, message, **full traceback, hostname, worker id, SDK version** |
| Retry | `POST /retry/<id>` on the failed job | Same id back to `IN_QUEUE`, ran again, `FAILED` again; `/health` counted `retried: 1` |
| Cancel while running | `POST /cancel/<id>` on a 60 s job | `CANCELLED` — but the cancel call itself took **~21 s** to return |
| Cancel while queued | `POST /cancel/<id>` | `CANCELLED` at once |
| Purge | `POST /purge-queue` | `{"removed": 10}`; running jobs finished, every purged job then answered **404 "job not found"** |
| Execution timeout | `"policy": {"executionTimeout": 5000}`, 30 s job | `FAILED`, `error: "executionTimeout exceeded"`, after **12.4 s** of execution |
| Queue TTL | `"policy": {"ttl": 10000}` while the workers were busy | Gone: **404** about 12 s after submission, no final status |

Results stay readable for a limited time: finished `/run` jobs answered `/status` for about **28–30 minutes** after completion, then 404; a `/runsync` result was already gone 13 minutes later.

What this means for a client:

- **`FAILED` covers three different things** — a raised exception, an `error` key in the output, and an execution timeout. Tell them apart by the `error` text.
- **A raised exception leaks internals** to whoever reads the status: the traceback with file paths, the hostname and worker id. Catch exceptions in the handler and return a clean `{"error": ...}` if callers are outside your team.
- **404 is an outcome, not just a typo.** A purged job, an expired job and an old result all answer `job not found`. A client that polls must treat 404 after a successful submit as "lost", not retry the poll forever.
- **`/runsync` gives up at about 90 s** and hands back an id; a client using it for long jobs must fall back to `/status`.
- **The execution timeout is enforced late** — 7 s over the 5 s limit here — so do not rely on it for exact cut-offs.
- Webhooks (`"webhook": url`) were not tested: they need a public receiver.

---

## 한국어

**목표:** 큐 엔드포인트 하나에서 작업이 끝날 수 있는 모든 방식 — 완료, 실패, 취소, 시간 초과, 만료, purge, 재시도 — 을 거쳐 보고, 각각 API 가 정확히 무엇을 돌려주는지 기록한다.

**시간:** 약 10분 · **비용:** CPU 엔드포인트에서 1센트 미만 (2026-11-07)

### 파일

| 파일 | 역할 |
|---|---|
| `lifecycle.py` | 아래 경우를 차례로 실행하고 응답을 그대로 저장 |
| `results/lifecycle.json` | 응답과 각 상태가 처음 보인 시각 |
| `results/retention.log` | 끝난 작업의 `/status` 를 사라질 때까지 2분마다 기록 |

워커: [`../06-autoscaling`](../06-autoscaling) 의 프로브 (`sleep`, `fail`, `error_output` 모드), CPU 2 vCPU, 워커 둘이 각자 네 건씩 처리.

```bash
python3 lifecycle.py <endpoint_id> --out results/lifecycle.json
```

### 경우별 결과 (2026-11-07)

| 경우 | 방법 | 최종 `/status` |
|---|---|---|
| 짧은 `/runsync` | 1초 작업 | 4.1초 기동을 포함해 5.6초 뒤 `output` 과 함께 `COMPLETED` |
| 긴 `/runsync` | 100초 작업 | **90.5초** 뒤 `IN_PROGRESS` 와 id 를 돌려줌; 나중에 `/status` 가 `COMPLETED` |
| 핸들러가 `{"error": ...}` 반환 | `error_output` | `FAILED`, `error` = 반환한 문자열 그대로 |
| 핸들러가 예외 발생 | `fail` | `FAILED`, `error` = 유형·메시지·**전체 트레이스백·호스트 이름·워커 id·SDK 버전** 이 든 JSON |
| 재시도 | 실패한 작업에 `POST /retry/<id>` | 같은 id 가 `IN_QUEUE` 로 돌아가 다시 실행, 다시 `FAILED`; `/health` 에 `retried: 1` |
| 실행 중 취소 | 60초 작업에 `POST /cancel/<id>` | `CANCELLED` — 다만 취소 호출 자체가 돌아오는 데 **약 21초** |
| 대기 중 취소 | `POST /cancel/<id>` | 즉시 `CANCELLED` |
| Purge | `POST /purge-queue` | `{"removed": 10}`; 실행 중인 작업은 끝까지 돌았고, purge 된 작업은 모두 **404 "job not found"** |
| 실행 시간 제한 | `"policy": {"executionTimeout": 5000}`, 30초 작업 | 실행 **12.4초** 뒤 `FAILED`, `error: "executionTimeout exceeded"` |
| 대기열 TTL | 워커가 바쁠 때 `"policy": {"ttl": 10000}` | 사라짐: 제출 약 12초 뒤 **404**, 최종 상태 없음 |

결과는 한정된 시간만 읽을 수 있다. 끝난 `/run` 작업은 완료 후 약 **28–30분** 동안 `/status` 에 답하고 그 뒤 404 였다. `/runsync` 결과는 13분 뒤 이미 없었다.

클라이언트에 주는 의미:

- **`FAILED` 는 세 가지를 뜻한다** — 예외 발생, 출력의 `error` 키, 실행 시간 초과. `error` 내용으로 구분한다.
- **예외는 내부 정보를 드러낸다.** 상태를 읽는 누구에게나 파일 경로가 든 트레이스백, 호스트 이름, 워커 id 가 보인다. 호출자가 팀 밖이라면 핸들러에서 예외를 잡아 깔끔한 `{"error": ...}` 를 돌려준다.
- **404 는 오타만이 아니라 결과다.** purge 된 작업, 만료된 작업, 오래된 결과가 모두 `job not found` 로 답한다. 폴링하는 클라이언트는 제출에 성공한 뒤의 404 를 "잃어버림" 으로 처리해야지, 끝없이 다시 묻지 않아야 한다.
- **`/runsync` 는 약 90초에서 포기하고** id 를 돌려준다. 긴 작업에 쓰는 클라이언트는 `/status` 로 넘어가야 한다.
- **실행 시간 제한은 늦게 적용된다** — 여기서는 5초 제한에 7초 초과 — 정확한 차단에 기대지 않는다.
- 웹훅 (`"webhook": url`) 은 공개 수신 서버가 필요해 시험하지 않았다.
