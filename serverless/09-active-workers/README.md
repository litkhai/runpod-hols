# Serverless Lab 09 — Active Workers

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** keep one active worker (`workersMin` 1) on a CPU queue endpoint for a clock hour, check whether requests skip the cold start, and compare the billed rate with flex hours on the same endpoint.

**Time:** one clock hour plus about an hour of billing lag · **Cost:** USD 0.018 for the hour (CPU 2 vCPU, 2026-11-07)

### Files

| File | Role |
|---|---|
| `active.py` | At `--start` PATCHes `workersMin` 1, sends a 1 s job with `/runsync` every `--every` minutes, PATCHes `workersMin` 0 at the end, then sends one more job two minutes later |
| `results/active.json` | Each PATCH and each job: `delayTime`, `executionTime`, `workerId`, the worker's uptime |

Worker: the probe from [`../06-autoscaling`](../06-autoscaling), on that lab's endpoint (CPU 2 vCPU, max 5 workers, idle timeout 5 s).

```bash
python3 active.py <endpoint_id> --start 17:00 --minutes 60 --every 10 --out results/active.json
# about an hour after the end
curl -s -H "Authorization: Bearer $RUNPOD_API_KEY" \
  "https://rest.runpod.io/v1/billing/endpoints?endpointId=<endpoint_id>&bucketSize=hour&startTime=2026-11-07T00:00:00Z"
```

Start on the hour: billing comes only in hourly buckets, so the active hour should share its bucket with nothing else.

### What the run showed (17:00–18:00 KST = 08:00–09:00 UTC, 2026-11-07)

| Job | Time (KST) | `delayTime` | Worker | Worker uptime |
|---|---|---|---|---|
| active_0 | 17:02 | 4.4 s | `agh3ew1fbn2zhq` | 1.9 s |
| active_1 … active_5 | 17:12–17:52 | 0.09 s (0.71 s once) | the same | 597 → 2,997 s |
| after `workersMin` 0 | 18:04 | 3.6 s | `7c6ci2hwp9opwa` | 1.8 s |

| Billing hour (UTC) | What ran | Billed time | Amount | Per second |
|---|---|---|---|---|
| 06:00 | Labs 06–08, flex | 458 s | USD 0.00235 | 0.00000513 |
| 07:00 | Labs 06–08, flex | 616 s | USD 0.00319 | 0.00000519 |
| **08:00** | **One active worker** | **3,353 s** | **USD 0.01746** | **0.00000521** |
| 09:00 | Two minutes of active, then one flex job | 282 s | USD 0.00141 | 0.00000500 |

- **The first request still paid a cold start.** `workersMin` 1 was set at 17:00:00, but the worker's handler started only when the first job arrived at 17:02 (`delayTime` 4.4 s, uptime 1.9 s).
- **After that, one worker stayed for the hour.** The same worker served every job, its uptime grew by 600 s between jobs, and `delayTime` stayed at about 0.09 s against 3.6–4.4 s cold.
- **No active-worker discount on this CPU endpoint.** The active hour billed USD 0.0000052 per second, the same as the flex hours (0.0000050–0.0000052); the differences follow the disk billed in each hour. The advertised discount may apply to GPU workers only.
- **Billing counted 3,353 of 3,600 s.** That is about 93 % of the hour, close to the time from the worker's start at 17:02 to the end of the hour.
- **The cost of skipping cold starts.** Six jobs in the hour billed 3,353 s with an active worker. The same six on flex would have billed a few seconds each, under 60 s in all, so here an always-on worker cost more than fifty times as much to save about 4 s per request.

Only keep a worker active where the latency matters on every request, and when traffic is steady enough to keep it busy.

---

## 한국어

**목표:** CPU 큐 엔드포인트에 활성 워커 (`workersMin` 1) 하나를 정각부터 한 시간 켜 두고, 요청이 콜드 스타트를 건너뛰는지, 같은 엔드포인트의 flex 시간대와 비교해 청구 요율이 어떤지 본다.

**시간:** 정각부터 한 시간 + 청구 반영 약 1시간 · **비용:** 한 시간에 USD 0.018 (CPU 2 vCPU, 2026-11-07)

### 파일

| 파일 | 역할 |
|---|---|
| `active.py` | `--start` 에 `workersMin` 1 로 PATCH, `--every` 분마다 1초짜리 작업을 `/runsync` 로 보내고, 끝나면 `workersMin` 0 으로 PATCH 한 뒤 2분 뒤에 작업을 한 번 더 보낸다 |
| `results/active.json` | PATCH 와 작업마다 `delayTime`, `executionTime`, `workerId`, 워커 가동 시간 |

워커: [`../06-autoscaling`](../06-autoscaling) 의 프로브를 그 실습의 엔드포인트 (CPU 2 vCPU, 최대 워커 5, 유휴 제한 5초) 에서 그대로 쓴다.

```bash
python3 active.py <엔드포인트_id> --start 17:00 --minutes 60 --every 10 --out results/active.json
# 끝나고 약 1시간 뒤
curl -s -H "Authorization: Bearer $RUNPOD_API_KEY" \
  "https://rest.runpod.io/v1/billing/endpoints?endpointId=<엔드포인트_id>&bucketSize=hour&startTime=2026-11-07T00:00:00Z"
```

정각에 시작한다. 청구는 시간 단위로만 나오므로 활성 시간대가 다른 사용과 한 칸에 섞이지 않아야 한다.

### 실행 결과 (2026-11-07 17:00–18:00 KST = 08:00–09:00 UTC)

| 작업 | 시각 (KST) | `delayTime` | 워커 | 워커 가동 시간 |
|---|---|---|---|---|
| active_0 | 17:02 | 4.4초 | `agh3ew1fbn2zhq` | 1.9초 |
| active_1 … active_5 | 17:12–17:52 | 0.09초 (한 번 0.71초) | 같은 워커 | 597 → 2,997초 |
| `workersMin` 0 이후 | 18:04 | 3.6초 | `7c6ci2hwp9opwa` | 1.8초 |

| 청구 시간대 (UTC) | 실행한 것 | 청구 시간 | 금액 | 초당 |
|---|---|---|---|---|
| 06:00 | 실습 06–08, flex | 458초 | USD 0.00235 | 0.00000513 |
| 07:00 | 실습 06–08, flex | 616초 | USD 0.00319 | 0.00000519 |
| **08:00** | **활성 워커 하나** | **3,353초** | **USD 0.01746** | **0.00000521** |
| 09:00 | 활성 2분, 이후 flex 작업 하나 | 282초 | USD 0.00141 | 0.00000500 |

- **첫 요청은 여전히 콜드 스타트를 냈다.** 17:00:00 에 `workersMin` 1 로 바꿨지만, 워커의 핸들러는 첫 작업이 들어온 17:02 에야 시작했다 (`delayTime` 4.4초, 가동 시간 1.9초).
- **그 뒤로는 워커 하나가 한 시간 내내 있었다.** 모든 작업을 같은 워커가 처리했고, 가동 시간은 작업마다 600초씩 늘었으며, `delayTime` 은 콜드일 때 3.6–4.4초에 비해 약 0.09초에 머물렀다.
- **이 CPU 엔드포인트에서는 활성 워커 할인이 없었다.** 활성 시간대는 초당 USD 0.0000052 로, flex 시간대 (0.0000050–0.0000052) 와 같다. 차이는 시간대마다 청구된 디스크 양을 따라간다. 광고된 할인은 GPU 워커에만 적용될 수 있다.
- **청구는 3,600초 중 3,353초였다.** 한 시간의 약 93 % 로, 17:02 에 워커가 시작한 뒤 정각까지의 시간과 비슷하다.
- **콜드 스타트를 없앤 값.** 활성 워커로 한 시간에 작업 6건을 처리하는 데 3,353초가 청구됐다. 같은 6건을 flex 로 보냈다면 건당 몇 초, 모두 합쳐 60초 미만이었을 것이다. 여기서는 상시 워커가 요청당 약 4초를 줄이는 데 50배 넘게 들었다.

모든 요청에서 지연이 중요하고, 워커를 계속 바쁘게 할 만큼 트래픽이 꾸준할 때만 활성 워커를 둔다.
