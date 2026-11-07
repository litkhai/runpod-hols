# Serverless Lab 06 — Autoscaling and Concurrency

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** send the same burst of jobs to one queue endpoint under each scaler type and under per-worker concurrency, and see how many workers start, when, and when they stop.

**Time:** ~30 minutes · **Cost:** under one cent on a 2 vCPU CPU endpoint (2026-11-07)

### Files

| File | Role |
|---|---|
| `handler.py` | Probe worker shared with labs 07–08: sleeps, fails or streams on request; reports its worker id, uptime, and how many jobs it was running when this one started |
| `Dockerfile`, `requirements.txt` | `python:3.11-slim` + `runpod~=1.12.0`; deployed from GitHub in the console |
| `burst.py` | Submits N jobs with `/run` at once, polls `/status` and `/health` until all finish |
| `results/*.json` | Every job's `delayTime`, `executionTime`, `workerId` and the handler's own timing |

### Setup

Endpoint `06-autoscaling`, deployed from this folder through the console's GitHub integration: CPU 2 vCPU / 8 GB, max workers 5, active workers 0, idle timeout 5 s, FlashBoot off. Two settings are changed between runs:

```bash
# scaler: PATCH the endpoint
curl -X PATCH https://rest.runpod.io/v1/endpoints/<id> -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H 'Content-Type: application/json' -d '{"scalerType":"REQUEST_COUNT","scalerValue":25}'
# concurrency: PATCH the template env; the workers are replaced with new ones
curl -X PATCH https://rest.runpod.io/v1/templates/<template_id> ... -d '{"env":{"CONCURRENCY":"4"}}'
python3 burst.py <id> --jobs 50 --seconds 2 --label request_count25_c4 --out results/request_count25_c4.json
```

The two scaler types, from the console: **Queue delay** adds a worker when a request has waited longer than N seconds; **Request count** keeps one worker per N requests in the queue and in progress.

### Results — 50 jobs of 2 s each (2026-11-07)

| Run | Scaler | Concurrency | Workers used | All done after | `delayTime` |
|---|---|---|---|---|---|
| `queue_delay_c1` | Queue delay, 4 s | 1 | 5 (3 at once, 2 more ~1.5 s later) | 42.6 s | 3.6–34.3 s |
| `request_count25_c1` | Request count, 25 | 1 | 2, the second retired after 13 jobs | 135.6 s | 3.1–132.0 s |
| `request_count25_c4` | Request count, 25 | 4 | 2, the first retired after 16 jobs | 36.0 s | 3.6–31.5 s |

The sum of `executionTime` was 110 s in every run; only how it was spread changed.

- **Queue delay went straight to the cap.** With 50 jobs waiting, every worker the endpoint allowed was busy within two seconds and each ran exactly 10 jobs.
- **Request count follows the backlog down, too.** 50 queued over 25 gave two workers; once the queue fell under 25 one of them was retired, and a single worker ran the remaining 37 jobs alone for another 85 s. Set the value for the backlog you can tolerate per worker, not for the peak.
- **Concurrency multiplied a worker's throughput.** With `CONCURRENCY=4` the same two workers ran four jobs each at a time (`running_at_start` up to 4) and finished in 36 s instead of 136 s. For I/O-bound or batching handlers this is the cheapest scale-out: more work per billed worker-second.
- **One-at-a-time workers lose ~1.3 s between jobs.** A worker with concurrency 1 started a 2 s job every 3.3–3.6 s. The gap is the SDK fetching the next job; short jobs pay it proportionally more.
- **Every first job paid ~3 s of start-up.** `delayTime` never went below 3.1 s, and each worker's uptime was ~2.5 s at its first job: even a worker shown as *idle* starts its container on demand.

Things noticed on the way:

- After the build, `/health` showed **five idle workers** — as many as the max — and kept showing `idle: 5` for ~20 s after jobs started running. Treat `/health` as late by tens of seconds.
- Changing the template env replaced all workers (new worker ids) without a new build.
- `GET /v1/templates/<id>` returned 404 for this GitHub-built template, while `PATCH` on the same id worked.

---

## 한국어

**목표:** 같은 양의 작업을 큐 엔드포인트 하나에 스케일러 유형별로, 그리고 워커당 동시성을 바꿔 보내서, 워커가 몇 개 언제 뜨고 언제 내려가는지 본다.

**시간:** 약 30분 · **비용:** 2 vCPU CPU 엔드포인트에서 1센트 미만 (2026-11-07)

### 파일

| 파일 | 역할 |
|---|---|
| `handler.py` | 실습 07–08 과 같이 쓰는 프로브 워커: 요청에 따라 대기·실패·스트리밍하고, 워커 id, 가동 시간, 이 작업이 시작될 때 처리 중이던 작업 수를 보고 |
| `Dockerfile`, `requirements.txt` | `python:3.11-slim` + `runpod~=1.12.0`; 콘솔에서 GitHub 로 배포 |
| `burst.py` | `/run` 으로 작업 N 개를 한꺼번에 보내고, 모두 끝날 때까지 `/status` 와 `/health` 를 확인 |
| `results/*.json` | 작업별 `delayTime`, `executionTime`, `workerId` 와 핸들러가 잰 시각 |

### 준비

엔드포인트 `06-autoscaling`, 이 폴더를 콘솔의 GitHub 연동으로 배포: CPU 2 vCPU / 8 GB, 최대 워커 5, 활성 워커 0, 유휴 타임아웃 5초, FlashBoot 끔. 실행 사이에 두 설정을 바꾼다:

```bash
# 스케일러: 엔드포인트를 PATCH
curl -X PATCH https://rest.runpod.io/v1/endpoints/<id> -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H 'Content-Type: application/json' -d '{"scalerType":"REQUEST_COUNT","scalerValue":25}'
# 동시성: 템플릿 env 를 PATCH; 워커가 새 워커로 교체된다
curl -X PATCH https://rest.runpod.io/v1/templates/<template_id> ... -d '{"env":{"CONCURRENCY":"4"}}'
python3 burst.py <id> --jobs 50 --seconds 2 --label request_count25_c4 --out results/request_count25_c4.json
```

콘솔이 설명하는 두 스케일러: **Queue delay** 는 요청이 N 초 넘게 기다리면 워커를 더하고, **Request count** 는 대기·처리 중인 요청 N 개마다 워커 하나를 유지한다.

### 결과 — 2초짜리 작업 50개 (2026-11-07)

| 실행 | 스케일러 | 동시성 | 쓴 워커 | 모두 끝난 시점 | `delayTime` |
|---|---|---|---|---|---|
| `queue_delay_c1` | Queue delay, 4초 | 1 | 5 (3개 동시, 2개는 약 1.5초 뒤) | 42.6초 | 3.6–34.3초 |
| `request_count25_c1` | Request count, 25 | 1 | 2, 두 번째는 13건 뒤 내려감 | 135.6초 | 3.1–132.0초 |
| `request_count25_c4` | Request count, 25 | 4 | 2, 첫 번째는 16건 뒤 내려감 | 36.0초 | 3.6–31.5초 |

`executionTime` 의 합은 모든 실행에서 110초였다. 바뀐 것은 그것이 어떻게 나뉘었는지뿐이다.

- **Queue delay 는 곧바로 상한까지 갔다.** 50건이 대기하자 허용된 워커 전부가 2초 안에 일을 시작했고 각자 정확히 10건씩 처리했다.
- **Request count 는 줄어드는 대기열도 따라간다.** 50건 ÷ 25 로 워커 둘이 떴다가, 대기열이 25 아래로 내려가자 하나가 내려갔고, 남은 37건을 워커 하나가 85초 더 혼자 처리했다. 값은 최대치가 아니라 워커 하나가 감당해도 되는 대기량에 맞춰 정한다.
- **동시성은 워커 하나의 처리량을 곱했다.** `CONCURRENCY=4` 에서 같은 워커 둘이 각자 네 건씩 동시에 처리했고 (`running_at_start` 최대 4), 136초 대신 36초에 끝났다. I/O 위주이거나 배치로 묶는 핸들러에는 가장 싼 확장이다 — 청구되는 워커-초당 처리량이 늘어난다.
- **한 번에 하나씩 처리하는 워커는 작업 사이에 약 1.3초를 잃는다.** 동시성 1 워커는 2초짜리 작업을 3.3–3.6초마다 시작했다. 다음 작업을 가져오는 SDK 의 시간이고, 짧은 작업일수록 비중이 크다.
- **첫 작업은 모두 약 3초의 기동 시간을 냈다.** `delayTime` 은 3.1초 밑으로 내려가지 않았고, 각 워커의 첫 작업 시점 가동 시간은 약 2.5초였다. *idle* 로 보이는 워커도 요청이 와야 컨테이너를 띄운다.

진행 중에 본 것:

- 빌드 뒤 `/health` 는 **idle 워커 5개** — 최대치만큼 — 를 보였고, 작업이 돌기 시작한 뒤에도 약 20초 동안 `idle: 5` 를 유지했다. `/health` 는 수십 초 늦는다고 보자.
- 템플릿 env 를 바꾸자 새 빌드 없이 워커가 모두 교체됐다 (새 워커 id).
- 이 GitHub 빌드 템플릿에 `GET /v1/templates/<id>` 는 404 를 돌려줬지만, 같은 id 로 `PATCH` 는 됐다.
