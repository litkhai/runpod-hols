# Serverless Lab 04 — Load-Balancing Endpoints

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** deploy a worker that is a plain HTTP server, call it through a load-balancing endpoint, and compare it with a queue endpoint on cold and warm requests.

**Time:** ~30 minutes · **Cost:** under USD 0.10 on 2026-11-07 (a few minutes of a CPU worker)

### Queue vs load balancer

| | Queue (labs 01–03) | Load balancer (this lab) |
|---|---|---|
| Worker | A handler, `runpod.serverless.start()` | Any HTTP server; no runpod SDK |
| URL | `https://api.runpod.ai/v2/<id>/run`, `/runsync` | `https://<id>.api.runpod.ai/<your path>` |
| No worker ready | The job waits in the queue | The request is held, then refused |
| Retries | Built in | None — the client retries |
| Health | Fitness checks inside the SDK | The platform polls `GET /ping`: 204 starting, 200 ready |
| Scaling | Queue delay or request count | Request count only |
| Limits | | 30 MB payload, 5.5 min per request ([docs](https://docs.runpod.io/serverless/load-balancing/overview)) |

### Files

| File | Role |
|---|---|
| `app.py` | FastAPI server: `GET /ping` returns 204 for the first `WARMUP_S` seconds (default 5), then 200; `POST /hello` greets and reports which worker answered |
| `Dockerfile` | `python:3.11-slim`, `PORT=80`, `PORT_HEALTH=80` |
| `bench.py` | Idle for `--gap` seconds, then one cold and `--warm` warm requests to each endpoint; load-balancer calls retry while refused, and every attempt is kept |
| `results/run1.json`, `run2.json` | The two runs below |

### Deploy

The REST API cannot create one: `POST /endpoints` has no endpoint-type field. Create it in the console:

1. **Serverless → New endpoint → Deploy from a GitHub repository**, pick this repository.
2. **Branch** `main`, **Dockerfile path** `/serverless/04-load-balancer/Dockerfile`, **Advanced settings → Build context** `/serverless/04-load-balancer`.
3. Choose **Load balancer** (not Queue). The console warns if it cannot find a `/ping` route on the default branch.
4. **CPU**, the smallest instance, **Max workers** 1. The form's only scaling option is **Request count** — "Load Balancer endpoints only support request count scaling".
5. Deploy. Runpod builds the image from the repository; the endpoint shows **Ready** once the build completes.

Then:

```bash
python3 bench.py <load_balancer_endpoint_id> <queue_endpoint_id> --gap 60 --warm 5 --out results/run1.json
```

### What the runs showed (2026-11-07)

| | Load balancer | Queue (01-hello-world) |
|---|---|---|
| Instance | `cpu5g-32-128` | `cpu5g-2-8` |
| Cold request, total | **38.6 s, 34.0 s** | 4.7 s, 5.1 s (`delayTime` 4.1, 4.5 s) |
| Warm requests | **0.34–0.75 s** | 1.23–1.38 s (`delayTime` 0.83–0.89 s) |

- **A cold request is held, then refused.** The first call waited 33.2 s and 28.2 s and got **HTTP 502**; the retry 5 s later succeeded in under a second. The worker that answered had been up 36.7 s and 31.3 s, of which 5 s was this app's own warm-up. The docs speak of `no workers available` errors; what came back here was a bare `error code: 502`.
- **Warm requests are 2–4× faster.** No queue, no status round trip: 0.34–0.75 s end to end against 1.2–1.4 s for `/runsync`, whose `delayTime` alone was 0.83–0.89 s.
- **Cold starts are slower here**, not faster: 34–39 s against 5 s for the queue endpoint's cold worker. The image was already on the host ("Image is up to date"), so the time is container start, the health-check cycle and routing.
- **The response is yours.** There is no `delayTime`, `executionTime` or `workerId`; the app returns its own worker id and timings. The console's Metrics still counted the requests (14 total, 3 failed — the 502s).
- `GET /ping` with no worker running timed out at 30 s rather than answering 204.
- The console shows a **Test** tab (method, path, body) in place of Requests, and no Bulk Requests tab.


The two endpoints ran on different CPU instances, and the load-balancing form came up with the 32 vCPU option already selected — check it before deploying. A hello-world handler does not use the cores, so the latency gap is the routing model, not the hardware.

**When to use it:** latency-sensitive HTTP or streaming APIs with a warm worker (Active workers ≥ 1, or steady traffic), and clients that retry. Keep the queue for long jobs, batches, and anything that must not be dropped while scaling from zero.

---

## 한국어

**목표:** 평범한 HTTP 서버인 워커를 배포해 로드밸런싱 엔드포인트로 호출하고, 콜드·웜 요청에서 큐 엔드포인트와 비교한다.

**시간:** 약 30분 · **비용:** 2026-11-07 기준 USD 0.10 미만 (CPU 워커 몇 분)

### 큐 vs 로드밸런서

| | 큐 (실습 01–03) | 로드밸런서 (이 실습) |
|---|---|---|
| 워커 | 핸들러, `runpod.serverless.start()` | 아무 HTTP 서버. runpod SDK 불필요 |
| URL | `https://api.runpod.ai/v2/<id>/run`, `/runsync` | `https://<id>.api.runpod.ai/<경로>` |
| 준비된 워커가 없을 때 | 작업이 큐에서 기다림 | 요청을 붙잡고 있다가 거절 |
| 재시도 | 내장 | 없음 — 클라이언트가 재시도 |
| 헬스 체크 | SDK 안의 적합성 검사 | 플랫폼이 `GET /ping` 을 확인: 기동 중 204, 준비 200 |
| 스케일링 | 큐 지연 또는 요청 수 | 요청 수만 |
| 한도 | | 페이로드 30 MB, 요청당 5.5분 ([문서](https://docs.runpod.io/serverless/load-balancing/overview)) |

### 파일

| 파일 | 역할 |
|---|---|
| `app.py` | FastAPI 서버: `GET /ping` 은 처음 `WARMUP_S` 초(기본 5) 동안 204, 이후 200. `POST /hello` 는 인사와 응답한 워커를 돌려준다 |
| `Dockerfile` | `python:3.11-slim`, `PORT=80`, `PORT_HEALTH=80` |
| `bench.py` | `--gap` 초 쉰 뒤 각 엔드포인트에 콜드 1건, 웜 `--warm` 건. 로드밸런서 호출은 거절되면 재시도하고 모든 시도를 남긴다 |
| `results/run1.json`, `run2.json` | 아래 두 번의 실행 |

### 배포

REST API 로는 만들 수 없다. `POST /endpoints` 에 엔드포인트 유형 필드가 없다. 콘솔에서 만든다:

1. **Serverless → New endpoint → Deploy from a GitHub repository**, 이 저장소 선택.
2. **Branch** `main`, **Dockerfile path** `/serverless/04-load-balancer/Dockerfile`, **Advanced settings → Build context** `/serverless/04-load-balancer`.
3. **Load balancer** 선택 (Queue 아님). 기본 브랜치에서 `/ping` 경로를 못 찾으면 콘솔이 경고한다.
4. **CPU**, 가장 작은 인스턴스, **Max workers** 1. 스케일링은 **Request count** 하나뿐이다 — "Load Balancer endpoints only support request count scaling".
5. 배포. Runpod 이 저장소에서 이미지를 빌드하고, 빌드가 끝나면 엔드포인트가 **Ready** 가 된다.

그다음:

```bash
python3 bench.py <로드밸런서_엔드포인트_id> <큐_엔드포인트_id> --gap 60 --warm 5 --out results/run1.json
```

### 실행 결과 (2026-11-07)

| | 로드밸런서 | 큐 (01-hello-world) |
|---|---|---|
| 인스턴스 | `cpu5g-32-128` | `cpu5g-2-8` |
| 콜드 요청, 전체 | **38.6초, 34.0초** | 4.7초, 5.1초 (`delayTime` 4.1, 4.5초) |
| 웜 요청 | **0.34–0.75초** | 1.23–1.38초 (`delayTime` 0.83–0.89초) |

- **콜드 요청은 붙잡혀 있다가 거절된다.** 첫 호출은 33.2초, 28.2초를 기다린 뒤 **HTTP 502** 를 받았고, 5초 뒤 재시도는 1초 안에 성공했다. 응답한 워커는 36.7초, 31.3초째 떠 있었고 그중 5초는 이 앱의 자체 워밍업이다. 문서는 `no workers available` 오류를 말하지만, 여기서 돌아온 것은 `error code: 502` 뿐이었다.
- **웜 요청은 2–4배 빠르다.** 큐도 상태 왕복도 없다. 종단 0.34–0.75초로, `delayTime` 만 0.83–0.89초인 `/runsync` 의 1.2–1.4초보다 빠르다.
- **콜드 스타트는 더 느렸다.** 큐 엔드포인트의 콜드 워커 5초에 비해 34–39초. 이미지는 이미 호스트에 있었으므로("Image is up to date") 컨테이너 시작, 헬스 체크 주기, 라우팅에 든 시간이다.
- **응답은 앱의 것이다.** `delayTime`, `executionTime`, `workerId` 가 없고, 앱이 자기 워커 id 와 시간을 돌려준다. 콘솔 Metrics 는 요청을 세었다 (전체 14, 실패 3 — 502).
- 워커가 없을 때 `GET /ping` 은 204 를 주지 않고 30초에 시간 초과됐다.
- 콘솔에는 Requests 대신 **Test** 탭(메서드, 경로, 본문)이 있고 Bulk Requests 탭이 없다.


두 엔드포인트는 서로 다른 CPU 인스턴스에서 돌았다. 로드밸런싱 생성 화면은 32 vCPU 옵션이 이미 선택된 채로 열렸으니 배포 전에 확인할 것. hello-world 는 코어를 쓰지 않으므로 지연 차이는 하드웨어가 아니라 라우팅 방식에서 온다.

**언제 쓰나:** 웜 워커가 있고(Active workers ≥ 1, 또는 꾸준한 트래픽) 클라이언트가 재시도하는, 지연에 민감한 HTTP·스트리밍 API. 긴 작업, 배치, 0 에서 확장하는 동안 버려지면 안 되는 요청은 큐를 쓴다.
