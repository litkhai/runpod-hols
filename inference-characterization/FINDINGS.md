# Inference Characterization — Findings

[English](#english) | [한국어](#한국어)

---

## English

Run on 2026-10-06 and 2026-10-07 (KST) against a real Runpod account; C22–C27 come from 2026-10-07. Every claim has an ID, an evidence grade and a way to re-check it from the files in [`lab/results/`](./lab/results). Grades: **measured** (run in this lab), **vendor doc** (link and date read), **observed once** (seen in one run, cause not established).

### Scope and spend

| Item | Value |
|---|---|
| Model and engine | `Qwen/Qwen2.5-7B-Instruct`, vLLM 0.31.0 on Pods; `runpod/worker-v1-vllm:v2.28.0` (vLLM 0.30.0) on Serverless |
| Pods | Secure Cloud: RTX 4090 (twice, on different hosts), H100 SXM, H100 PCIe, H100 NVL, H200, A100 SXM 80GB, A100 80GB PCIe, L40, L4. Community Cloud: RTX 4090, functional check only |
| Serverless | RTX 4090, workers 0–1, idle timeout 5 s, FlashBoot on and off |
| Spend | The account balance fell by USD 16.34 over the night: the lab's ledger, wall time × rate, gives USD 15.79 for Pods ([`runs.json`](./lab/results/runs.json), [`ledger.json`](./lab/results/ledger.json)) plus USD 0.37 for Serverless and USD 0.18 unassigned. The billing API snapshot ([`billing.json`](./lab/results/billing.json), Pods USD 14.47) was read 42 s after the last Pod stopped and under-posts the last three Pods (H100 PCIe 28.6 billed vs 46.9 wall minutes, A100 80GB PCIe 41.8 vs 46.3, L4 41.7 vs 103.1: USD 1.48), and its `pods` list holds the three Serverless worker ids (USD 0.09). The morning tests of 2026-10-07 (C22–C25) cost USD 0.28 by balance |
| Hourly prices | The API's `costPerHr` at creation ([`prices.json`](./lab/results/prices.json)); the console showed USD 0.01 more on each of the seven Pods visible at the time |

### Claims

| ID | Claim | Grade | Evidence and how to re-check |
|---|---|---|---|
| C1 | The same image and sweep completed on nine Secure GPU types: 14 result files each, 27,900 requests, all completed except one on L40 (`chat`, 1 req/s, `ServerDisconnectedError`) | measured | `lab/results/<GPU>/*_rate*.json`, fields `completed` and `failed` |
| C2 | Around 22:40 KST four of the seven planned types (H100 PCIe, A100 80GB PCIe, L40S, L4) showed no one-GPU Secure stock with a CUDA 13 driver floor (output not saved), so A100 SXM 80GB, H100 NVL and L40 were used. Three of the four ran later: A100 80GB PCIe and L4 were created on the first try at 00:36; H100 PCIe showed `Low` at 00:32 yet failed 13 creates before one succeeded at 00:49. L40 had needed 10 retries at 23:13; RTX 4090 failed once with "There are no instances currently available" | measured | [`runs.json`](./lab/results/runs.json) (`capacity_retries_before_create`, `no_capacity_first_kst`, `no_capacity_last_kst`, `created_at`), [`stock_snapshot.json`](./lab/results/stock_snapshot.json) |
| C3 | Inside every Secure Pod, the lab captured GPU UUID, PCIe generation and width, GPU topology, CPU model, driver and CUDA version, datacenter and Pod host name | measured | `lab/results/<GPU>/host.json` |
| C4 | Host facts differ within one GPU type and between types (table below) | measured | `host.json` per label |
| C5 | Throttle reasons, power and SM clock were sampled every second on every Secure Pod. The only active reason was `sw_power_cap`; no thermal throttling appeared | measured | `lab/results/<GPU>/*.gpu.csv` |
| C6 | vLLM's preemption counter (`vllm:num_preemptions_total`) was readable on every Pod. It rose only on the three GPUs with the smallest KV caches: RTX 4090 (`chat` 16 req/s: 61 and 64 on the two hosts; `rag` from 2 req/s; `summarize` from 1 req/s), L4 (from `chat` 4 req/s and in every `rag` and `summarize` run) and L40 (one each in `rag` 2–8 req/s) | measured | `*.metrics_before.txt` and `*.metrics_after.txt`; `preempt` column in [`PROFILE.md`](./lab/results/PROFILE.md) |
| C7 | A Community Cloud RTX 4090 Pod was created with `supportPublicIp: true` but had no public IP or port-22 mapping within 15 minutes, so C3 and C5 could not be tested on Community Cloud | observed once | `runs.json` (`RTX_4090_community`, status `no-ssh`) |
| C8 | Runpod's documentation states that Community Cloud no longer accepts new hosts | vendor doc | [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod.md), read 2026-10-06 |
| C9 | A Serverless job returns `delayTime`, `executionTime` and `workerId`. Cold requests waited 150–383 s with FlashBoot on (two runs of three) and 181–276 s with it off, while execution stayed at 0.5–0.7 s; warm requests waited 83–94 ms | measured | [`coldstart_flashboot_on_run1.json`](./lab/results/coldstart_flashboot_on_run1.json), [`coldstart.json`](./lab/results/coldstart.json) (FlashBoot on, with logs), [`coldstart_flashboot_off.json`](./lab/results/coldstart_flashboot_off.json) |
| C10 | The same `workerId` answered both cold and warm requests, so the job response alone does not tell a cold start from a warm one | measured | same files, `workerId` per row |
| C11 | `GET /v2/serverless/{id}/workers` maps a worker id to `gpuTypeId`, `dataCenterId` and `startedAt`; the v1 worker objects carried `machineId` but an empty `machine` and a null `gpu` | measured | `lab/results/coldstart_logs/*/workers_*.json` |
| C12 | `GET /v2/serverless/{id}/workers/{workerId}/logs` returns timestamped system and container lines from which a cold start can be split into phases (table below) | measured | `lab/results/coldstart_logs/`, [`coldstart_phases.py`](./lab/coldstart_phases.py) |
| C13 | Container lines disappear from that endpoint once the container is removed: a capture during worker `gen3hjitlrbrcg`'s first container held 230 container lines; captures after that container was removed held none of them, only system lines and the next container's lines. They have to be captured during the cold start. Runpod's documentation describes worker logs as "not persistent" and "removed when a worker terminates", and endpoint logs as retained for 90 days | measured, vendor doc | `coldstart_logs/flashboot_off/gen3hjitlrbrcg.early.jsonl` vs `gen3hjitlrbrcg.jsonl`; [Serverless logs](https://docs.runpod.io/serverless/development/logs.md), read 2026-10-07 |
| C14 | Before the serving container was created, the platform had started other workers for the same job; one spent 197 s loading the image from the host cache | measured | `image_loads_from_cache` in the phases output |
| C15 | No public documentation describes a GPU availability notification or a way to wait for one specific type. Fallback across types exists: `gpuTypeIds` with `gpuTypePriority` on Pod creation, and up to three GPU types in priority order on a Serverless endpoint. `stockStatus`, `runpodctl gpu`, savings plans and Pod migration (beta) also exist | vendor doc | docs.runpod.io index, [Endpoint settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations.md), [Pricing](https://docs.runpod.io/pods/pricing.md), [Pod migration](https://docs.runpod.io/pods/troubleshooting/pod-migration.md), REST v1 OpenAPI `PodCreateInput`, read 2026-10-07; [`evidence/excerpts.md`](./evidence/excerpts.md) |
| C16 | Among the platforms reviewed, Modal also combines a wide per-second GPU menu with functions and sandboxes from one image; fal documents per-state cold-start timing | vendor doc | [`RESEARCH.md`](./RESEARCH.md) |
| C17 | With FlashBoot on, three cold starts on the same worker spent 56, 13 and 47 s before a container existed; with it off, 62 and 70 s. Every logged cold start, on or off, created a new container, restarted vLLM from scratch and downloaded the weights again (14.19 GiB on an `OVERLAY` filesystem) | measured | [`coldstart_flashboot_on_phases.json`](./lab/results/coldstart_flashboot_on_phases.json), [`coldstart_flashboot_off_phases.json`](./lab/results/coldstart_flashboot_off_phases.json); system lines `create container` / `remove container` |
| C18 | Between the system line "worker is ready" and "create container", up to 56 s passed with nothing logged | measured | `coldstart_logs/flashboot_on/woylujqk91186x.jsonl` (15:37:13 → 15:38:09 UTC) |
| C19 | CUDA graph capture (two passes per start, summed) took 9 s on the FlashBoot-on worker's host and 62–73 s on the FlashBoot-off hosts, for the same image and model. The fitness-check lines show three different machines (host RAM 503.55, 755.70 and 503.49 GB; matrix-multiply check 61–71 ms vs 124 and 96 ms) | measured; see C23 for a second reading | `graph_capture_s` in the two phases files |
| C21 | The sweep used vLLM's `random` dataset with one fixed seed, so every rate of a use case sent the same prompts, and `chat` and `summarize` prompts are prefixes of the `rag` prompts. vLLM ran with prefix caching on. On the GPUs whose KV cache holds over a million tokens (A100, H100, H200), 97–100% of prompt tokens were served from the prefix cache in every run after the first of each use case; on RTX 4090 and L4 (73k–97k tokens) the share was 0–6%; L40 (448k) was mixed. Latency and throughput on the large-KV GPUs after their first runs therefore measured little prefill work, and are not comparable with RTX 4090 and L4. `run_sweep.sh` now gives each run its own seed; that change has not been re-run | measured | `prefix hit` column in [`PROFILE.md`](./lab/results/PROFILE.md) (from `vllm:prefix_cache_hits_total` and `vllm:prefix_cache_queries_total`), `enable_prefix_caching=True` and "GPU KV cache size" in each `vllm.log` |
| C20 | In nine stock readings (00:32, then every 10 minutes from 00:50 to 02:00 KST), nine of the thirteen tracked types changed status at least once — between `Low` and none, or `Low` and `Medium`. A100 SXM 80GB and H200 stayed `Low`; A100 SXM 40GB and H200 NVL never showed stock. With and without the CUDA 13 floor the status matched in all but five type-readings | measured | [`stock_snapshots.jsonl`](./lab/results/stock_snapshots.jsonl), [`stock_snapshot.json`](./lab/results/stock_snapshot.json), [`stock_snapshots.sh`](./lab/stock_snapshots.sh) |
| C22 | With FlashBoot on and a 5 s idle timeout, the container that served a request also served the requests sent 15 s and 30 s after the previous one (`delayTime` 1.9 and 1.3 s) and was stopped 23 s after the last of them. From a 60 s gap on, every request got a new container (97–104 s). "Before a container existed" was 43 s on the first start and 1–4 s afterwards, when spare workers that had logged `worker is ready` 11–18 min earlier were used | measured | [`coldstart_gaps.json`](./lab/results/coldstart_gaps.json), [`coldstart_gaps_phases.json`](./lab/results/coldstart_gaps_phases.json), `coldstart_logs/flashboot_on_gaps/`; `GAPS=15,30,60,120,300` in [`coldstart_probe.py`](./lab/coldstart_probe.py) |
| C23 | On one worker, the first container loaded the weights in 151.8 s and captured graphs in 135 s; the next container on the same worker took 1.9 s and 7 s, and two other workers in other datacenters started in 90–94 s with 9 s of graph capture. C19's 9 s against 62–73 s therefore has a second reading — a host's first start of this image against a repeat — that the data cannot separate from host hardware | measured, cause not established | same files, `weights_load_s` and `graph_capture_s`; `Loading weights took` lines in `g17xiqon7kw30a.jsonl` |
| C24 | Five requests sent at once to an endpoint with `workersMax` 3 were all served by the one container that came up, with the same `delayTime` to within 0.1 s (152.2–152.3 s); five more sent at once afterwards took 96–190 ms on the same worker. Meanwhile the worker list held five workers, and one of them created a container 5 s after the first engine was ready and served nothing | observed once | [`concurrent.json`](./lab/results/concurrent.json), `coldstart_logs/concurrent_w3/`, [`concurrent_probe.py`](./lab/concurrent_probe.py) |
| C25 | In 20 create attempts over ten minutes, a type whose `stockStatus` read `Low` was created 9 times in 10 (2.1–2.6 s each; the failure was B200), and a type with no stock reading failed 10 times in 10 with "There are no instances currently available". Each Pod was deleted within 3 s | measured | [`stock_create_probe.jsonl`](./lab/results/stock_create_probe.jsonl), [`stock_create_probe.py`](./lab/stock_create_probe.py) |
| C26 | `delayTime` and `executionTime` are milliseconds: on all 18 requests of C9, wall time minus their sum is +0.45 to +2.07 s, the client's submit and 0.5 s status polling | measured | the three C9 files, `wall_s` against `delayTime_ms` + `executionTime_ms` |
| C27 | Over one day (77 readings, 08:15–20:56 KST on 2026-10-07, every 10 min), 10 of the 13 tracked types changed status at least once. H100 PCIe showed no one-GPU Secure stock in 43 of 77 readings (56%) and changed 22 times; L40 changed 22 times, A100 80GB PCIe 19, B200 17. A100 SXM 40GB and H200 NVL never showed stock; H200 read `Low` all day; RTX 4090 read `High` in 47 readings after reading `Low` the night before. With and without the CUDA 13 floor the status differed in 78 of 1,001 type-readings (8%) | measured | [`stock_snapshots_run2.jsonl`](./lab/results/stock_snapshots_run2.jsonl), [`stock_snapshots.sh`](./lab/stock_snapshots.sh) |

### Host facts

| Label | Datacenter | PCIe gen (current/max) | PCIe width (current/max) | CPU | Driver | Power limit (W) |
|---|---|---|---|---|---|---|
| RTX_4090 | EUR-IS-2 | gen4/4 | x16/16 | AMD EPYC 7532 | 580.159.04 | 450 |
| RTX_4090_repeat | EU-RO-1 | gen4/4 | x8/16 | AMD Ryzen 9 7950X | 580.159.04 | 450 |
| H100_SXM | AP-IN-1 | gen5/5 | x16/16 | Intel Xeon Platinum 8480+ | 580.126.09 | 700 |
| H100_NVL | US-KS-2 | gen5/5 | x16/16 | Intel Xeon Platinum 8452Y | 580.159.04 | 310 |
| H100_PCIe | US-KS-2 | gen4/4 | x16/16 | Intel Xeon Platinum 8352Y | 580.142 | 310 |
| H200 | US-CO-1 | gen5/5 | x16/16 | Intel Xeon Platinum 8562Y+ | 580.178.04 | 700 |
| A100_SXM_80GB | US-KS-2 | gen4/4 | x16/16 | AMD EPYC 7742 | 580.159.04 | 400 |
| A100_80GB_PCIe | CA-MTL-3 | gen4/4 | x16/16 | AMD EPYC 7763 | 580.159.04 | 300 |
| L40 | US-KS-2 | gen4/4 | x16/16 | AMD EPYC 7773X | 580.178.04 | 300 |
| L4 | EU-RO-1 | gen4/4 | x8/16 | AMD EPYC 9254 | 580.159.04 | 72 |

Captured once per Pod, before the sweep, with the GPU idle. `max` is what `nvidia-smi` reports as possible for this GPU and system configuration; a current width below the maximum, as on `RTX_4090_repeat` and `L4` (both in EU-RO-1), may be a slot limit or a link that narrowed at idle — one reading cannot tell.

NVIDIA lists 400 W as the H100 NVL default when its power cable is strapped for 450 or 600 W, and 310 W when strapped for 300 W ([PB-11773-001_v01](https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/h100/PB-11773-001_v01.pdf), Table 1, read 2026-10-07). Which case applies to this host cannot be seen from inside the Pod. `sw_power_cap` was active in 80% of its samples.

### Cold start, phase by phase

From the worker logs (C12). Seconds. Produced by `python3 lab/coldstart_phases.py <probe.json> <log_dir>`.

| Run | Probe | delayTime | Before a container existed | Container start | vLLM start to engine ready | of which: weights download | compile | graph capture | Worker boot and checks | Pickup |
|---|---|---|---|---|---|---|---|---|---|---|
| FlashBoot off | 0 | 258.2 | 62.1 | 6.4 | 178.3 | 15.0 | 17.6 | 73.0 | 10.6 | 0.8 |
| FlashBoot off | 1 | 276.3 | 70.3 | 10.8 | 186.1 | 46.7 | 14.6 | 62.0 | 8.4 | 0.6 |
| FlashBoot off | 2 | 181.5 | - | 3.1 | - | 25.4 | 18.6 | - | - | - |
| FlashBoot on | 0 | 227.6 | 56.3 | 4.6 | 160.3 | 55.9 | 19.3 | 9.0 | 5.6 | 0.7 |
| FlashBoot on | 1 | 150.3 | 13.2 | 2.2 | 129.3 | 32.0 | 17.5 | 9.0 | 4.9 | 0.6 |
| FlashBoot on | 2 | 181.2 | 46.5 | 2.0 | 127.6 | 26.9 | 17.3 | 9.0 | 4.5 | 0.6 |

"Before a container existed" is `delayTime` minus the logged time from container creation to job pickup: queueing, host selection, attempts on other workers and image load. The engine phase is set by the model and engine configuration; the phases before it are set by the platform. FlashBoot-off probe 2 was captured only up to model loading: the endpoint was deleted before the next log poll. The first FlashBoot-on run ([`coldstart_flashboot_on_run1.json`](./lab/results/coldstart_flashboot_on_run1.json)) has no logs.

Idle-gap run of 2026-10-07 (C22, C23), FlashBoot on, same endpoint settings, gap = idle seconds before the request:

| Gap | delayTime | Container | Before a container existed | vLLM start to engine ready | of which: weights download | weights load | compile | graph capture | Worker boot and checks | Pickup |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 439.6 | new | 43.2 | 379.1 | 13.8 | 151.8 | 15.7 | 135.0 | 13.0 | 0.6 |
| 15 | 1.9 | reused | - | - | - | - | - | - | - | - |
| 30 | 1.3 | reused | - | - | - | - | - | - | - | - |
| 60 | 102.4 | new, same worker | 4.3 | 90.2 | 15.1 | 1.9 | 13.7 | 7.0 | 5.0 | 0.6 |
| 120 | 96.8 | new, other worker | 1.1 | 89.6 | 9.6 | 1.8 | 14.8 | 9.0 | 4.1 | 0.3 |
| 300 | 104.3 | new, other worker | 3.7 | 93.7 | 15.2 | 2.1 | 14.1 | 9.0 | 3.8 | 0.4 |

"reused": the container that served the previous request was still running (no `create container` between the request and its pickup); the parser marks such rows "no cold start".

### Reference data

Not used as pass/fail criteria. Full table: [`PROFILE.md`](./lab/results/PROFILE.md).

- RTX 4090 stopped meeting the SLO at `chat` 16 req/s and `rag` 2 req/s. L4 met it at no swept rate (`chat` 1 req/s TPOT p99 81 ms against a 50 ms SLO), with `sw_power_cap` active in 97% of samples at a 72 W limit. RTX 4090 `summarize` failed from 1 req/s; L40 met `chat` up to 8 req/s and failed `rag` above 0.5 req/s on TPOT. The H100 and A100 types met the SLO at every swept rate — but almost entirely from the prefix cache after their first runs (C21), so neither their limit nor their cost at SLO is established.
- The two RTX 4090 hosts (PCIe width x16, and x8 of a possible x16 at idle) gave near-identical percentiles, e.g. `chat` 1 req/s TTFT p99 128 and 123 ms, `chat` 8 req/s 314 and 319 ms.

### What the lab had to work around

| Symptom | Cause | Fix in the lab |
|---|---|---|
| HTTP 403, `error code: 1010` from `rest.runpod.io` | Cloudflare rejects the default `Python-urllib` User-Agent | Send an explicit User-Agent |
| `pip install vllm` fails on `runpod/pytorch` | System Python has a Debian-owned PyJWT that pip cannot uninstall | Install into a venv made by the standalone `uv` installer |
| vLLM 0.31.0 needs a CUDA 13 driver | It pins `torch==2.13.0` with `cu13` dependencies | `allowedCudaVersions: ["13.0"]` on the Pod, `minCudaVersion: "13.0"` on the endpoint |
| `RUNPOD_*` variables missing over SSH | They are set on the container's PID 1 only | Read `/proc/1/environ` |
| Throttle columns named `clocks_event_reasons.*`, clock column `clocks.current.sm` | Renamed in driver 580 | Detect the field names at run time |

### Not established

- Whether the host differences in C4 change throughput or latency. One host per GPU type was measured, two for RTX 4090; those two ran the same prompt schedule, and paired per-request end-to-end latency was about 1% higher on the repeat host at `chat` 8 and 16 req/s, a difference the pairing resolves but cannot attribute.
- Performance on the large-KV GPUs without prefix-cache reuse (C21).
- C3, C5 and C6 on Community Cloud (C7).
- Why individual cold starts differ, beyond the phases in C12 and C22.
- Whether the slow first start in C23 is the host's first use of the image or the host itself; and whether the multi-worker case in C24 can hide a cold start behind a warm `delayTime`, since the second container never served a job.

---

## 한국어

2026-10-06~07(KST)에 실제 Runpod 계정에서 실행했다. C22–C27은 2026-10-07에 추가로 실행한 것이다. 모든 주장에는 ID, 근거 등급, [`lab/results/`](./lab/results)의 파일로 다시 확인하는 방법이 붙어 있다. 등급: **실측**(이 lab에서 실행), **공급사 문서**(링크와 확인일), **1회 관측**(한 번 보았고 원인은 확인하지 않음).

### 범위와 비용

| 항목 | 값 |
|---|---|
| 모델과 엔진 | `Qwen/Qwen2.5-7B-Instruct`, Pod에서는 vLLM 0.31.0, Serverless에서는 `runpod/worker-v1-vllm:v2.28.0`(vLLM 0.30.0) |
| Pod | Secure Cloud: RTX 4090(서로 다른 호스트에서 두 번), H100 SXM, H100 PCIe, H100 NVL, H200, A100 SXM 80GB, A100 80GB PCIe, L40, L4. Community Cloud: RTX 4090, 기능 점검만 |
| Serverless | RTX 4090, 워커 0–1, 유휴 타임아웃 5초, FlashBoot 켬과 끔 |
| 비용 | 하룻밤 사이 계정 잔액이 USD 16.34 줄었다. lab 장부(벽시계 시간 × 요금)로 Pod USD 15.79 ([`runs.json`](./lab/results/runs.json), [`ledger.json`](./lab/results/ledger.json)), Serverless USD 0.37, 미배정 USD 0.18이다. 청구 API 스냅샷([`billing.json`](./lab/results/billing.json), Pod USD 14.47)은 마지막 Pod가 멈춘 42초 뒤에 읽어 마지막 Pod 3개가 덜 반영됐고(H100 PCIe 청구 28.6분 대 벽시계 46.9분, A100 80GB PCIe 41.8 대 46.3, L4 41.7 대 103.1: USD 1.48), `pods` 목록에 Serverless 워커 id 세 개(USD 0.09)가 들어 있다. 2026-10-07 아침 테스트(C22–C25)는 잔액 기준 USD 0.28이 들었다 |
| 시간당 가격 | 생성 시 API의 `costPerHr` ([`prices.json`](./lab/results/prices.json)). 그때 보이던 Pod 7개 모두 콘솔에는 USD 0.01 높게 표시됐다 |

### 주장

| ID | 주장 | 등급 | 근거와 재확인 방법 |
|---|---|---|---|
| C1 | 같은 이미지와 스윕이 Secure GPU 9종에서 끝까지 돌았다. 종류마다 결과 파일 14개, 요청 27,900건 가운데 L40의 1건(`chat` 1 req/s, `ServerDisconnectedError`)을 빼고 모두 완료됐다 | 실측 | `lab/results/<GPU>/*_rate*.json`의 `completed`, `failed` |
| C2 | 22:40 KST 무렵 계획한 7종 가운데 4종(H100 PCIe, A100 80GB PCIe, L40S, L4)은 CUDA 13 드라이버 조건의 1장짜리 Secure 재고가 없어(조회 결과는 저장하지 않음) A100 SXM 80GB, H100 NVL, L40을 대신 썼다. 그 4종 가운데 3종은 나중에 돌았다. A100 80GB PCIe와 L4는 00:36에 첫 시도로 생성됐고, H100 PCIe는 00:32에 `Low`였는데도 13번 실패한 뒤 00:49에 생성됐다. L40은 23:13에 재시도 10번이 필요했고, RTX 4090은 한 번 "There are no instances currently available"로 실패했다 | 실측 | [`runs.json`](./lab/results/runs.json)(`capacity_retries_before_create`, `no_capacity_first_kst`, `no_capacity_last_kst`, `created_at`), [`stock_snapshot.json`](./lab/results/stock_snapshot.json) |
| C3 | 모든 Secure Pod 안에서 GPU UUID, PCIe 세대와 폭, GPU 토폴로지, CPU 모델, 드라이버와 CUDA 버전, 데이터센터, Pod 호스트명을 수집했다 | 실측 | `lab/results/<GPU>/host.json` |
| C4 | 호스트 정보는 같은 GPU 종류 안에서도, 종류 사이에서도 다르다(아래 표) | 실측 | 라벨별 `host.json` |
| C5 | 모든 Secure Pod에서 스로틀 사유, 전력, SM 클럭을 1초 단위로 샘플링했다. 활성화된 사유는 `sw_power_cap`뿐이었고 열 스로틀은 없었다 | 실측 | `lab/results/<GPU>/*.gpu.csv` |
| C6 | vLLM 선점 카운터(`vllm:num_preemptions_total`)는 모든 Pod에서 읽혔다. 증가한 것은 KV 캐시가 가장 작은 세 GPU뿐이었다: RTX 4090(`chat` 16 req/s에서 두 호스트 각각 61과 64, `rag` 2 req/s부터, `summarize` 1 req/s부터), L4(`chat` 4 req/s부터, 그리고 모든 `rag`와 `summarize` 실행), L40(`rag` 2–8 req/s에서 각 1회) | 실측 | `*.metrics_before.txt`, `*.metrics_after.txt`, [`PROFILE.md`](./lab/results/PROFILE.md)의 `preempt` 열 |
| C7 | Community Cloud RTX 4090 Pod는 `supportPublicIp: true`로 생성됐지만 15분 안에 공인 IP와 22번 포트 매핑이 생기지 않아, C3과 C5를 Community Cloud에서 검증하지 못했다 | 1회 관측 | `runs.json`(`RTX_4090_community`, 상태 `no-ssh`) |
| C8 | Runpod 문서는 Community Cloud가 더 이상 새 호스트를 받지 않는다고 적고 있다 | 공급사 문서 | [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod.md), 2026-10-06 확인 |
| C9 | Serverless 작업은 `delayTime`, `executionTime`, `workerId`를 돌려준다. 콜드 요청 대기는 FlashBoot 켬에서 150–383초(두 번의 실행, 각 3회), 끔에서 181–276초였고, 실행은 0.5–0.7초로 일정했다. 웜 요청 대기는 83–94 ms였다 | 실측 | [`coldstart_flashboot_on_run1.json`](./lab/results/coldstart_flashboot_on_run1.json), [`coldstart.json`](./lab/results/coldstart.json)(FlashBoot 켬, 로그 포함), [`coldstart_flashboot_off.json`](./lab/results/coldstart_flashboot_off.json) |
| C10 | 콜드와 웜 요청에 같은 `workerId`가 돌아와, 작업 응답만으로는 콜드스타트와 웜을 구분할 수 없다 | 실측 | 같은 파일의 행별 `workerId` |
| C11 | `GET /v2/serverless/{id}/workers`는 워커 id를 `gpuTypeId`, `dataCenterId`, `startedAt`에 대응시킨다. v1 워커 객체에는 `machineId`가 있었지만 `machine`은 비어 있고 `gpu`는 null이었다 | 실측 | `lab/results/coldstart_logs/*/workers_*.json` |
| C12 | `GET /v2/serverless/{id}/workers/{workerId}/logs`는 타임스탬프가 붙은 시스템과 컨테이너 로그를 돌려주며, 이것으로 콜드스타트를 단계별로 나눌 수 있다(아래 표) | 실측 | `lab/results/coldstart_logs/`, [`coldstart_phases.py`](./lab/coldstart_phases.py) |
| C13 | 컨테이너가 제거되면 컨테이너 로그가 그 API에서 사라진다. 워커 `gen3hjitlrbrcg`의 첫 컨테이너가 살아 있을 때 받은 로그에는 컨테이너 로그가 230줄 있었고, 그 컨테이너가 제거된 뒤 받은 로그에는 그 줄이 하나도 없이 시스템 로그와 다음 컨테이너의 로그만 있었다. 그래서 콜드스타트 도중에 수집해야 한다. Runpod 문서도 워커 로그를 "not persistent", "removed when a worker terminates"로, 엔드포인트 로그는 90일 보관으로 설명한다 | 실측, 공급사 문서 | `coldstart_logs/flashboot_off/gen3hjitlrbrcg.early.jsonl`과 `gen3hjitlrbrcg.jsonl` 비교, [Serverless logs](https://docs.runpod.io/serverless/development/logs.md), 2026-10-07 확인 |
| C14 | 작업을 처리한 컨테이너가 생성되기 전에 플랫폼은 같은 작업을 위해 다른 워커들을 띄웠고, 그중 하나는 호스트 캐시에서 이미지를 읽는 데 197초를 썼다 | 실측 | 단계 분석 출력의 `image_loads_from_cache` |
| C15 | GPU 재고 알림이나 특정 종류 하나를 기다리는 기능을 설명하는 공개 문서는 없다. 종류 간 대체는 있다: Pod 생성의 `gpuTypeIds`와 `gpuTypePriority`, Serverless 엔드포인트의 우선순위 GPU 최대 3종. `stockStatus`, `runpodctl gpu`, savings plan, Pod migration(베타)도 있다 | 공급사 문서 | docs.runpod.io 색인, [Endpoint settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations.md), [Pricing](https://docs.runpod.io/pods/pricing.md), [Pod migration](https://docs.runpod.io/pods/troubleshooting/pod-migration.md), REST v1 OpenAPI `PodCreateInput`, 2026-10-07 확인, [`evidence/excerpts.md`](./evidence/excerpts.md) |
| C16 | 조사한 플랫폼 가운데 Modal도 초 단위 과금의 넓은 GPU 메뉴와 한 이미지로 쓰는 함수·샌드박스를 함께 갖고 있고, fal은 상태별 콜드스타트 시간을 문서화한다 | 공급사 문서 | [`RESEARCH.md`](./RESEARCH.md) |
| C17 | FlashBoot 켬에서 같은 워커의 콜드스타트 세 번은 컨테이너가 생기기 전까지 56, 13, 47초를 썼고, 끔에서는 62, 70초였다. 로그가 있는 콜드스타트는 켬과 끔 모두 매번 새 컨테이너를 만들고 vLLM을 처음부터 다시 띄우고 가중치를 다시 받았다(14.19 GiB, `OVERLAY` 파일시스템) | 실측 | [`coldstart_flashboot_on_phases.json`](./lab/results/coldstart_flashboot_on_phases.json), [`coldstart_flashboot_off_phases.json`](./lab/results/coldstart_flashboot_off_phases.json), 시스템 로그 `create container` / `remove container` |
| C18 | 시스템 로그의 "worker is ready"와 "create container" 사이에 기록 없이 최대 56초가 지났다 | 실측 | `coldstart_logs/flashboot_on/woylujqk91186x.jsonl`(15:37:13 → 15:38:09 UTC) |
| C19 | 같은 이미지와 모델에서 CUDA 그래프 캡처(시작마다 두 번, 합산)가 FlashBoot 켬 워커의 호스트에서는 9초, 끔 워커들의 호스트에서는 62–73초 걸렸다. 적합성 검사 로그로 보아 세 대의 서로 다른 머신이었다(호스트 RAM 503.55, 755.70, 503.49 GB, 행렬곱 점검 61–71 ms 대 124, 96 ms) | 실측, 다른 해석은 C23 | 두 단계 분석 파일의 `graph_capture_s` |
| C21 | 스윕은 vLLM의 `random` 데이터셋을 고정 시드 하나로 썼다. 그래서 한 유즈케이스의 모든 요청률이 같은 프롬프트를 보냈고, `chat`과 `summarize` 프롬프트는 `rag` 프롬프트의 앞부분이다. vLLM은 프리픽스 캐싱이 켜진 상태였다. KV 캐시가 100만 토큰을 넘는 GPU(A100, H100, H200)에서는 유즈케이스별 첫 실행 이후 모든 실행에서 프롬프트 토큰의 97–100%를 프리픽스 캐시에서 처리했고, RTX 4090과 L4(7만 3천–9만 7천 토큰)에서는 0–6%, L40(44만 8천)은 섞여 있었다. 따라서 대형 KV GPU의 첫 실행 이후 지연과 처리량은 prefill을 거의 하지 않은 값이며 RTX 4090, L4와 비교할 수 없다. `run_sweep.sh`는 이제 실행마다 다른 시드를 쓰지만 이 변경으로 다시 돌리지는 않았다 | 실측 | [`PROFILE.md`](./lab/results/PROFILE.md)의 `prefix hit` 열(`vllm:prefix_cache_hits_total`, `vllm:prefix_cache_queries_total`에서 계산), 각 `vllm.log`의 `enable_prefix_caching=True`와 "GPU KV cache size" |
| C20 | 재고 조회 9회(00:32, 그리고 00:50부터 02:00까지 10분마다, KST)에서 추적한 13종 가운데 9종이 한 번 이상 상태가 바뀌었다(`Low`와 없음, 또는 `Low`와 `Medium` 사이). A100 SXM 80GB와 H200은 계속 `Low`, A100 SXM 40GB와 H200 NVL은 한 번도 재고가 없었다. CUDA 13 조건 유무에 따른 상태는 다섯 번을 빼고 모두 같았다 | 실측 | [`stock_snapshots.jsonl`](./lab/results/stock_snapshots.jsonl), [`stock_snapshot.json`](./lab/results/stock_snapshot.json), [`stock_snapshots.sh`](./lab/stock_snapshots.sh) |
| C22 | FlashBoot 켬, 유휴 타임아웃 5초에서 요청을 처리한 컨테이너가 직전 요청 15초·30초 뒤에 보낸 요청도 그대로 처리했고(`delayTime` 1.9초, 1.3초) 마지막 요청 23초 뒤에 멈췄다. 간격 60초부터는 매번 새 컨테이너였다(97–104초). "컨테이너 생성 전"은 첫 시작에서 43초, 그 뒤로는 1–4초였는데, 11–18분 전에 `worker is ready`를 남긴 예비 워커가 쓰였기 때문이다 | 실측 | [`coldstart_gaps.json`](./lab/results/coldstart_gaps.json), [`coldstart_gaps_phases.json`](./lab/results/coldstart_gaps_phases.json), `coldstart_logs/flashboot_on_gaps/`, [`coldstart_probe.py`](./lab/coldstart_probe.py)의 `GAPS=15,30,60,120,300` |
| C23 | 한 워커에서 첫 컨테이너는 가중치 로드 151.8초, 그래프 캡처 135초였고, 같은 워커의 다음 컨테이너는 1.9초와 7초였다. 다른 데이터센터의 워커 둘도 90–94초에 기동했고 그래프 캡처는 9초였다. 따라서 C19의 9초 대 62–73초에는 호스트 하드웨어 차이 말고도 "그 호스트에서 이 이미지의 첫 기동 대 재기동"이라는 해석이 가능하며, 데이터로는 둘을 가를 수 없다 | 실측, 원인 미확인 | 같은 파일의 `weights_load_s`, `graph_capture_s`, `g17xiqon7kw30a.jsonl`의 `Loading weights took` 줄 |
| C24 | `workersMax` 3인 엔드포인트에 동시에 보낸 요청 5건을 먼저 뜬 컨테이너 하나가 모두 처리했고 `delayTime`은 0.1초 안에서 같았다(152.2–152.3초). 이어서 동시에 보낸 5건은 같은 워커에서 96–190 ms였다. 그동안 워커 목록에는 워커 5개가 있었고, 그중 하나는 첫 엔진이 준비된 5초 뒤 컨테이너를 만들었지만 아무 작업도 처리하지 않았다 | 1회 관측 | [`concurrent.json`](./lab/results/concurrent.json), `coldstart_logs/concurrent_w3/`, [`concurrent_probe.py`](./lab/concurrent_probe.py) |
| C25 | 10분 동안 생성 20회를 시도해, `stockStatus`가 `Low`인 종류는 10번 중 9번 생성됐고(각 2.1–2.6초, 실패 1건은 B200), 재고 표시가 없는 종류는 10번 모두 "There are no instances currently available"로 실패했다. 생성된 Pod는 모두 3초 안에 삭제했다 | 실측 | [`stock_create_probe.jsonl`](./lab/results/stock_create_probe.jsonl), [`stock_create_probe.py`](./lab/stock_create_probe.py) |
| C26 | `delayTime`과 `executionTime`은 밀리초다. C9의 요청 18건 모두에서 벽시계 시간에서 둘의 합을 뺀 값이 +0.45~+2.07초로, 클라이언트의 제출과 0.5초 상태 폴링에 해당한다 | 실측 | C9의 세 파일, `wall_s`와 `delayTime_ms` + `executionTime_ms` |
| C27 | 하루 동안(2026-10-07 08:15–20:56 KST, 10분마다 77회) 추적한 13종 가운데 10종이 한 번 이상 상태가 바뀌었다. H100 PCIe는 77회 중 43회(56%)에서 1장짜리 Secure 재고가 없었고 22번 바뀌었다. L40 22번, A100 80GB PCIe 19번, B200 17번. A100 SXM 40GB와 H200 NVL은 한 번도 재고가 없었고, H200은 종일 `Low`, RTX 4090은 전날 밤 `Low`였다가 47회 `High`였다. CUDA 13 조건 유무에 따라 상태가 다른 경우는 1,001건 중 78건(8%) | 실측 | [`stock_snapshots_run2.jsonl`](./lab/results/stock_snapshots_run2.jsonl), [`stock_snapshots.sh`](./lab/stock_snapshots.sh) |

### 호스트 정보

| 라벨 | 데이터센터 | PCIe 세대 (현재/최대) | PCIe 폭 (현재/최대) | CPU | 드라이버 | 전력 상한 (W) |
|---|---|---|---|---|---|---|
| RTX_4090 | EUR-IS-2 | gen4/4 | x16/16 | AMD EPYC 7532 | 580.159.04 | 450 |
| RTX_4090_repeat | EU-RO-1 | gen4/4 | x8/16 | AMD Ryzen 9 7950X | 580.159.04 | 450 |
| H100_SXM | AP-IN-1 | gen5/5 | x16/16 | Intel Xeon Platinum 8480+ | 580.126.09 | 700 |
| H100_NVL | US-KS-2 | gen5/5 | x16/16 | Intel Xeon Platinum 8452Y | 580.159.04 | 310 |
| H100_PCIe | US-KS-2 | gen4/4 | x16/16 | Intel Xeon Platinum 8352Y | 580.142 | 310 |
| H200 | US-CO-1 | gen5/5 | x16/16 | Intel Xeon Platinum 8562Y+ | 580.178.04 | 700 |
| A100_SXM_80GB | US-KS-2 | gen4/4 | x16/16 | AMD EPYC 7742 | 580.159.04 | 400 |
| A100_80GB_PCIe | CA-MTL-3 | gen4/4 | x16/16 | AMD EPYC 7763 | 580.159.04 | 300 |
| L40 | US-KS-2 | gen4/4 | x16/16 | AMD EPYC 7773X | 580.178.04 | 300 |
| L4 | EU-RO-1 | gen4/4 | x8/16 | AMD EPYC 9254 | 580.159.04 | 72 |

Pod마다 스윕 전에 GPU가 쉬는 상태에서 한 번 수집했다. `최대`는 `nvidia-smi`가 이 GPU와 시스템 구성에서 가능하다고 보고한 값이다. `RTX_4090_repeat`과 `L4`(둘 다 EU-RO-1)처럼 현재 폭이 최대보다 작으면 슬롯 제한일 수도, 유휴 상태에서 링크가 좁아진 것일 수도 있으며, 한 번의 측정으로는 구분할 수 없다.

NVIDIA는 H100 NVL의 기본 전력을 전원 케이블이 450 또는 600 W로 설정된 경우 400 W, 300 W로 설정된 경우 310 W로 적고 있다([PB-11773-001_v01](https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/h100/PB-11773-001_v01.pdf), Table 1, 2026-10-07 확인). 이 호스트가 어느 경우인지는 Pod 안에서 알 수 없다. 샘플의 80%에서 `sw_power_cap`이 활성화돼 있었다.

### 콜드스타트 단계별 분해

워커 로그 기준(C12). 단위는 초. `python3 lab/coldstart_phases.py <probe.json> <log_dir>`로 만든다.

| 실행 | 프로브 | delayTime | 컨테이너 생성 전 | 컨테이너 시작 | vLLM 시작부터 엔진 준비까지 | 그중 가중치 다운로드 | 컴파일 | 그래프 캡처 | 워커 기동과 점검 | 작업 수령 |
|---|---|---|---|---|---|---|---|---|---|---|
| FlashBoot 끔 | 0 | 258.2 | 62.1 | 6.4 | 178.3 | 15.0 | 17.6 | 73.0 | 10.6 | 0.8 |
| FlashBoot 끔 | 1 | 276.3 | 70.3 | 10.8 | 186.1 | 46.7 | 14.6 | 62.0 | 8.4 | 0.6 |
| FlashBoot 끔 | 2 | 181.5 | - | 3.1 | - | 25.4 | 18.6 | - | - | - |
| FlashBoot 켬 | 0 | 227.6 | 56.3 | 4.6 | 160.3 | 55.9 | 19.3 | 9.0 | 5.6 | 0.7 |
| FlashBoot 켬 | 1 | 150.3 | 13.2 | 2.2 | 129.3 | 32.0 | 17.5 | 9.0 | 4.9 | 0.6 |
| FlashBoot 켬 | 2 | 181.2 | 46.5 | 2.0 | 127.6 | 26.9 | 17.3 | 9.0 | 4.5 | 0.6 |

"컨테이너 생성 전"은 `delayTime`에서 로그상 컨테이너 생성부터 작업 수령까지의 시간을 뺀 값이다. 대기, 호스트 선택, 다른 워커 시도, 이미지 로드가 여기에 들어간다. 엔진 구간은 모델과 엔진 설정이 정하고, 그 앞 구간은 플랫폼이 정한다. FlashBoot 끔 프로브 2는 모델 로딩까지만 수집됐다. 다음 로그 수집 전에 엔드포인트가 삭제됐기 때문이다. 첫 FlashBoot 켬 실행([`coldstart_flashboot_on_run1.json`](./lab/results/coldstart_flashboot_on_run1.json))에는 로그가 없다.

2026-10-07의 유휴 간격 실행(C22, C23). FlashBoot 켬, 같은 엔드포인트 설정, 간격 = 요청 전 유휴 초:

| 간격 | delayTime | 컨테이너 | 컨테이너 생성 전 | vLLM 시작부터 엔진 준비까지 | 그중 가중치 다운로드 | 가중치 로드 | 컴파일 | 그래프 캡처 | 워커 기동과 점검 | 작업 수령 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 439.6 | 새로 | 43.2 | 379.1 | 13.8 | 151.8 | 15.7 | 135.0 | 13.0 | 0.6 |
| 15 | 1.9 | 재사용 | - | - | - | - | - | - | - | - |
| 30 | 1.3 | 재사용 | - | - | - | - | - | - | - | - |
| 60 | 102.4 | 새로, 같은 워커 | 4.3 | 90.2 | 15.1 | 1.9 | 13.7 | 7.0 | 5.0 | 0.6 |
| 120 | 96.8 | 새로, 다른 워커 | 1.1 | 89.6 | 9.6 | 1.8 | 14.8 | 9.0 | 4.1 | 0.3 |
| 300 | 104.3 | 새로, 다른 워커 | 3.7 | 93.7 | 15.2 | 2.1 | 14.1 | 9.0 | 3.8 | 0.4 |

"재사용": 직전 요청을 처리한 컨테이너가 아직 돌고 있었다(요청과 수령 사이에 `create container`가 없음). 파서는 이런 행을 "콜드스타트 없음"으로 표시한다.

### 참고 데이터

판정 기준으로 쓰지 않는다. 전체 표는 [`PROFILE.md`](./lab/results/PROFILE.md)에 있다.

- RTX 4090은 `chat` 16 req/s, `rag` 2 req/s에서 SLO를 충족하지 못했다. L4는 어떤 요청률에서도 충족하지 못했고(`chat` 1 req/s TPOT p99 81 ms, SLO 50 ms), 72 W 상한에서 샘플의 97%가 `sw_power_cap`이었다. RTX 4090 `summarize`는 1 req/s부터 충족하지 못했고, L40은 `chat` 8 req/s까지 충족했지만 `rag`는 0.5 req/s를 넘으면 TPOT에서 충족하지 못했다. H100과 A100 계열은 모든 요청률에서 충족했지만 첫 실행 이후에는 거의 전부 프리픽스 캐시에서 처리됐으므로(C21), 한계도 SLO 기준 비용도 확인되지 않았다.
- RTX 4090 두 호스트(PCIe 폭 x16, 그리고 유휴 시 최대 x16 중 x8)의 백분위는 거의 같았다. 예: `chat` 1 req/s TTFT p99 128과 123 ms, `chat` 8 req/s 314와 319 ms.

### lab이 우회해야 했던 것

| 증상 | 원인 | lab의 조치 |
|---|---|---|
| `rest.runpod.io`에서 HTTP 403, `error code: 1010` | Cloudflare가 기본 `Python-urllib` User-Agent를 거부 | User-Agent를 명시 |
| `runpod/pytorch`에서 `pip install vllm` 실패 | 시스템 Python에 pip가 제거할 수 없는 Debian 소유 PyJWT가 있음 | 독립 실행형 `uv` 설치기로 만든 venv에 설치 |
| vLLM 0.31.0이 CUDA 13 드라이버를 요구 | `cu13` 의존성과 함께 `torch==2.13.0`을 고정 | Pod에 `allowedCudaVersions: ["13.0"]`, 엔드포인트에 `minCudaVersion: "13.0"` |
| SSH에서 `RUNPOD_*` 변수가 없음 | 컨테이너 PID 1에만 설정됨 | `/proc/1/environ`에서 읽음 |
| 스로틀 열 이름이 `clocks_event_reasons.*`, 클럭 열이 `clocks.current.sm` | 드라이버 580에서 이름이 바뀜 | 실행 시 필드 이름을 감지 |

### 확인하지 못한 것

- C4의 호스트 차이가 처리량이나 지연을 바꾸는지. GPU 종류마다 호스트 1곳(RTX 4090은 2곳)만 측정했다. 두 RTX 4090은 같은 프롬프트 일정으로 돌았고, 요청별로 짝지어 보면 `chat` 8과 16 req/s에서 반복 호스트의 종단 지연이 약 1% 높았다. 짝지은 비교로 구분되는 차이지만 원인은 알 수 없다.
- 프리픽스 캐시 재사용이 없을 때 대형 KV GPU의 성능(C21).
- Community Cloud에서의 C3, C5, C6(C7).
- C12와 C22의 단계 너머에서 개별 콜드스타트가 서로 다른 이유.
- C23의 느린 첫 기동이 그 호스트에서 이미지를 처음 쓴 탓인지 호스트 자체 탓인지. C24의 다중 워커 상황에서 콜드스타트가 웜 `delayTime` 뒤에 숨을 수 있는지 — 두 번째 컨테이너는 작업을 받지 못해 확인하지 못했다.
