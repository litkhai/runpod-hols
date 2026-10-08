# Inference Characterization — one model, many GPUs

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** run the same model image across several GPU types and hosts and record, per use case, what the engine and the hardware do to throughput, tail latency and cost — with the host facts attached.

**Status:** run end to end on 2026-10-06/07 (KST) against a real account. Verified on vLLM 0.31.0 (Pods) and `runpod/worker-v1-vllm:v2.28.0` (Serverless). Findings with evidence: [`FINDINGS.md`](./FINDINGS.md).

### Test scenario

Each hypothesis is a functional check: does the platform let this analysis be done, on which product and cloud type. Measured numbers (throughput, percentiles, cost per token) are recorded as data, not used as pass/fail criteria.

| ID | Hypothesis | Passes when |
|---|---|---|
| F1 | Host context can be captured on both Secure Cloud and Community Cloud Pods: GPU UUID, PCIe generation and width, GPU topology, CPU, driver and CUDA, datacenter, host name | `host.json` has every field filled, per cloud type |
| F2 | On both cloud types, throttle reasons, power and SM clock can be sampled every second, and vLLM's preemption counter can be read | `*.gpu.csv` and the `/metrics` snapshots are populated |
| F3 | The same image and sweep run end to end on every requested GPU type and produce per-use-case percentiles and goodput | One result JSON per use case and rate; GPU types that could not be obtained are recorded as a result |
| F4 | Serverless returns `delayTime`, `executionTime` and `workerId` for cold and warm requests, with no per-phase cold-start breakdown; whether `workerId` leads to a GPU or host | Fields present in the probe output |
| F5 | Which other GPU platforms document the same capabilities | Desk research in [`RESEARCH.md`](./RESEARCH.md) |

What transfers to other environments: engine- and GPU-type-level behaviour. What does not: load balancers, autoscalers, scheduling and network paths. The client runs on the same Pod as the server, so the network is deliberately out of the measurement.

### Fixed setup

| Item | Value | How it was confirmed |
|---|---|---|
| Model | `Qwen/Qwen2.5-7B-Instruct`, `--max-model-len 8192`, `--gpu-memory-utilization 0.90` | — |
| Engine | vLLM 0.31.0 (`pip install vllm==0.31.0` on the Pod) | PyPI, read 2026-10-06 |
| CUDA | Host driver must support CUDA 13: vLLM 0.31.0 pins `torch==2.13.0` with `cu13` dependencies | PyPI `requires_dist`, read 2026-10-06 |
| Image | `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404` (the image `pod/01-launch-connect` uses) | Docker Hub tag lookup |
| Pod | 1 GPU, 80 GB container disk, no volume, port `22/tcp`, `allowedCudaVersions: ["13.0"]` | Published OpenAPI spec, `POST /pods` |

Use cases ([`lab/use_cases.json`](./lab/use_cases.json)):

| Use case | Input tokens | Output tokens | Rates (req/s) | SLO |
|---|---|---|---|---|
| chat | 512 | 256 | 1, 2, 4, 8, 16 | TTFT ≤ 1000 ms, TPOT ≤ 50 ms |
| rag | 4096 | 256 | 0.5, 1, 2, 4, 8 | TTFT ≤ 2000 ms, TPOT ≤ 50 ms |
| summarize | 2048 | 1024 | 0.5, 1, 2, 4 | TTFT ≤ 2000 ms, TPOT ≤ 60 ms |

The dataset is `random`: lengths and arrival rate define a use case, not prompt content. Each run now gets its own seed; the published results used one fixed seed, which let GPUs with a large KV cache serve later runs from vLLM's prefix cache ([FINDINGS C21](./FINDINGS.md)). The per-run seed has not been re-run yet. `--ignore-eos` makes every request generate exactly the output length (vLLM 0.31.0 already forces it for `random`; `vllm/benchmarks/serve.py`).

### Files

| File | Runs on | Does |
|---|---|---|
| [`lab/pod_sweep.py`](./lab/pod_sweep.py) | your machine | Creates a Pod, uploads the lab, starts the bootstrap, polls, fetches results, terminates the Pod in a `finally`, appends to `results/ledger.json` and refuses a launch that would pass `BUDGET_USD` |
| [`lab/pod_bootstrap.sh`](./lab/pod_bootstrap.sh) | the Pod | Installs vLLM, checks every `vllm bench serve` flag the sweep uses, starts the server, runs the sweep |
| [`lab/run_sweep.sh`](./lab/run_sweep.sh) | the Pod | Host capture, warm-up, then per use case × rate: `/metrics` before and after, 1 s GPU sampling, `vllm bench serve` |
| [`lab/capture_host.sh`](./lab/capture_host.sh) | the Pod | GPU UUID, PCIe gen and width, `nvidia-smi topo -m`, CPU, driver, CUDA, kernel, `RUNPOD_*` env (credentials, public IP and port map dropped) |
| [`lab/sample_gpu.sh`](./lab/sample_gpu.sh) | the Pod | Utilization, power, SM clock, temperature, throttle reasons — uses `clocks_event_reasons.*` when the driver has renamed `clocks_throttle_reasons.*` |
| [`lab/build_profile.py`](./lab/build_profile.py) | your machine | `results/profile.json` and `results/PROFILE.md`, including cost at SLO |
| [`lab/coldstart_probe.py`](./lab/coldstart_probe.py) | your machine | Serverless cold vs warm request pairs, with job id and submit time; `GAPS=15,30,60` sets a different idle gap before each probe |
| [`lab/serverless_endpoint.py`](./lab/serverless_endpoint.py) | your machine | Creates and deletes the probe's template and endpoint (workers 0–1 or `--workers-max N`, idle 5 s, FlashBoot on or off) |
| [`lab/concurrent_probe.py`](./lab/concurrent_probe.py) | your machine | Sends `BURST` requests at once, cold wave then warm wave, and records `delayTime` and `workerId` per job with the worker list after each wave |
| [`lab/capture_worker_logs.sh`](./lab/capture_worker_logs.sh) | your machine | Every 20 s, merges each worker's system and container log lines; container lines vanish when the container is removed |
| [`lab/coldstart_phases.py`](./lab/coldstart_phases.py) | your machine | Splits each cold start into phases from those logs |
| [`lab/stock_snapshots.sh`](./lab/stock_snapshots.sh) | your machine | Read-only stock snapshots, with and without a CUDA 13 floor |
| [`lab/stock_create_probe.py`](./lab/stock_create_probe.py) | your machine | Paid: after each stock reading, one create on a `Low` type and one on a no-stock type, Pod deleted at once |
| [`lab/collect_evidence.py`](./lab/collect_evidence.py) | your machine | Saves the lines of each cited public page into [`evidence/excerpts.md`](./evidence/excerpts.md) |

### Run it

Paid: every step below except `--dry-run` and `--ledger` creates billable compute.

```bash
cd inference-characterization/lab
python3 pod_sweep.py --label RTX_4090 --gpu "NVIDIA GeForce RTX 4090" --dry-run
BUDGET_USD=40 python3 pod_sweep.py --label RTX_4090 --gpu "NVIDIA GeForce RTX 4090"
python3 pod_sweep.py --ledger
python3 build_profile.py results

# Serverless cold starts
python3 serverless_endpoint.py create --flashboot on        # prints ENDPOINT_ID=...
./capture_worker_logs.sh <ENDPOINT_ID> results/coldstart_logs/flashboot_on &
ENDPOINT_ID=<ENDPOINT_ID> N=3 GAP_S=300 python3 coldstart_probe.py
# or one idle gap per probe: ENDPOINT_ID=<ENDPOINT_ID> GAPS=15,30,60,120,300 OUT=results/coldstart_gaps.json python3 coldstart_probe.py
python3 serverless_endpoint.py delete
python3 coldstart_phases.py results/coldstart.json results/coldstart_logs/flashboot_on results/coldstart_flashboot_on_phases.json

# Several workers, concurrent requests
python3 serverless_endpoint.py create --flashboot on --workers-max 3
ENDPOINT_ID=<ENDPOINT_ID> BURST=5 python3 concurrent_probe.py
python3 serverless_endpoint.py delete

# Does a `Low` stock reading predict a successful create (one Pod created and deleted per attempt)
ROUNDS=10 SLEEP_S=60 python3 stock_create_probe.py
```

Community Cloud runs once, at the smallest scale that proves F1 and F2 — one use case at one rate. It needs `supportPublicIp` for SSH:

```bash
python3 pod_sweep.py --label RTX_4090_community --gpu "NVIDIA GeForce RTX 4090" --cloud COMMUNITY --cases chat --rates 1
```

### Results

| ID | Result | Claims in [`FINDINGS.md`](./FINDINGS.md) |
|---|---|---|
| F1 | Secure Cloud: passes. Community Cloud: not determined — the Pod never got a public IP or port 22 | C3, C4, C7 |
| F2 | Secure Cloud: passes; the only throttle reason seen was `sw_power_cap`. Community Cloud: not determined | C5, C6, C7 |
| F3 | Passes on every GPU type obtained; one-GPU stock with a CUDA 13 floor changed within hours | C1, C2 |
| F4 | The job response carries one `delayTime` and a `workerId` that does not distinguish cold from warm; the v2 worker logs hold the phases, but only while the container exists | C9–C14, C17–C19 |
| F5 | Not as worded: Modal meets three of the four conditions under a literal reading | C16, [`RESEARCH.md`](./RESEARCH.md) |

Raw results: [`lab/results/`](./lab/results). Profile table: [`lab/results/PROFILE.md`](./lab/results/PROFILE.md).

---

## 한국어

**목표:** 같은 모델 이미지를 여러 GPU 종류와 호스트에서 돌려, 유즈케이스별로 엔진과 하드웨어가 처리량, 꼬리 지연, 비용에 어떤 영향을 주는지 호스트 정보와 함께 기록한다.

**상태:** 2026-10-06~07(KST) 실제 계정에서 끝까지 실행했다. vLLM 0.31.0(Pod)과 `runpod/worker-v1-vllm:v2.28.0`(Serverless)에서 검증했다. 근거가 붙은 결과는 [`FINDINGS.md`](./FINDINGS.md)에 있다.

### 테스트 시나리오

가설은 모두 기능 점검이다. 플랫폼이 이 분석을 할 수 있게 해 주는지, 어느 제품과 어느 클라우드 유형에서 되는지를 본다. 측정한 숫자(처리량, 백분위, 토큰당 비용)는 데이터로 기록할 뿐 판정 기준으로 쓰지 않는다.

| ID | 가설 | 통과 조건 |
|---|---|---|
| F1 | Secure Cloud와 Community Cloud Pod 모두에서 호스트 정보를 수집할 수 있다: GPU UUID, PCIe 세대와 폭, GPU 토폴로지, CPU, 드라이버와 CUDA, 데이터센터, 호스트명 | 클라우드 유형별로 `host.json`의 모든 필드가 채워진다 |
| F2 | 두 클라우드 유형 모두에서 스로틀 사유, 전력, SM 클럭을 1초 단위로 샘플링하고 vLLM 선점 카운터를 읽을 수 있다 | `*.gpu.csv`와 `/metrics` 스냅샷이 채워진다 |
| F3 | 같은 이미지와 스윕이 요청한 모든 GPU 종류에서 끝까지 돌아 유즈케이스별 백분위와 goodput을 낸다 | 유즈케이스와 요청률마다 결과 JSON이 하나씩 생긴다. 확보하지 못한 GPU 종류도 결과로 기록한다 |
| F4 | Serverless는 콜드와 웜 요청에 `delayTime`, `executionTime`, `workerId`를 돌려주지만 콜드스타트를 단계별로 나눠 주지 않는다. `workerId`로 GPU나 호스트를 알아낼 수 있는지 본다 | 프로브 출력에 필드가 있는지 |
| F5 | 다른 GPU 플랫폼 가운데 같은 기능을 문서화한 곳 | [`RESEARCH.md`](./RESEARCH.md) 데스크 리서치 |

다른 환경으로 옮겨 쓸 수 있는 것은 엔진 수준과 GPU 종류 수준의 동작이다. 로드밸런서, 오토스케일러, 스케줄링, 네트워크 경로는 옮겨지지 않는다. 클라이언트가 서버와 같은 Pod에서 돌기 때문에 네트워크는 의도적으로 측정에서 빠진다.

### 고정 조건

| 항목 | 값 | 확인 방법 |
|---|---|---|
| 모델 | `Qwen/Qwen2.5-7B-Instruct`, `--max-model-len 8192`, `--gpu-memory-utilization 0.90` | — |
| 엔진 | vLLM 0.31.0 (Pod에서 `pip install vllm==0.31.0`) | PyPI, 2026-10-06 확인 |
| CUDA | 호스트 드라이버가 CUDA 13을 지원해야 한다. vLLM 0.31.0이 `cu13` 의존성과 함께 `torch==2.13.0`을 고정한다 | PyPI `requires_dist`, 2026-10-06 확인 |
| 이미지 | `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404` (`pod/01-launch-connect`와 같은 이미지) | Docker Hub 태그 조회 |
| Pod | GPU 1개, 컨테이너 디스크 80 GB, 볼륨 없음, 포트 `22/tcp`, `allowedCudaVersions: ["13.0"]` | 공개 OpenAPI 스펙 `POST /pods` |

유즈케이스 ([`lab/use_cases.json`](./lab/use_cases.json)):

| 유즈케이스 | 입력 토큰 | 출력 토큰 | 요청률 (req/s) | SLO |
|---|---|---|---|---|
| chat | 512 | 256 | 1, 2, 4, 8, 16 | TTFT ≤ 1000 ms, TPOT ≤ 50 ms |
| rag | 4096 | 256 | 0.5, 1, 2, 4, 8 | TTFT ≤ 2000 ms, TPOT ≤ 50 ms |
| summarize | 2048 | 1024 | 0.5, 1, 2, 4 | TTFT ≤ 2000 ms, TPOT ≤ 60 ms |

데이터셋은 `random`이다. 유즈케이스는 프롬프트 내용이 아니라 길이와 도착률로 정의된다. 이제 실행마다 다른 시드를 쓴다. 공개된 결과는 고정 시드 하나로 돌렸고, 그래서 KV 캐시가 큰 GPU가 이후 실행을 vLLM 프리픽스 캐시로 처리했다([FINDINGS C21](./FINDINGS.md)). 실행별 시드로는 아직 다시 돌리지 않았다. `--ignore-eos`로 모든 요청이 정확히 출력 길이만큼 생성한다(vLLM 0.31.0은 `random`에서 이미 강제한다. `vllm/benchmarks/serve.py`).

### 파일

| 파일 | 실행 위치 | 하는 일 |
|---|---|---|
| [`lab/pod_sweep.py`](./lab/pod_sweep.py) | 로컬 | Pod 생성, lab 업로드, 부트스트랩 시작, 폴링, 결과 회수, `finally`에서 Pod 종료, `results/ledger.json`에 기록, `BUDGET_USD`를 넘길 실행은 거부 |
| [`lab/pod_bootstrap.sh`](./lab/pod_bootstrap.sh) | Pod | vLLM 설치, 스윕이 쓰는 `vllm bench serve` 플래그 전부 확인, 서버 기동, 스윕 실행 |
| [`lab/run_sweep.sh`](./lab/run_sweep.sh) | Pod | 호스트 캡처, 워밍업, 유즈케이스 × 요청률마다 `/metrics` 전후 스냅샷, 1초 GPU 샘플링, `vllm bench serve` |
| [`lab/capture_host.sh`](./lab/capture_host.sh) | Pod | GPU UUID, PCIe 세대와 폭, `nvidia-smi topo -m`, CPU, 드라이버, CUDA, 커널, `RUNPOD_*` 환경변수(자격 증명, 공인 IP, 포트 매핑 제외) |
| [`lab/sample_gpu.sh`](./lab/sample_gpu.sh) | Pod | 활용률, 전력, SM 클럭, 온도, 스로틀 사유. 드라이버가 `clocks_throttle_reasons.*`를 `clocks_event_reasons.*`로 바꿨으면 새 이름을 쓴다 |
| [`lab/build_profile.py`](./lab/build_profile.py) | 로컬 | `results/profile.json`과 `results/PROFILE.md`, SLO 기준 비용 포함 |
| [`lab/coldstart_probe.py`](./lab/coldstart_probe.py) | 로컬 | Serverless 콜드와 웜 요청 쌍, 작업 id와 제출 시각 포함. `GAPS=15,30,60`으로 프로브마다 다른 유휴 간격을 준다 |
| [`lab/serverless_endpoint.py`](./lab/serverless_endpoint.py) | 로컬 | 프로브용 템플릿과 엔드포인트 생성과 삭제(워커 0–1 또는 `--workers-max N`, 유휴 5초, FlashBoot 켬 또는 끔) |
| [`lab/concurrent_probe.py`](./lab/concurrent_probe.py) | 로컬 | `BURST`건을 동시에 보내 콜드 물결과 웜 물결을 만들고, 작업별 `delayTime`과 `workerId`, 물결마다의 워커 목록을 기록 |
| [`lab/capture_worker_logs.sh`](./lab/capture_worker_logs.sh) | 로컬 | 20초마다 워커별 시스템과 컨테이너 로그를 합쳐 저장. 컨테이너 로그는 컨테이너가 지워지면 사라진다 |
| [`lab/coldstart_phases.py`](./lab/coldstart_phases.py) | 로컬 | 그 로그로 콜드스타트를 단계별로 나눈다 |
| [`lab/stock_snapshots.sh`](./lab/stock_snapshots.sh) | 로컬 | 읽기 전용 재고 스냅샷, CUDA 13 조건 유무 각각 |
| [`lab/stock_create_probe.py`](./lab/stock_create_probe.py) | 로컬 | 과금: 재고를 읽을 때마다 `Low` 종류 하나와 재고 없음 종류 하나에 생성을 시도하고 Pod는 즉시 삭제 |
| [`lab/collect_evidence.py`](./lab/collect_evidence.py) | 로컬 | 인용한 공개 페이지에서 해당 줄을 [`evidence/excerpts.md`](./evidence/excerpts.md)에 저장 |

### 실행

과금 주의: `--dry-run`과 `--ledger`를 뺀 모든 단계가 과금되는 컴퓨트를 만든다.

```bash
cd inference-characterization/lab
python3 pod_sweep.py --label RTX_4090 --gpu "NVIDIA GeForce RTX 4090" --dry-run
BUDGET_USD=40 python3 pod_sweep.py --label RTX_4090 --gpu "NVIDIA GeForce RTX 4090"
python3 pod_sweep.py --ledger
python3 build_profile.py results

# Serverless 콜드스타트
python3 serverless_endpoint.py create --flashboot on        # ENDPOINT_ID=... 출력
./capture_worker_logs.sh <ENDPOINT_ID> results/coldstart_logs/flashboot_on &
ENDPOINT_ID=<ENDPOINT_ID> N=3 GAP_S=300 python3 coldstart_probe.py
# 또는 프로브마다 유휴 간격을 달리: ENDPOINT_ID=<ENDPOINT_ID> GAPS=15,30,60,120,300 OUT=results/coldstart_gaps.json python3 coldstart_probe.py
python3 serverless_endpoint.py delete
python3 coldstart_phases.py results/coldstart.json results/coldstart_logs/flashboot_on results/coldstart_flashboot_on_phases.json

# 워커 여러 개, 동시 요청
python3 serverless_endpoint.py create --flashboot on --workers-max 3
ENDPOINT_ID=<ENDPOINT_ID> BURST=5 python3 concurrent_probe.py
python3 serverless_endpoint.py delete

# `Low` 재고 표시가 생성 성공을 예측하는지(시도마다 Pod 하나 생성·삭제)
ROUNDS=10 SLEEP_S=60 python3 stock_create_probe.py
```

Community Cloud는 F1과 F2를 확인하는 최소 규모로 한 번만 돌린다. 유즈케이스 하나, 요청률 하나다. SSH를 쓰려면 `supportPublicIp`가 필요하다.

```bash
python3 pod_sweep.py --label RTX_4090_community --gpu "NVIDIA GeForce RTX 4090" --cloud COMMUNITY --cases chat --rates 1
```

### 결과

| ID | 결과 | [`FINDINGS.md`](./FINDINGS.md)의 주장 |
|---|---|---|
| F1 | Secure Cloud: 통과. Community Cloud: 판정 불가. Pod에 공인 IP와 22번 포트가 생기지 않았다 | C3, C4, C7 |
| F2 | Secure Cloud: 통과. 관측된 스로틀 사유는 `sw_power_cap`뿐이다. Community Cloud: 판정 불가 | C5, C6, C7 |
| F3 | 확보한 모든 GPU 종류에서 통과. CUDA 13 조건의 1장짜리 재고는 몇 시간 사이에 바뀌었다 | C1, C2 |
| F4 | 작업 응답에는 `delayTime` 하나와 콜드·웜을 구분하지 못하는 `workerId`만 있다. v2 워커 로그에 단계 정보가 있지만 컨테이너가 살아 있는 동안만 남는다 | C9–C14, C17–C19 |
| F5 | 문장 그대로는 성립하지 않는다. Modal이 문자 그대로 읽으면 네 조건 중 세 가지를 충족한다 | C16, [`RESEARCH.md`](./RESEARCH.md) |

원자료: [`lab/results/`](./lab/results). 프로파일 표: [`lab/results/PROFILE.md`](./lab/results/PROFILE.md).
