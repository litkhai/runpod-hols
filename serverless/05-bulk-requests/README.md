# Serverless Lab 05 — Bulk Requests (Batch Jobs)

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** submit a batch of requests to a queue endpoint through the Bulk Requests API, see how and when it runs, and check the advertised discount against billing.

**Time:** ~15 minutes plus billing lag · **Cost:** a few hundredths of a cent on a CPU endpoint (2026-11-07)

### What the console and docs say

Every queue endpoint now has a **Bulk Requests** tab and a banner: *"Run your next large workload as a batch on this endpoint for up to 30% off serverless rates. Batches run on dedicated workers, so your real-time traffic isn't affected."* The [docs](https://docs.runpod.io/serverless/batch-jobs) add: batches run "within 24 hours on a best-effort basis", up to 5,000 requests per batch and 10 active batches per endpoint, and they are "billed at a discounted rate" — with no rate published. Load-balancing endpoints ([lab 04](../04-load-balancer)) have no batch support.

### Files

| File | Role |
|---|---|
| `batch.py` | `submit` (create + finalize), `poll`, `wait`, `results` over `https://api.runpod.ai/v2/<endpoint>/batch` |
| `results/batch1*.json*`, `batch2*.json*` | The two batches below: status polls and every request's output, `delayTime`, `executionTime` |
| `results/gpu_batch*` | The GPU batch at the end |

### Run

```bash
cd serverless/05-bulk-requests
python3 batch.py submit <queue_endpoint_id> --n 30          # prints BATCH_ID=...
python3 batch.py wait <queue_endpoint_id> <batch_id> --every 60
python3 batch.py results <queue_endpoint_id> <batch_id> --out results/batch.json
```

The body is a JSON array of `{"input": ...}` objects, the same shape as `/run`; an empty array makes a draft you can fill and finalize later.

### What the runs showed (01-hello-world, CPU, 2026-11-07)

| | Batch 1 | Batch 2 |
|---|---|---|
| Submitted → completed | 04:32 → by 04:36 UTC | 05:02 → by 05:04 UTC |
| Requests | 30, all `COMPLETED` | 30, all `COMPLETED` |
| Worker | one, `xripev7689qmwz` | one, `9e3s7ph6z6x0wf` |
| `delayTime` | 119.8–158.7 s | 65.9–105.0 s |
| `executionTime` | 136–232 ms | 144–241 ms |

- **"Within 24 hours" was minutes.** Both batches finished two to four minutes after submission, at 13:30 and 14:00 KST on a Saturday.
- **A dedicated worker, one request at a time.** Each batch got a worker the endpoint had not used before, and `delayTime` grew by about 1.3 s per request — the requests ran in sequence on it, not in parallel.
- **No discount on the rate.** The billing API (`/billing/endpoints`, hourly) charged the batch-only hour at **USD 0.0000050 per second** — 45.0 s for USD 0.00022485 — the same rate as hours of ordinary requests to this endpoint (36.3 s for USD 0.0001813). The discount may apply to GPU tiers or arrive as a separate credit; on this CPU endpoint it did not show in billing.
- **It is cheaper all the same.** 30 requests packed on one worker billed 45 s, 1.5 s each; ordinary requests that arrive scattered pay a cold start or idle time each (here about 6 s per request).
- The console's completion notice read *"finished with {requestCompleted} completed"* — the placeholder was not filled.

Billing posts about an hour late and only in hourly buckets, so to price a batch, run it in an hour with no other traffic on the endpoint.

### GPU — RTX A5000 (2026-11-07, 22:03 KST)

Endpoint 02-llm-chat (Qwen2.5-1.5B, model cached on a network volume) pinned to **RTX A5000** for the evening so every hour billed the same GPU; the original GPU list was restored afterwards. Prompt: *"What is Runpod Serverless in two sentences?"*, `max_tokens` 120.

```bash
python3 batch.py submit 3xiuyqtrh6r0zl --n 30 --input '{"prompt":"What is Runpod Serverless in two sentences?","max_tokens":120}'
python3 batch.py wait 3xiuyqtrh6r0zl <batch_id> --every 60
python3 batch.py results 3xiuyqtrh6r0zl <batch_id> --out results/gpu_batch.json
```

| | Result |
|---|---|
| Submitted → completed | 13:04 → by 13:07 UTC, 30 of 30 `COMPLETED` |
| `delayTime` | 93–133 s, about 1.4 s more per request: one worker, in sequence |
| `executionTime` | 0.43–1.05 s, 17.2 s in all |

| Billing hour (UTC) | What ran | Billed time | Amount | Per second |
|---|---|---|---|---|
| 11:00 | Six flex jobs, 20:31–20:43 KST | 342 s | USD 0.0712 | 0.0002085 |
| 12:00 | One active worker, six jobs | 3,419 s | USD 0.7129 | 0.0002085 |
| 13:00 | Active worker to 22:02, one flex job, the 30-request batch | 414 s | USD 0.0818 | 0.0001977 |

- **A small discount showed on the GPU.** The batch hour billed USD 0.0001977 per second against 0.0002085 for the flex and active hours, 5% lower. Two minutes of the [Lab 09](../09-active-workers) active worker and one flex job fell into that hour; taking about 156 s of them out at the ordinary rate leaves the batch at about USD 0.000191/s, roughly 8% off. Disk billed also differs from hour to hour, so treat the figure as approximate — but it is nowhere near the banner's "up to 30%".
- The CPU run above showed no discount at all, so the discount, where there is one, appears on GPU workers.

---

## 한국어

**목표:** Bulk Requests API 로 큐 엔드포인트에 배치를 제출하고, 언제 어떻게 실행되는지 보고, 광고된 할인을 청구 내역과 맞춰 본다.

**시간:** 약 15분 + 청구 반영 지연 · **비용:** CPU 엔드포인트에서 1센트의 몇백분의 일 (2026-11-07)

### 콘솔과 문서가 말하는 것

모든 큐 엔드포인트에 **Bulk Requests** 탭과 배너가 생겼다: *"Run your next large workload as a batch on this endpoint for up to 30% off serverless rates. Batches run on dedicated workers, so your real-time traffic isn't affected."* [문서](https://docs.runpod.io/serverless/batch-jobs)는 배치가 "within 24 hours on a best-effort basis" 로 실행되고, 배치당 최대 5,000 건, 엔드포인트당 활성 배치 10개이며 "billed at a discounted rate" 라고 하지만 요율은 공개하지 않는다. 로드밸런싱 엔드포인트([실습 04](../04-load-balancer))는 배치를 지원하지 않는다.

### 파일

| 파일 | 역할 |
|---|---|
| `batch.py` | `https://api.runpod.ai/v2/<endpoint>/batch` 로 `submit` (생성 + 확정), `poll`, `wait`, `results` |
| `results/batch1*.json*`, `batch2*.json*` | 아래 두 배치: 상태 확인 기록과 요청별 output, `delayTime`, `executionTime` |
| `results/gpu_batch*` | 끝의 GPU 배치 |

### 실행

```bash
cd serverless/05-bulk-requests
python3 batch.py submit <큐_엔드포인트_id> --n 30          # BATCH_ID=... 출력
python3 batch.py wait <큐_엔드포인트_id> <batch_id> --every 60
python3 batch.py results <큐_엔드포인트_id> <batch_id> --out results/batch.json
```

본문은 `/run` 과 같은 `{"input": ...}` 객체의 JSON 배열이다. 빈 배열을 보내면 나중에 채워서 확정할 수 있는 초안이 된다.

### 실행 결과 (01-hello-world, CPU, 2026-11-07)

| | 배치 1 | 배치 2 |
|---|---|---|
| 제출 → 완료 | 04:32 → 04:36 UTC 이전 | 05:02 → 05:04 UTC 이전 |
| 요청 | 30건, 모두 `COMPLETED` | 30건, 모두 `COMPLETED` |
| 워커 | 하나, `xripev7689qmwz` | 하나, `9e3s7ph6z6x0wf` |
| `delayTime` | 119.8–158.7초 | 65.9–105.0초 |
| `executionTime` | 136–232 ms | 144–241 ms |

- **"24시간 내" 는 몇 분이었다.** 두 배치 모두 제출 2–4분 뒤에 끝났다 (토요일 한국 시간 13:30, 14:00).
- **전용 워커 하나가 한 건씩.** 배치마다 엔드포인트가 쓰지 않던 워커가 붙었고, `delayTime` 이 요청마다 약 1.3초씩 늘었다 — 병렬이 아니라 차례로 처리했다.
- **요율 할인은 없었다.** 청구 API (`/billing/endpoints`, 시간 단위) 는 배치만 돈 시간대를 **초당 USD 0.0000050** — 45.0초에 USD 0.00022485 — 로 청구했고, 이 엔드포인트의 일반 요청 시간대 (36.3초에 USD 0.0001813) 와 같은 요율이다. 할인이 GPU 등급에만 적용되거나 별도 크레딧으로 들어올 수도 있지만, 이 CPU 엔드포인트의 청구 내역에는 보이지 않았다.
- **그래도 더 싸다.** 30건을 워커 하나에 몰아 45초, 건당 1.5초가 청구됐다. 흩어져 들어오는 일반 요청은 건마다 콜드 스타트나 유휴 시간을 낸다 (여기서는 건당 약 6초).
- 콘솔의 완료 알림이 *"finished with {requestCompleted} completed"* 로 나왔다 — 자리 표시자가 채워지지 않았다.

청구는 약 1시간 늦게, 시간 단위로만 반영되므로 배치의 비용을 재려면 그 엔드포인트에 다른 요청이 없는 시간대에 돌린다.

### GPU — RTX A5000 (2026-11-07, 22:03 KST)

엔드포인트 02-llm-chat (Qwen2.5-1.5B, 네트워크 볼륨 캐시) 을 그날 저녁 **RTX A5000** 하나로 고정해 모든 시간대가 같은 GPU 로 청구되게 했고, 끝난 뒤 원래 GPU 목록으로 되돌렸다. 프롬프트: *"What is Runpod Serverless in two sentences?"*, `max_tokens` 120.

```bash
python3 batch.py submit 3xiuyqtrh6r0zl --n 30 --input '{"prompt":"What is Runpod Serverless in two sentences?","max_tokens":120}'
python3 batch.py wait 3xiuyqtrh6r0zl <batch_id> --every 60
python3 batch.py results 3xiuyqtrh6r0zl <batch_id> --out results/gpu_batch.json
```

| | 결과 |
|---|---|
| 제출 → 완료 | 13:04 → 13:07 UTC 이전, 30건 모두 `COMPLETED` |
| `delayTime` | 93–133초, 요청마다 약 1.4초씩 증가: 워커 하나가 차례로 처리 |
| `executionTime` | 0.43–1.05초, 합계 17.2초 |

| 청구 시간대 (UTC) | 실행한 것 | 청구 시간 | 금액 | 초당 |
|---|---|---|---|---|
| 11:00 | flex 작업 6건, 20:31–20:43 KST | 342초 | USD 0.0712 | 0.0002085 |
| 12:00 | 활성 워커 하나, 작업 6건 | 3,419초 | USD 0.7129 | 0.0002085 |
| 13:00 | 22:02 까지 활성 워커, flex 작업 1건, 30건 배치 | 414초 | USD 0.0818 | 0.0001977 |

- **GPU 에서는 작은 할인이 보였다.** 배치 시간대는 초당 USD 0.0001977 로, flex·활성 시간대의 0.0002085 보다 5% 낮았다. 그 시간대에는 [실습 09](../09-active-workers) 의 활성 워커 2분과 flex 작업 1건이 섞여 있다. 이 약 156초를 일반 요율로 빼면 배치는 초당 약 USD 0.000191, 대략 8% 할인이다. 시간대마다 청구된 디스크 양도 달라 근삿값으로 봐야 하지만, 배너의 "최대 30%" 와는 거리가 멀다.
- 위 CPU 실행에서는 할인이 전혀 없었으니, 할인이 있다면 GPU 워커에서 나타난다.
