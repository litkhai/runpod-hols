# Serverless Lab 07 — Streaming

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** stream a generator handler's output through `/stream` and measure when each chunk reaches the client, compared with when the worker produced it — the time-to-first-token question for any LLM endpoint.

**Time:** ~15 minutes · **Cost:** a fraction of a cent on a CPU endpoint (2026-11-07)

### Files

| File | Role |
|---|---|
| `stream.py` | Submits with `/run`, polls `/stream/<id>` until done, records every chunk's arrival; then one `/runsync` of the same input |
| `results/stream_20x0.5.json` | 20 chunks, one every 0.5 s (5 runs) |
| `results/stream_200x0.02.json` | 200 chunks, one every 20 ms, like tokens (3 runs) |

Worker: the probe from [`../06-autoscaling`](../06-autoscaling) with template env `HANDLER_KIND=stream`, which starts it as an async generator with `return_aggregate_stream: True`. Each chunk carries `t`, seconds since the handler started.

```bash
python3 stream.py <endpoint_id> --chunks 200 --every 0.02 --runs 3 --out results/stream_200x0.02.json
```

### Results (2026-11-07, CPU 2 vCPU)

| | 20 chunks × 0.5 s | 200 chunks × 20 ms |
|---|---|---|
| First chunk at the client, warm worker | 1.6–1.7 s (0.8 s `delayTime` + 0.5 s to make it + ~0.35 s) | 0.95 s |
| First chunk, worker starting | 4.5 s | 3.9–6.4 s |
| Chunk made → chunk received | 0.31–0.37 s median | 0.51–0.55 s median, up to 1.7 s |
| Chunks per `/stream` call | 1 | 4–5, once 20 |
| Handler time for the chunks | 11.1 s for 10 s of sleeps | **13.0–13.4 s for 4 s of sleeps** |
| `/runsync` of the same input | Everything at once after 12.2 s | Everything at once after 14.9 s |

- **`/stream` is a long poll.** Each call waited for new chunks and returned as soon as there were some — one per call at 0.5 s spacing, four or five at 20 ms. No need to sleep between calls.
- **Each chunk reached the client about a third to half a second after it was made.** Fine for a chat UI; it sets a floor on time to first token on top of `delayTime`.
- **Every `yield` cost the handler about 45–55 ms.** Two hundred 20 ms chunks took 13 s instead of 4 s: the generator was held up after each yield. A model producing 50 tokens per second and yielding each token would be throttled to under 15. **Yield groups of tokens**, not single ones.
- **`/runsync` does not stream.** With `return_aggregate_stream` it returns the full list of chunks once the generator is done, and so does the final `/status`.
- Right after the env change one job still landed on an old, non-streaming worker and came back as a plain result. Wait for the workers to roll over before measuring.

---

## 한국어

**목표:** 제너레이터 핸들러의 출력을 `/stream` 으로 받으며, 각 청크가 워커에서 만들어진 시각과 클라이언트에 도착한 시각을 잰다 — 모든 LLM 엔드포인트의 첫 토큰 시간 문제다.

**시간:** 약 15분 · **비용:** CPU 엔드포인트에서 1센트 미만 (2026-11-07)

### 파일

| 파일 | 역할 |
|---|---|
| `stream.py` | `/run` 으로 제출하고, 끝날 때까지 `/stream/<id>` 를 호출하며 청크마다 도착 시각을 기록; 마지막에 같은 입력으로 `/runsync` 한 번 |
| `results/stream_20x0.5.json` | 0.5초마다 하나씩 20개 청크 (5회) |
| `results/stream_200x0.02.json` | 토큰처럼 20 ms 마다 하나씩 200개 청크 (3회) |

워커: [`../06-autoscaling`](../06-autoscaling) 의 프로브에 템플릿 env `HANDLER_KIND=stream` 을 주면 `return_aggregate_stream: True` 인 async 제너레이터로 시작한다. 각 청크에 핸들러 시작 후 경과 초 `t` 가 들어 있다.

```bash
python3 stream.py <endpoint_id> --chunks 200 --every 0.02 --runs 3 --out results/stream_200x0.02.json
```

### 결과 (2026-11-07, CPU 2 vCPU)

| | 청크 20개 × 0.5초 | 청크 200개 × 20 ms |
|---|---|---|
| 첫 청크 도착, 워커가 떠 있을 때 | 1.6–1.7초 (`delayTime` 0.8초 + 만드는 데 0.5초 + 약 0.35초) | 0.95초 |
| 첫 청크, 워커가 뜨는 중일 때 | 4.5초 | 3.9–6.4초 |
| 청크 생성 → 수신 | 중앙값 0.31–0.37초 | 중앙값 0.51–0.55초, 최대 1.7초 |
| `/stream` 호출당 청크 수 | 1 | 4–5, 한 번은 20 |
| 청크를 만드는 데 든 핸들러 시간 | 10초 대기에 11.1초 | **4초 대기에 13.0–13.4초** |
| 같은 입력의 `/runsync` | 12.2초 뒤 한꺼번에 | 14.9초 뒤 한꺼번에 |

- **`/stream` 은 롱 폴링이다.** 호출마다 새 청크를 기다렸다가 생기는 대로 돌아왔다 — 0.5초 간격이면 한 번에 하나, 20 ms 간격이면 네다섯 개. 호출 사이에 sleep 할 필요가 없다.
- **청크는 만들어진 뒤 0.3–0.5초쯤 지나 클라이언트에 닿았다.** 채팅 UI 에는 충분하지만, `delayTime` 위에 첫 토큰 시간의 바닥을 깐다.
- **`yield` 한 번에 핸들러가 약 45–55 ms 를 썼다.** 20 ms 청크 200개가 4초가 아니라 13초 걸렸다 — yield 할 때마다 제너레이터가 멈춰 있었다. 초당 50 토큰을 만드는 모델이 토큰마다 yield 하면 초당 15 토큰 아래로 묶인다. **토큰을 묶어서 yield 하자.**
- **`/runsync` 는 스트리밍하지 않는다.** `return_aggregate_stream` 이면 제너레이터가 끝난 뒤 청크 전체 목록을 한꺼번에 돌려주고, 최종 `/status` 도 같다.
- env 를 바꾼 직후 작업 하나가 아직 스트리밍이 아닌 예전 워커에 가서 일반 결과로 돌아왔다. 측정 전에 워커가 모두 바뀔 때까지 기다린다.
