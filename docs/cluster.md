---
layout: default
title: Cluster
permalink: /cluster/
---

# Cluster

<div class="lang" data-lang="en" markdown="1">

## English

<div class="note" markdown="1">
**Status: lab 01 stage 1 done; stage 2 ran once (2026-11-07).** A 2 × 8 A100 SXM cluster ran for 35 minutes, but NCCL could not use InfiniBand from the stock PyTorch image; a rerun with an RDMA-ready image is open ([#52](https://github.com/litkhai/runpod-hols/issues/52)).
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) are Runpod's multi-node offering: fully managed clusters with high-speed interconnect for distributed training and large-scale inference.

| Property | Value |
|---|---|
| GPUs | B300, B200, H200, H100 SXM, A100 SXM (console, 2026-11-07) |
| Cluster size | 2 Pods or more, 8 GPUs per Pod; the form's slider goes to 32 Pods |
| Interconnect | 1600 Gbps (A100) to 6400 Gbps (B300) between nodes, exposed as `ens1`–`ens8` |
| Price, smallest cluster | A100 SXM USD 2.15/GPU-hr = USD 34.37/hr; H100 SXM USD 4.79 = USD 76.61/hr |
| Frameworks | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### Lab 01 — torchrun and NCCL

[`cluster/01-pytorch-distributed`](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed) measures how fast GPUs exchange gradients and what that does to data-parallel training. The same `run.sh` runs on one multi-GPU Pod (stage 1) and on every node of a cluster (stage 2): topology, an NCCL all-reduce sweep (1 MiB – 1 GiB), then a 101 M-parameter model under `DistributedDataParallel` on 1 GPU and on all GPUs.

```bash
cd cluster/01-pytorch-distributed
python3 lab.py create                    # 2x RTX 4090; --gpu "NVIDIA A100-SXM4-80GB" for the A100 pair
python3 lab.py push && python3 lab.py run 2x4090 && python3 lab.py pull
python3 lab.py delete
```

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}" alt="Pod deploy form with RTX 4090 and GPU count 2, USD 1.78/hr" loading="lazy" width="1400" height="998"></a><figcaption>Deploy form: a multi-GPU Pod is one card plus a GPU count. The lab does the same through <code>POST /pods</code> with <code>gpuCount: 2</code>.</figcaption></figure>

### Stage 1 results — one Pod, two GPUs

| | 2x RTX 4090 | 2x A100 SXM 80GB |
|---|---|---|
| Price | USD 1.78/hr | USD 3.58/hr |
| Link (`nvidia-smi topo -m`) | `SYS`: PCIe across two NUMA nodes | `NV12`: 12 NVLinks |
| NCCL transport | `SHM` through host memory | `P2P` GPU to GPU |
| all-reduce `busbw`, 1 GiB | **15.6 GB/s** | **201 GB/s** |
| DDP, 1 GPU | 39,453 samples/s | 23,132 samples/s |
| DDP, 2 GPUs | 16,244 samples/s | 41,871 samples/s |
| Scaling efficiency | **0.21** | **0.91** |

- **Two RTX 4090s trained 2.4× slower than one.** Each step all-reduces about 400 MB of gradients: about 26 ms at 15.6 GB/s, against 6.5 ms of compute. GeForce cards have no GPU-to-GPU P2P, so NCCL went through host memory.
- **The A100 pair scaled at 91%**: over NVLink the 400 MB takes about 2 ms.
- **The console's GPU utilization hid it.** Both 4090s read 100% while most of each step was waiting on the transfer; NCCL kernels hold the GPU while they wait.
- The single A100 was slower than the single 4090 here because the model runs plain fp32 (TF32 off, the PyTorch default). Per dollar, one RTX 4090 beat both pairs for this model.

Why the gap is this large: a ring all-reduce moves 2(n−1)/n of the gradient per GPU every step, so the link — not the GPU — sets the ceiling, and `SYS` against `NV12` decides which side of it you land on. The arithmetic, and why tensor parallelism must never leave the NVLink domain, is in [GPU Topology → in numbers]({{ '/readings/gpu-topology/#in-numbers' | relative_url }}); sizing and cost in [GPU & LLM Basics]({{ '/readings/gpu-llm-basics/' | relative_url }}).

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}" alt="Pod Telemetry tab: two RTX 4090 GPUs at 100% utilization" loading="lazy" width="1400" height="998"></a><figcaption>Telemetry during the 2x RTX 4090 run: 100% on both GPUs, yet the pair trained at a fifth of its ideal speed.</figcaption></figure>

Stage 1 cost about USD 0.40 (7 and 3 minutes of Pod time).

**Four H100 SXM in one Pod** (2026-11-08; a single Pod had stock while no cluster did):

| 2026-11-08, US-NE-1 | 4x H100 SXM 80GB |
|---|---|
| Price | USD 15.96/hr |
| Link (`topo -m`) | `NV18`: 18 NVLinks between every pair |
| all-reduce `busbw`, 1 MiB / 1 GiB | 11.1 / **356.3 GB/s** |
| DDP, 1 GPU | 54,981 samples/s (4.7 ms/step) |
| DDP, 4 GPUs | 179,442 samples/s (5.7 ms/step) |
| Scaling efficiency (4 GPUs / 4 × 1 GPU) | **0.82** |

The link is 1.8× the A100 pair's and one H100 is 2.4× one A100 here, but efficiency fell to 0.82: with 4.7 ms of compute against about 1 ms of all-reduce, the faster the GPU, the more the link decides. This is the in-node ceiling to compare a cluster against — stage 2's socket run moved 0.32 GB/s between nodes. About USD 3 for 11.5 minutes.

### Stage 2 — Instant Cluster

Clusters are created in the console (**Clusters → Create cluster**) or over GraphQL with `createCluster` / `deleteCluster`; the REST API has no cluster endpoints. The form prices the whole cluster per hour and marks each type Available or Unavailable. On 2026-11-07 every type was **Unavailable**, while single A100 SXM and H100 SXM Pods could be deployed at the same time. The form reads this from GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }`, which returns `null` for Unavailable. That evening A100 SXM showed Available from about 19:29 to 19:36 KST and was gone by 19:46, so this lab waits for stock with a script that creates the cluster through GraphQL, runs both nodes and deletes it after at most 75 minutes ([`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)).

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster form: B300, B200, H200 SXM and H100 SXM all Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster, 2026-11-07: 8 GPUs per Pod, price per GPU-hour and per cluster-hour, every type Unavailable.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="Billing page showing a spend rate limit of USD 80 per hour" loading="lazy" width="1400" height="998"></a><figcaption>Billing shows this account's <strong>spend rate limit, USD 80/hr</strong>. The smallest A100 cluster (USD 34.37/hr) and H100 cluster (USD 76.61/hr) fit under it; H200 (USD 101.57) and B200 (USD 153.41) would not — the "default spending limit" the docs mention.</figcaption></figure>

### Sockets instead of InfiniBand

A100 SXM came back at 21:42 KST; `cluster.py` created the cluster at 21:48, SSH was open on both nodes 114 s later, `run.sh` ran 21:50–22:09, and the cluster was deleted at 22:23: Runpod charged USD 13.86: billing stopped at 22:15, when the faulty hosts were taken out of service (see below). `createCluster` needs `deployCost` (the whole cluster's hourly offer; the API checks it per Pod against a minimum of USD 14.32), and the Pods were billed at the list price whatever the offer.

| 16 GPUs, `runpod/pytorch` image as is | Result |
|---|---|
| NCCL network between nodes | **`Socket` over `ens1`**: *"Failed to open libibverbs.so[.1]"* |
| all-reduce `busbw`, 1 GiB | **0.32 GB/s** (2 A100s over NVLink in stage 1: 201 GB/s) |
| DDP, 1 GPU → 16 GPUs | 23,497 → **1,105 samples/s** (step 10.9 ms → 3,705 ms) |

- **The image had no RDMA user space**, so NCCL fell back to TCP on `ens1` without a warning and the job finished anyway: sixteen GPUs trained 21× slower than one. Each node had twelve Mellanox HCAs, and Runpod had already set `NCCL_IB_HCA` to the eight next to the GPUs.
- **Installing `libibverbs1` from Ubuntu was not enough.** NCCL then chose `IB` with GPU Direct RDMA on all eight HCAs, and every HCA reported *"local catastrophic error"*; the all-reduce made no progress in ten minutes and the run was stopped.
- Check the NCCL log for `Using network IB` before trusting any multi-node number. The console's cluster templates use a separate image, `runpod/pytorch:1.0.7-cu1300-torch291-ubuntu2404-cluster`; the next run uses it.

Details and raw logs: [lab README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#stage-2-run--sockets-instead-of-infiniband).

### InfiniBand fails on the cluster image

`cluster.py` waited a day and ran again on 2026-11-08 with the cluster image (`…-ubuntu2404-cluster`, NCCL 2.27.7). The cluster was created at 22:28 KST and SSH was open 50 s later. This time NCCL found the eight 200 Gb/s InfiniBand HCAs, connected the queue pairs and logged `Using network IB` with GPU Direct RDMA through DMA-BUF. On the first all-reduce, at 22:30, every HCA on both nodes reported *"local catastrophic error"* within ten seconds. Nothing moved after that; the run hit its 40-minute timeout and the watchdog deleted the cluster at 75 minutes (billing had already stopped at about 22:33: USD 2.06, USD 15.91 for the two clusters).

<figure class="shot"><a href="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}" alt="NCCL log: Using network IB and GDRDMA, then local catastrophic error on every HCA" loading="lazy" width="1400" height="480"></a><figcaption>NCCL log of the rerun (excerpt): IB and GPU Direct RDMA set up correctly, then the same fatal event on all eight HCAs of both nodes.</figcaption></figure>

- **Not the image.** The first run with Ubuntu's `libibverbs` failed the same way.
- **Cause: a host hardware fault (Runpod support, 2026-11-09).** At both times (2026-11-07 about 13:09 UTC, 2026-11-08 about 13:30 UTC) each host had a fatal PCIe error that disconnected all of its devices at once: GPUs, NVSwitches, storage and every InfiniBand card. The *"local catastrophic error"* lines are the HCAs dropping off. Not the NCCL configuration, the InfiniBand settings or the image; support advised against changing NCCL settings such as `NCCL_NET_GDR_LEVEL=LOC` because of it. The machines were taken out of service.
- **The earlier guess was wrong.** The logs had been read as a GPU Direct RDMA failure (the container's `libmlx5` lacks `mlx5dv_reg_dmabuf_mr`). That message is real but unrelated.
- **A host fault looks like a hang.** Nothing exits with an error. Runpod detects the fault, takes the machines out of service within minutes and stops billing then (about USD 4.92 of the two clusters fell after the faults), but sends no notification.
- **Same group of hosts.** The two clusters used different pairs of machines from one group of A100 SXM hosts; all four had the same fault and are out of service.
- **Checks Runpod recommends.** After start: `nvidia-smi` (8 GPUs) and `ibv_devinfo` (every port `PORT_ACTIVE`) on each node, then a short cross-node `all_reduce_perf` with small messages. During the run: `timeout=timedelta(minutes=5)` in `init_process_group`. The timeout matters most, because a fault can come later: here after 1.5 minutes and after 16 minutes.
- **Recorded as a failure.** As of 2026-11-08 this site has no multi-node bandwidth figure for a Runpod Instant Cluster ([#52](https://github.com/litkhai/runpod-hols/issues/52)).

Timeline and log excerpt: [lab README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#stage-2-rerun--the-cluster-image-infiniband-fails).

### Possible labs

| Lab | Contents |
|---|---|
| 01-pytorch-distributed | Stage 1 done; stage 2 ran on sockets, rerun with an RDMA-ready image open |
| 02-slurm-cluster | Deploy a managed Slurm cluster and submit a job |
| 03-axolotl-finetune | Multi-node LLM fine-tuning with Axolotl |

### References

[Overview](https://docs.runpod.io/instant-clusters) ·
[PyTorch](https://docs.runpod.io/instant-clusters/pytorch) ·
[Slurm](https://docs.runpod.io/instant-clusters/slurm-clusters) ·
[Axolotl](https://docs.runpod.io/instant-clusters/axolotl) ·
[Configuration](https://docs.runpod.io/instant-clusters/configuration) ·
[Scaling](https://docs.runpod.io/instant-clusters/scale-clusters) ·
[Observability](https://docs.runpod.io/instant-clusters/cluster-observability) ·
[pytorch-cluster image](https://github.com/runpod/containers/tree/main/official-templates/pytorch-cluster)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

<div class="note" markdown="1">
**상태: 실습 01 의 1단계 완료, 2단계 1회 실행 (2026-11-07).** A100 SXM 2 × 8장 클러스터를 35분 돌렸지만, 기본 PyTorch 이미지에서는 NCCL 이 InfiniBand 를 쓰지 못했다. RDMA 를 갖춘 이미지로 다시 돌리는 일이 남아 있다 ([#52](https://github.com/litkhai/runpod-hols/issues/52)).
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) 는 Runpod 의 다중 노드 제품입니다. 분산 학습과 대규모 추론을 위한, 고속 인터커넥트를 갖춘 완전관리형 클러스터입니다.

| 항목 | 값 |
|---|---|
| GPU | B300, B200, H200, H100 SXM, A100 SXM (콘솔, 2026-11-07) |
| 클러스터 규모 | Pod 2개 이상, Pod 당 GPU 8장. 화면의 슬라이더는 32 Pod 까지 |
| 인터커넥트 | 노드 간 1600 Gbps (A100) ~ 6400 Gbps (B300), `ens1`~`ens8` 인터페이스 |
| 가장 작은 클러스터 가격 | A100 SXM GPU 시간당 USD 2.15 = 시간당 USD 34.37, H100 SXM USD 4.79 = 시간당 USD 76.61 |
| 프레임워크 | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### 실습 01 — torchrun 과 NCCL

[`cluster/01-pytorch-distributed`](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed) 는 GPU 끼리 기울기를 얼마나 빨리 주고받는지, 그것이 데이터 병렬 학습에 어떤 영향을 주는지 잰다. 같은 `run.sh` 가 멀티 GPU Pod 한 대(1단계)와 클러스터의 모든 노드(2단계)에서 돈다. 토폴로지, NCCL all-reduce 측정(1 MiB – 1 GiB), 그리고 1억 1백만 파라미터 모델을 `DistributedDataParallel` 로 GPU 1장과 전체 GPU 에서 돌린다.

```bash
cd cluster/01-pytorch-distributed
python3 lab.py create                    # RTX 4090 두 장. A100 은 --gpu "NVIDIA A100-SXM4-80GB"
python3 lab.py push && python3 lab.py run 2x4090 && python3 lab.py pull
python3 lab.py delete
```

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}" alt="RTX 4090, GPU count 2 를 고른 Pod 배포 화면, 시간당 USD 1.78" loading="lazy" width="1400" height="998"></a><figcaption>배포 화면: 멀티 GPU Pod 는 카드 하나와 GPU 개수로 정한다. 실습은 같은 일을 <code>POST /pods</code> 의 <code>gpuCount: 2</code> 로 한다.</figcaption></figure>

### 1단계 결과 — Pod 한 대, GPU 두 장

| | RTX 4090 두 장 | A100 SXM 80GB 두 장 |
|---|---|---|
| 가격 | USD 1.78/hr | USD 3.58/hr |
| 연결 (`nvidia-smi topo -m`) | `SYS`: NUMA 노드 두 개에 걸친 PCIe | `NV12`: NVLink 12개 |
| NCCL 전송 | `SHM` 호스트 메모리 경유 | `P2P` GPU 간 직접 |
| all-reduce `busbw`, 1 GiB | **15.6 GB/s** | **201 GB/s** |
| DDP, GPU 1장 | 초당 39,453 샘플 | 초당 23,132 샘플 |
| DDP, GPU 2장 | 초당 16,244 샘플 | 초당 41,871 샘플 |
| 확장 효율 | **0.21** | **0.91** |

- **RTX 4090 두 장이 한 장보다 2.4배 느렸다.** 스텝마다 기울기 약 400 MB 를 all-reduce 하는데, 15.6 GB/s 로 약 26 ms 다. 계산은 6.5 ms 였다. GeForce 카드는 GPU 간 P2P 가 없어서 NCCL 이 호스트 메모리를 거쳤다.
- **A100 두 장은 91% 로 확장됐다.** NVLink 로는 400 MB 가 약 2 ms 다.
- **콘솔의 GPU 사용률로는 보이지 않았다.** 4090 두 장 모두 100% 였지만 스텝 대부분은 전송 대기였다. NCCL 커널은 기다리는 동안에도 GPU 를 점유한다.
- 여기서 A100 한 장이 4090 한 장보다 느린 것은 모델이 순수 fp32 (TF32 꺼짐, PyTorch 기본값) 이기 때문이다. 달러당으로는 이 모델에서 RTX 4090 한 장이 두 조합보다 나았다.

차이가 이렇게 큰 이유: ring all-reduce 는 매 스텝 GPU 당 그래디언트의 2(n−1)/n 을 전송하므로, 상한을 정하는 것은 GPU 가 아니라 링크이고, `SYS` 냐 `NV12` 냐가 그 상한의 어느 쪽에 떨어지는지를 가른다. 계산 과정과 텐서 병렬이 NVLink 도메인을 절대 벗어나면 안 되는 이유는 [GPU Topology → 숫자로]({{ '/readings/gpu-topology/#in-numbers-ko' | relative_url }}) 에, 사이징과 비용은 [GPU·LLM 기초]({{ '/readings/gpu-llm-basics/' | relative_url }}) 에 있다.

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}" alt="Pod Telemetry 탭: RTX 4090 두 장 사용률 100%" loading="lazy" width="1400" height="998"></a><figcaption>RTX 4090 두 장 실행 중 Telemetry: 두 GPU 모두 100% 인데, 학습 속도는 이상치의 5분의 1 이었다.</figcaption></figure>

1단계 비용은 약 USD 0.40 (Pod 7분과 3분).

**Pod 한 대에 H100 SXM 4장** (2026-11-08. 클러스터 재고가 없을 때도 단일 Pod 는 재고가 있었다):

| 2026-11-08, US-NE-1 | H100 SXM 80GB 4장 |
|---|---|
| 가격 | 시간당 USD 15.96 |
| 연결 (`topo -m`) | `NV18`: 모든 쌍 사이 NVLink 18개 |
| all-reduce `busbw`, 1 MiB / 1 GiB | 11.1 / **356.3 GB/s** |
| DDP, GPU 1장 | 54,981 samples/s (스텝 4.7 ms) |
| DDP, GPU 4장 | 179,442 samples/s (스텝 5.7 ms) |
| 확장 효율 (4장 / 1장 × 4) | **0.82** |

연결은 A100 두 장의 1.8배, H100 한 장은 A100 한 장의 2.4배였지만 효율은 0.82 로 떨어졌다. 계산 4.7 ms 에 all-reduce 약 1 ms 라, GPU 가 빠를수록 연결이 성능을 좌우한다. 클러스터와 비교할 노드 안의 천장이 이것이다. 2단계 소켓 실행은 노드 사이 0.32 GB/s 였다. 11.5분에 약 USD 3.

### 2단계 — Instant Cluster

클러스터는 콘솔 (**Clusters → Create cluster**) 이나 GraphQL 의 `createCluster` / `deleteCluster` 로 만든다. REST API 에는 클러스터 엔드포인트가 없다. 화면은 클러스터 전체의 시간당 가격과 종류별 Available/Unavailable 을 보여준다. 2026-11-07 에는 모든 종류가 **Unavailable** 이었고, 같은 시각 A100 SXM, H100 SXM 단일 Pod 는 배포할 수 있었다. 화면은 이 값을 GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }` 로 읽으며, Unavailable 이면 `null` 이다. 같은 날 저녁 A100 SXM 이 한국 시간 약 19:29–19:36 에 Available 이었다가 19:46 에는 사라졌다. 그래서 이 실습은 스크립트로 재고를 기다려, GraphQL 로 클러스터를 만들고 두 노드에서 돌린 뒤 늦어도 75분 안에 지운다 ([`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)).

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster 화면: B300, B200, H200 SXM, H100 SXM 모두 Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster, 2026-11-07: Pod 당 GPU 8장, GPU 시간당과 클러스터 시간당 가격, 모든 종류 Unavailable.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="시간당 USD 80 의 지출 속도 한도를 보여주는 Billing 화면" loading="lazy" width="1400" height="998"></a><figcaption>Billing 화면에 이 계정의 <strong>지출 속도 한도, 시간당 USD 80</strong> 이 나온다. 가장 작은 A100 클러스터(시간당 USD 34.37)와 H100 클러스터(USD 76.61)는 그 안에 들어가고, H200(USD 101.57)과 B200(USD 153.41)은 넘는다. 문서가 말하는 "기본 지출 한도" 가 이것이다.</figcaption></figure>

### InfiniBand 대신 소켓

A100 SXM 이 한국 시간 21:42 에 다시 나왔다. `cluster.py` 가 21:48 에 클러스터를 만들었고, 114초 뒤 두 노드에 SSH 가 열렸으며, `run.sh` 가 21:50–22:09 에 돌고 22:23 에 클러스터를 지웠다. Runpod 청구액은 USD 13.86 이다. 장애 난 호스트가 서비스에서 빠진 22:15 에 과금이 멈췄다 (아래 참고). `createCluster` 에는 `deployCost` (클러스터 전체의 시간당 제시 가격. API 는 이를 Pod 당으로 나눠 최소 USD 14.32 와 비교한다) 가 필요하고, 제시 가격과 관계없이 Pod 는 정가로 청구됐다.

| GPU 16장, `runpod/pytorch` 이미지 그대로 | 결과 |
|---|---|
| 노드 간 NCCL 네트워크 | **`ens1` 위의 `Socket`**: *"Failed to open libibverbs.so[.1]"* |
| all-reduce `busbw`, 1 GiB | **0.32 GB/s** (1단계 NVLink A100 2장: 201 GB/s) |
| DDP, GPU 1장 → 16장 | 23,497 → **1,105 samples/s** (스텝 10.9 ms → 3,705 ms) |

- **이미지에 RDMA 사용자 공간 라이브러리가 없어서** NCCL 이 경고 없이 `ens1` 의 TCP 로 내려갔고, 작업은 그대로 끝났다. GPU 16장이 1장보다 21배 느렸다. 노드마다 Mellanox HCA 가 12개 있었고, Runpod 은 이미 `NCCL_IB_HCA` 를 GPU 옆의 8개로 설정해 두었다.
- **Ubuntu 의 `libibverbs1` 을 설치하는 것만으로는 부족했다.** 그러자 NCCL 은 HCA 8개 모두에서 GPU Direct RDMA 와 함께 `IB` 를 골랐지만, 모든 HCA 가 *"local catastrophic error"* 를 냈고 all-reduce 는 10분 동안 진척이 없어 중단했다.
- 다중 노드 수치를 믿기 전에 NCCL 로그에서 `Using network IB` 를 확인한다. 콘솔의 클러스터 템플릿은 별도 이미지 `runpod/pytorch:1.0.7-cu1300-torch291-ubuntu2404-cluster` 를 쓰며, 다음 실행은 이 이미지로 한다.

자세한 내용과 원본 로그: [실습 README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#2단계-실행--infiniband-대신-소켓).

### 클러스터용 이미지에서도 InfiniBand 실패

`cluster.py` 가 하루를 기다려 2026-11-08 에 클러스터용 이미지(`…-ubuntu2404-cluster`, NCCL 2.27.7)로 다시 돌았다. 한국 시간 22:28 에 클러스터가 만들어졌고 50초 뒤 SSH 가 열렸다. 이번에는 NCCL 이 200 Gb/s InfiniBand HCA 8개를 찾고 큐 페어를 연결했으며, DMA-BUF 를 통한 GPU Direct RDMA 와 함께 `Using network IB` 를 남겼다. 22:30 첫 all-reduce 에서 두 노드의 모든 HCA 가 10초 안에 *"local catastrophic error"* 를 냈다. 그 뒤로는 아무것도 진행되지 않아 40분 제한에 걸렸고, 감시 프로세스가 75분에 클러스터를 지웠다 (과금은 약 22:33 에 이미 멈춰 USD 2.06, 두 클러스터 합계 USD 15.91).

<figure class="shot"><a href="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}" alt="NCCL 로그: Using network IB 와 GDRDMA 뒤 모든 HCA 에서 local catastrophic error" loading="lazy" width="1400" height="480"></a><figcaption>재실행의 NCCL 로그 (발췌): IB 와 GPU Direct RDMA 는 제대로 잡혔고, 이어서 두 노드의 HCA 8개 모두에서 같은 치명 이벤트가 났다.</figcaption></figure>

- **이미지 탓이 아니다.** Ubuntu 의 `libibverbs` 를 쓴 첫 실행도 똑같이 실패했다.
- **원인: 호스트 하드웨어 장애 (Runpod 지원팀, 2026-11-09).** 두 시각 (2026-11-07 약 13:09 UTC, 2026-11-08 약 13:30 UTC) 모두 각 호스트에서 치명적인 PCIe 오류가 나 GPU, NVSwitch, 스토리지, InfiniBand 카드 전부가 한꺼번에 끊겼다. *"local catastrophic error"* 는 그때 HCA 가 떨어져 나가며 남긴 줄이다. NCCL 설정, InfiniBand 설정, 이미지 탓이 아니며, 지원팀은 이 일 때문에 `NCCL_NET_GDR_LEVEL=LOC` 같은 NCCL 설정을 바꾸지 말라고 했다. 해당 머신은 서비스에서 빠졌다.
- **앞서 한 추측은 틀렸다.** 로그를 GPU Direct RDMA 실패로 읽었었다 (컨테이너의 `libmlx5` 에 `mlx5dv_reg_dmabuf_mr` 가 없음). 그 메시지는 사실이지만 이번 실패와는 관계없다.
- **호스트 장애는 멈춤처럼 보인다.** 아무것도 오류로 끝나지 않는다. Runpod 은 장애를 감지해 몇 분 안에 머신을 서비스에서 빼고 그때 과금을 멈추지만 (두 클러스터에서 장애 뒤 몫은 약 USD 4.92), 알림은 보내지 않는다.
- **같은 호스트 그룹.** 두 클러스터는 한 A100 SXM 호스트 그룹의 서로 다른 머신 쌍을 썼고, 네 대 모두 같은 장애를 내 서비스에서 빠졌다.
- **Runpod 이 권하는 점검.** 시작 직후 노드마다 `nvidia-smi` (GPU 8장) 와 `ibv_devinfo` (모든 포트 `PORT_ACTIVE`), 이어서 작은 메시지로 두 노드에 걸친 `all_reduce_perf` 를 짧게. 실행 중에는 `init_process_group` 에 `timeout=timedelta(minutes=5)`. 장애는 나중에도 나므로 (이번에는 1.5분 뒤와 16분 뒤) 이 제한이 가장 중요하다.
- **실패로 기록한다.** 2026-11-08 기준 이 사이트에는 Runpod Instant Cluster 의 다중 노드 대역폭 수치가 없다 ([#52](https://github.com/litkhai/runpod-hols/issues/52)).

시간표와 로그 발췌: [실습 README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#2단계-재실행--클러스터용-이미지-infiniband-실패).

### 검토 중인 실습

| 실습 | 내용 |
|---|---|
| 01-pytorch-distributed | 1단계 완료. 2단계는 소켓으로 1회 실행, RDMA 이미지로 재실행 남음 |
| 02-slurm-cluster | 관리형 Slurm 클러스터 배포 및 잡 제출 |
| 03-axolotl-finetune | Axolotl 을 이용한 다중 노드 LLM 파인튜닝 |

### 참조 자료

[Overview](https://docs.runpod.io/instant-clusters) ·
[PyTorch](https://docs.runpod.io/instant-clusters/pytorch) ·
[Slurm](https://docs.runpod.io/instant-clusters/slurm-clusters) ·
[Axolotl](https://docs.runpod.io/instant-clusters/axolotl) ·
[Configuration](https://docs.runpod.io/instant-clusters/configuration) ·
[Scaling](https://docs.runpod.io/instant-clusters/scale-clusters) ·
[Observability](https://docs.runpod.io/instant-clusters/cluster-observability) ·
[pytorch-cluster 이미지](https://github.com/runpod/containers/tree/main/official-templates/pytorch-cluster)

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

<div class="note" markdown="1">
**状态：实验 01 第 1 阶段已完成，第 2 阶段运行过一次（2026-11-07）。** 2 × 8 A100 SXM 集群运行了 35 分钟，但在默认 PyTorch 镜像中 NCCL 无法使用 InfiniBand；用支持 RDMA 的镜像重跑仍待完成（[#52](https://github.com/litkhai/runpod-hols/issues/52)）。
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) 是 Runpod 的多节点产品：带高速互连的全托管集群，用于分布式训练和大规模推理。

| 属性 | 值 |
|---|---|
| GPU | B300, B200, H200, H100 SXM, A100 SXM（控制台，2026-11-07） |
| 集群规模 | 2 个 Pod 起，每个 Pod 8 块 GPU；表单滑块最多 32 个 Pod |
| 互连 | 节点间 1600 Gbps（A100）到 6400 Gbps（B300），以 `ens1`–`ens8` 暴露 |
| 最小集群价格 | A100 SXM 每 GPU 小时 USD 2.15 = 每小时 USD 34.37；H100 SXM USD 4.79 = 每小时 USD 76.61 |
| 框架 | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### 实验 01 — torchrun 与 NCCL

[`cluster/01-pytorch-distributed`](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed) 测量 GPU 之间交换梯度的速度，以及它对数据并行训练的影响。同一个 `run.sh` 既在一台多 GPU Pod 上运行（第 1 阶段），也在集群的每个节点上运行（第 2 阶段）：拓扑、NCCL all-reduce 扫描（1 MiB – 1 GiB），然后用 `DistributedDataParallel` 在 1 块 GPU 和全部 GPU 上训练一个 1.01 亿参数的模型。

```bash
cd cluster/01-pytorch-distributed
python3 lab.py create                    # 2 块 RTX 4090；A100 用 --gpu "NVIDIA A100-SXM4-80GB"
python3 lab.py push && python3 lab.py run 2x4090 && python3 lab.py pull
python3 lab.py delete
```

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}" alt="选择 RTX 4090、GPU count 2 的 Pod 部署表单，每小时 USD 1.78" loading="lazy" width="1400" height="998"></a><figcaption>部署表单：多 GPU Pod 就是一张卡加上 GPU 数量。实验通过 <code>POST /pods</code> 的 <code>gpuCount: 2</code> 做同样的事。</figcaption></figure>

### 第 1 阶段结果 — 一台 Pod，两块 GPU

| | 2 块 RTX 4090 | 2 块 A100 SXM 80GB |
|---|---|---|
| 价格 | USD 1.78/hr | USD 3.58/hr |
| 连接（`nvidia-smi topo -m`） | `SYS`：跨两个 NUMA 节点的 PCIe | `NV12`：12 条 NVLink |
| NCCL 传输 | `SHM` 经主机内存 | `P2P` GPU 直连 |
| all-reduce `busbw`，1 GiB | **15.6 GB/s** | **201 GB/s** |
| DDP，1 块 GPU | 每秒 39,453 样本 | 每秒 23,132 样本 |
| DDP，2 块 GPU | 每秒 16,244 样本 | 每秒 41,871 样本 |
| 扩展效率 | **0.21** | **0.91** |

- **两块 RTX 4090 的训练速度比一块慢 2.4 倍。** 每步要 all-reduce 约 400 MB 梯度：在 15.6 GB/s 下约 26 ms，而计算只需 6.5 ms。GeForce 卡没有 GPU 间 P2P，NCCL 只能经主机内存中转。
- **A100 双卡的扩展效率为 91%**：经 NVLink 传 400 MB 约 2 ms。
- **控制台的 GPU 利用率看不出这一点。** 两块 4090 都显示 100%，但每步大部分时间在等传输；NCCL 内核在等待时也占着 GPU。
- 这里单块 A100 比单块 4090 慢，是因为模型跑的是纯 fp32（TF32 关闭，PyTorch 默认）。按每美元计算，这个模型用一块 RTX 4090 比两种双卡组合都划算。

差距为何如此之大：环形 all-reduce 每一步每块 GPU 都要搬运 2(n−1)/n 的梯度，所以设定上限的是链路而不是 GPU，而 `SYS` 还是 `NV12` 决定了你落在哪一侧。具体计算，以及为什么张量并行绝不能离开 NVLink 域，见 [GPU Topology → 用数字说话]({{ '/readings/gpu-topology/#in-numbers-zh' | relative_url }})；规模估算和成本见 [GPU 与 LLM 基础]({{ '/readings/gpu-llm-basics/' | relative_url }})。

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}" alt="Pod Telemetry 标签：两块 RTX 4090 利用率 100%" loading="lazy" width="1400" height="998"></a><figcaption>2 块 RTX 4090 运行时的 Telemetry：两块 GPU 都是 100%，训练速度却只有理想值的五分之一。</figcaption></figure>

第 1 阶段花费约 USD 0.40（Pod 运行 7 分钟和 3 分钟）。

**一台 Pod 中的 4 块 H100 SXM**（2026-11-08；没有集群库存时，单台 Pod 有库存）：

| 2026-11-08，US-NE-1 | 4 块 H100 SXM 80GB |
|---|---|
| 价格 | 每小时 USD 15.96 |
| 连接（`topo -m`） | `NV18`：每对之间 18 条 NVLink |
| all-reduce `busbw`，1 MiB / 1 GiB | 11.1 / **356.3 GB/s** |
| DDP，1 块 GPU | 54,981 samples/s（每步 4.7 ms） |
| DDP，4 块 GPU | 179,442 samples/s（每步 5.7 ms） |
| 扩展效率（4 块 / 1 块 × 4） | **0.82** |

连接是两块 A100 的 1.8 倍，单块 H100 在这里是单块 A100 的 2.4 倍，但扩展效率降到 0.82：计算 4.7 ms 对 all-reduce 约 1 ms，GPU 越快，连接越起决定作用。这是与集群比较的节点内上限——第 2 阶段的 Socket 运行在节点间只有 0.32 GB/s。11.5 分钟约 USD 3。

### 第 2 阶段 — Instant Cluster

集群可以在控制台创建（**Clusters → Create cluster**），也可以用 GraphQL 的 `createCluster` / `deleteCluster`；REST API 没有集群端点。表单按小时显示整个集群的价格，并把每种类型标为 Available 或 Unavailable。2026-11-07 所有类型都是 **Unavailable**，而同一时间单台 A100 SXM 和 H100 SXM Pod 可以部署。表单从 GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }` 读取，Unavailable 时返回 `null`。当天晚上 A100 SXM 在韩国时间约 19:29–19:36 显示 Available，到 19:46 又消失了；因此本实验用脚本等待库存，通过 GraphQL 创建集群，在两个节点上运行，最迟 75 分钟后删除（[`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)）。

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster 表单：B300、B200、H200 SXM、H100 SXM 均为 Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster，2026-11-07：每个 Pod 8 块 GPU，按 GPU 小时和集群小时计价，所有类型 Unavailable。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="Billing 页面显示每小时 USD 80 的花费速率上限" loading="lazy" width="1400" height="998"></a><figcaption>Billing 页面显示该账户的<strong>花费速率上限为每小时 USD 80</strong>。最小的 A100 集群（每小时 USD 34.37）和 H100 集群（USD 76.61）在限额内；H200（USD 101.57）和 B200（USD 153.41）则会超出——这就是文档所说的“默认花费限额”。</figcaption></figure>

### 走 Socket 而不是 InfiniBand

A100 SXM 在韩国时间 21:42 再次出现；`cluster.py` 在 21:48 创建集群，114 秒后两个节点都能 SSH，`run.sh` 在 21:50–22:09 运行，22:23 删除集群：Runpod 实际收费 USD 13.86：故障主机在 22:15 停止服务时计费就停止了（见下文）。`createCluster` 需要 `deployCost`（整个集群每小时的出价；API 按 Pod 拆分后与最低价 USD 14.32 比较），而无论出价多少，Pod 都按标价计费。

| 16 块 GPU，`runpod/pytorch` 镜像原样 | 结果 |
|---|---|
| 节点间 NCCL 网络 | **`ens1` 上的 `Socket`**：*"Failed to open libibverbs.so[.1]"* |
| all-reduce `busbw`，1 GiB | **0.32 GB/s**（第 1 阶段 NVLink 两块 A100：201 GB/s） |
| DDP，1 块 → 16 块 GPU | 23,497 → **1,105 samples/s**（每步 10.9 ms → 3,705 ms） |

- **镜像中没有 RDMA 用户态库**，NCCL 在没有警告的情况下退回 `ens1` 上的 TCP，任务照样完成：16 块 GPU 比 1 块慢 21 倍。每个节点有 12 个 Mellanox HCA，Runpod 已把 `NCCL_IB_HCA` 设为靠近 GPU 的 8 个。
- **只从 Ubuntu 安装 `libibverbs1` 不够。** 之后 NCCL 在全部 8 个 HCA 上选择了带 GPU Direct RDMA 的 `IB`，随即每个 HCA 都报告 *"local catastrophic error"*；all-reduce 十分钟没有进展，于是中止。
- 相信任何多节点数据之前，先在 NCCL 日志中确认 `Using network IB`。控制台的集群模板使用单独的镜像 `runpod/pytorch:1.0.7-cu1300-torch291-ubuntu2404-cluster`，下一次运行将使用它。

详情与原始日志：[实验 README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#stage-2-run--sockets-instead-of-infiniband)。

### 集群镜像上 InfiniBand 也失败

`cluster.py` 等了一天，于 2026-11-08 用集群镜像（`…-ubuntu2404-cluster`，NCCL 2.27.7）再次运行。集群在韩国时间 22:28 创建，50 秒后 SSH 可用。这一次 NCCL 找到了 8 个 200 Gb/s InfiniBand HCA，建立了队列对，并记录了 `Using network IB`，通过 DMA-BUF 使用 GPU Direct RDMA。22:30 第一次 all-reduce 时，两个节点上的每个 HCA 都在十秒内报告 *"local catastrophic error"*。此后没有任何进展：运行触发 40 分钟超时，看门狗在第 75 分钟删除了集群（计费已在约 22:33 停止：USD 2.06，两次集群合计 USD 15.91）。

<figure class="shot"><a href="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}" alt="NCCL 日志：Using network IB 和 GDRDMA 之后，每个 HCA 都出现 local catastrophic error" loading="lazy" width="1400" height="480"></a><figcaption>重跑的 NCCL 日志（节选）：IB 与 GPU Direct RDMA 均正确建立，随后两个节点的 8 个 HCA 全部出现同样的致命事件。</figcaption></figure>

- **不是镜像的问题。** 使用 Ubuntu `libibverbs` 的第一次运行以同样的方式失败。
- **原因：主机硬件故障（Runpod 支持，2026-11-09）。** 在两个时间点（2026-11-07 约 13:09 UTC，2026-11-08 约 13:30 UTC），每台主机都发生了致命的 PCIe 错误，所有设备同时断开：GPU、NVSwitch、存储和全部 InfiniBand 卡。*"local catastrophic error"* 就是 HCA 在这次故障中掉线时留下的。与 NCCL 配置、InfiniBand 设置或镜像无关；支持人员建议不要因此修改 `NCCL_NET_GDR_LEVEL=LOC` 等 NCCL 设置。这些机器已停止服务。
- **之前的推测是错的。** 日志曾被解读为 GPU Direct RDMA 失败（容器的 `libmlx5` 没有 `mlx5dv_reg_dmabuf_mr`）。该消息确实存在，但与这次失败无关。
- **主机故障看起来像卡住。** 没有任何进程以错误退出。Runpod 会检测到故障，在几分钟内让机器停止服务并同时停止计费（两次集群在故障之后的费用约 USD 4.92），但不会通知用户。
- **同一组主机。** 两次集群使用同一组 A100 SXM 主机中不同的两对机器；四台都出现同样的故障，已全部停止服务。
- **Runpod 建议的检查。** 启动后在每个节点运行 `nvidia-smi`（8 张 GPU）和 `ibv_devinfo`（每个端口 `PORT_ACTIVE`），再用小消息跨节点短跑一次 `all_reduce_perf`。运行中在 `init_process_group` 里设置 `timeout=timedelta(minutes=5)`。故障也可能稍后才出现（这次分别在 1.5 分钟和 16 分钟后），所以这个超时最重要。
- **记录为失败。** 截至 2026-11-08，本站没有 Runpod Instant Cluster 的多节点带宽数据（[#52](https://github.com/litkhai/runpod-hols/issues/52)）。

时间线与日志节选：[实验 README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#stage-2-rerun--the-cluster-image-infiniband-fails)。

### 可能的实验

| 实验 | 内容 |
|---|---|
| 01-pytorch-distributed | 第 1 阶段完成；第 2 阶段以 Socket 运行过一次，待用支持 RDMA 的镜像重跑 |
| 02-slurm-cluster | 部署托管 Slurm 集群并提交作业 |
| 03-axolotl-finetune | 用 Axolotl 进行多节点 LLM 微调 |

### 参考

[Overview](https://docs.runpod.io/instant-clusters) ·
[PyTorch](https://docs.runpod.io/instant-clusters/pytorch) ·
[Slurm](https://docs.runpod.io/instant-clusters/slurm-clusters) ·
[Axolotl](https://docs.runpod.io/instant-clusters/axolotl) ·
[Configuration](https://docs.runpod.io/instant-clusters/configuration) ·
[Scaling](https://docs.runpod.io/instant-clusters/scale-clusters) ·
[Observability](https://docs.runpod.io/instant-clusters/cluster-observability) ·
[pytorch-cluster 镜像](https://github.com/runpod/containers/tree/main/official-templates/pytorch-cluster)

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

<div class="note" markdown="1">
**状態：ラボ 01 のステージ 1 完了、ステージ 2 を 1 回実行（2026-11-07）。** A100 SXM 2 × 8 基のクラスタを 35 分動かしましたが、標準の PyTorch イメージでは NCCL が InfiniBand を使えませんでした。RDMA 対応イメージでの再実行が残っています（[#52](https://github.com/litkhai/runpod-hols/issues/52)）。
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) は Runpod のマルチノード製品です。分散学習と大規模推論のための、高速インターコネクトを備えたフルマネージドのクラスタです。

| 項目 | 値 |
|---|---|
| GPU | B300, B200, H200, H100 SXM, A100 SXM（コンソール、2026-11-07） |
| クラスタ規模 | 2 Pod 以上、Pod あたり GPU 8 基。フォームのスライダーは 32 Pod まで |
| インターコネクト | ノード間 1600 Gbps（A100）〜 6400 Gbps（B300）、`ens1`–`ens8` として公開 |
| 最小クラスタの価格 | A100 SXM は GPU 時間あたり USD 2.15 = 時間あたり USD 34.37、H100 SXM は USD 4.79 = 時間あたり USD 76.61 |
| フレームワーク | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### ラボ 01 — torchrun と NCCL

[`cluster/01-pytorch-distributed`](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed) は、GPU 同士が勾配をどれだけ速くやり取りできるか、それがデータ並列学習にどう効くかを測ります。同じ `run.sh` をマルチ GPU の Pod 1 台（ステージ 1）とクラスタの全ノード（ステージ 2）で実行します。トポロジー、NCCL all-reduce のスイープ（1 MiB – 1 GiB）、続いて 1 億 100 万パラメータのモデルを `DistributedDataParallel` で GPU 1 基と全 GPU で学習させます。

```bash
cd cluster/01-pytorch-distributed
python3 lab.py create                    # RTX 4090 2 基。A100 は --gpu "NVIDIA A100-SXM4-80GB"
python3 lab.py push && python3 lab.py run 2x4090 && python3 lab.py pull
python3 lab.py delete
```

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-deploy-2gpu.webp' | relative_url }}" alt="RTX 4090 と GPU count 2 を選んだ Pod デプロイ画面、時間あたり USD 1.78" loading="lazy" width="1400" height="998"></a><figcaption>デプロイ画面：マルチ GPU の Pod はカード 1 枚と GPU 数で決まります。ラボは同じことを <code>POST /pods</code> の <code>gpuCount: 2</code> で行います。</figcaption></figure>

### ステージ 1 の結果 — Pod 1 台、GPU 2 基

| | RTX 4090 × 2 | A100 SXM 80GB × 2 |
|---|---|---|
| 価格 | USD 1.78/hr | USD 3.58/hr |
| 接続（`nvidia-smi topo -m`） | `SYS`：2 つの NUMA ノードにまたがる PCIe | `NV12`：NVLink 12 本 |
| NCCL の転送 | `SHM` ホストメモリ経由 | `P2P` GPU 間で直接 |
| all-reduce `busbw`、1 GiB | **15.6 GB/s** | **201 GB/s** |
| DDP、GPU 1 基 | 毎秒 39,453 サンプル | 毎秒 23,132 サンプル |
| DDP、GPU 2 基 | 毎秒 16,244 サンプル | 毎秒 41,871 サンプル |
| スケーリング効率 | **0.21** | **0.91** |

- **RTX 4090 2 基の学習は 1 基より 2.4 倍遅くなりました。** 各ステップで約 400 MB の勾配を all-reduce し、15.6 GB/s では約 26 ms かかります。計算は 6.5 ms でした。GeForce には GPU 間 P2P がないため、NCCL はホストメモリを経由しました。
- **A100 2 基は 91% でスケールしました**。NVLink なら 400 MB は約 2 ms です。
- **コンソールの GPU 使用率には表れませんでした。** 4090 は 2 基とも 100% でしたが、各ステップの大半は転送待ちでした。NCCL のカーネルは待っている間も GPU を占有します。
- ここで A100 1 基が 4090 1 基より遅いのは、モデルが素の fp32（TF32 オフ、PyTorch の既定）だからです。ドルあたりでは、このモデルは RTX 4090 1 基がどちらの 2 基構成よりも有利でした。

差がこれほど大きい理由：リング all-reduce は毎ステップ GPU あたり勾配の 2(n−1)/n を転送するので、上限を決めるのは GPU ではなくリンクです。そして `SYS` か `NV12` かが、その上限のどちら側に来るかを決めます。計算の詳細と、テンソル並列が決して NVLink ドメインの外に出てはならない理由は [GPU Topology → 数値で見る]({{ '/readings/gpu-topology/#in-numbers-ja' | relative_url }})にあります。サイジングとコストは [GPU と LLM の基礎]({{ '/readings/gpu-llm-basics/' | relative_url }})にあります。

<figure class="shot"><a href="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/pod-telemetry-2x4090.webp' | relative_url }}" alt="Pod の Telemetry タブ：RTX 4090 2 基とも使用率 100%" loading="lazy" width="1400" height="998"></a><figcaption>RTX 4090 × 2 の実行中の Telemetry：2 基とも 100% なのに、学習速度は理想の 5 分の 1 でした。</figcaption></figure>

ステージ 1 の費用は約 USD 0.40（Pod 7 分と 3 分）。

**Pod 1 台に H100 SXM 4 基**（2026-11-08。クラスタの在庫がないときも単体 Pod には在庫がありました）：

| 2026-11-08、US-NE-1 | H100 SXM 80GB 4 基 |
|---|---|
| 価格 | 時間あたり USD 15.96 |
| 接続（`topo -m`） | `NV18`：すべてのペア間に NVLink 18 本 |
| all-reduce `busbw`、1 MiB / 1 GiB | 11.1 / **356.3 GB/s** |
| DDP、GPU 1 基 | 54,981 samples/s（ステップ 4.7 ms） |
| DDP、GPU 4 基 | 179,442 samples/s（ステップ 5.7 ms） |
| スケーリング効率（4 基 / 1 基 × 4） | **0.82** |

接続は A100 2 基の 1.8 倍、H100 1 基はここで A100 1 基の 2.4 倍でしたが、効率は 0.82 に下がりました。計算 4.7 ms に対し all-reduce 約 1 ms で、GPU が速いほど接続が性能を左右します。これがクラスタと比べるべきノード内の上限です。ステージ 2 のソケット実行はノード間 0.32 GB/s でした。11.5 分で約 USD 3。

### ステージ 2 — Instant Cluster

クラスタはコンソール（**Clusters → Create cluster**）か、GraphQL の `createCluster` / `deleteCluster` で作成します。REST API にクラスタのエンドポイントはありません。フォームはクラスタ全体の時間あたり価格と、種別ごとの Available／Unavailable を表示します。2026-11-07 はすべての種別が **Unavailable** で、同じ時刻に A100 SXM と H100 SXM の単体 Pod はデプロイできました。フォームはこれを GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }` から読み、Unavailable なら `null` が返ります。同じ日の夜、A100 SXM は韓国時間 19:29〜19:36 ごろ Available になり、19:46 には消えていました。そこでこのラボはスクリプトで在庫を待ち、GraphQL でクラスタを作成して両ノードで実行し、遅くとも 75 分後に削除します（[`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)）。

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster 画面：B300、B200、H200 SXM、H100 SXM がすべて Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster、2026-11-07：Pod あたり GPU 8 基、GPU 時間あたりとクラスタ時間あたりの価格、すべて Unavailable。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="時間あたり USD 80 の支出レート上限を示す Billing 画面" loading="lazy" width="1400" height="998"></a><figcaption>Billing にこのアカウントの<strong>支出レート上限、時間あたり USD 80</strong> が表示されます。最小の A100 クラスタ（時間あたり USD 34.37）と H100 クラスタ（USD 76.61）は収まり、H200（USD 101.57）と B200（USD 153.41）は超えます。ドキュメントのいう「既定の支出上限」がこれです。</figcaption></figure>

### InfiniBand ではなくソケット

A100 SXM は韓国時間 21:42 に再び出ました。`cluster.py` が 21:48 にクラスタを作成し、114 秒後に両ノードで SSH が開き、`run.sh` が 21:50〜22:09 に実行され、22:23 にクラスタを削除しました。Runpod の請求額は USD 13.86 です。障害のあったホストが 22:15 にサービスから外された時点で課金が止まりました（後述）。`createCluster` には `deployCost`（クラスタ全体の時間あたりの提示価格。API は Pod ごとに割って最低価格 USD 14.32 と比較）が必要で、提示価格にかかわらず Pod は定価で請求されました。

| GPU 16 基、`runpod/pytorch` イメージそのまま | 結果 |
|---|---|
| ノード間の NCCL ネットワーク | **`ens1` 上の `Socket`**：*"Failed to open libibverbs.so[.1]"* |
| all-reduce `busbw`、1 GiB | **0.32 GB/s**（ステージ 1 の NVLink A100 2 基：201 GB/s） |
| DDP、GPU 1 基 → 16 基 | 23,497 → **1,105 samples/s**（ステップ 10.9 ms → 3,705 ms） |

- **イメージに RDMA のユーザー空間ライブラリがなく**、NCCL は警告なしに `ens1` の TCP へフォールバックし、ジョブはそのまま完了しました。GPU 16 基が 1 基より 21 倍遅くなりました。各ノードには Mellanox HCA が 12 個あり、Runpod は `NCCL_IB_HCA` を GPU 近くの 8 個に設定済みでした。
- **Ubuntu の `libibverbs1` を入れるだけでは足りませんでした。** すると NCCL は 8 個すべての HCA で GPU Direct RDMA 付きの `IB` を選びましたが、どの HCA も *"local catastrophic error"* を報告し、all-reduce は 10 分間進まなかったため中止しました。
- マルチノードの数値を信じる前に、NCCL のログで `Using network IB` を確認してください。コンソールのクラスタ用テンプレートは別のイメージ `runpod/pytorch:1.0.7-cu1300-torch291-ubuntu2404-cluster` を使っており、次回はこれで実行します。

詳細と生ログ：[ラボの README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#stage-2-run--sockets-instead-of-infiniband)。

### クラスタ用イメージでも InfiniBand が失敗

`cluster.py` は 1 日待って、2026-11-08 にクラスタ用イメージ（`…-ubuntu2404-cluster`、NCCL 2.27.7）で再実行しました。クラスタは韓国時間 22:28 に作成され、50 秒後に SSH が開きました。今回は NCCL が 200 Gb/s の InfiniBand HCA を 8 個見つけてキューペアを接続し、DMA-BUF 経由の GPU Direct RDMA とともに `Using network IB` を記録しました。22:30 の最初の all-reduce で、両ノードのすべての HCA が 10 秒以内に *"local catastrophic error"* を出しました。その後は何も進まず、実行は 40 分のタイムアウトに達し、監視プロセスが 75 分でクラスタを削除しました（課金は約 22:33 に既に止まっており USD 2.06、2 回のクラスタで USD 15.91）。

<figure class="shot"><a href="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/ib-catastrophic-error.webp' | relative_url }}" alt="NCCL ログ：Using network IB と GDRDMA のあと、すべての HCA で local catastrophic error" loading="lazy" width="1400" height="480"></a><figcaption>再実行の NCCL ログ（抜粋）：IB と GPU Direct RDMA は正しく設定され、その直後に両ノードの 8 個の HCA すべてで同じ致命的イベントが起きました。</figcaption></figure>

- **イメージのせいではありません。** Ubuntu の `libibverbs` を使った最初の実行も同じように失敗しました。
- **原因：ホストのハードウェア障害（Runpod サポート、2026-11-09）。** 2 つの時刻（2026-11-07 約 13:09 UTC、2026-11-08 約 13:30 UTC）のどちらでも、各ホストで致命的な PCIe エラーが起き、GPU、NVSwitch、ストレージ、すべての InfiniBand カードが一度に切断されました。*"local catastrophic error"* は、その障害で HCA が外れたときの記録です。NCCL の設定、InfiniBand の設定、イメージのせいではなく、サポートはこの件を理由に `NCCL_NET_GDR_LEVEL=LOC` などの NCCL 設定を変えないよう勧めています。該当マシンはサービスから外されました。
- **以前の推測は誤りでした。** ログを GPU Direct RDMA の失敗と読んでいました（コンテナの `libmlx5` に `mlx5dv_reg_dmabuf_mr` がない）。このメッセージ自体は本当ですが、今回の失敗とは無関係です。
- **ホスト障害は停止のように見えます。** どのプロセスもエラーで終了しません。Runpod は障害を検知して数分以内にマシンをサービスから外し、その時点で課金も止めます（2 回のクラスタで障害後の分は約 USD 4.92）。ただし通知は届きません。
- **同じホストグループ。** 2 回のクラスタは、同じ A100 SXM ホストグループの別々のマシン 2 台ずつを使いました。4 台とも同じ障害を起こし、サービスから外されています。
- **Runpod が勧めるチェック。** 起動直後に各ノードで `nvidia-smi`（GPU 8 枚）と `ibv_devinfo`（すべてのポートが `PORT_ACTIVE`）、続いて小さなメッセージでノード間の `all_reduce_perf` を短く実行します。実行中は `init_process_group` に `timeout=timedelta(minutes=5)` を指定します。障害は後から起きることもあるため（今回は 1.5 分後と 16 分後）、このタイムアウトが最も重要です。
- **失敗として記録します。** 2026-11-08 時点で、このサイトには Runpod Instant Cluster のマルチノード帯域の数値がありません（[#52](https://github.com/litkhai/runpod-hols/issues/52)）。

タイムラインとログの抜粋：[ラボの README](https://github.com/litkhai/runpod-hols/tree/main/cluster/01-pytorch-distributed#stage-2-rerun--the-cluster-image-infiniband-fails)。

### 候補のラボ

| ラボ | 内容 |
|---|---|
| 01-pytorch-distributed | ステージ 1 完了。ステージ 2 は Socket で 1 回実行、RDMA 対応イメージでの再実行待ち |
| 02-slurm-cluster | マネージド Slurm クラスタをデプロイしてジョブを投入 |
| 03-axolotl-finetune | Axolotl によるマルチノードの LLM ファインチューニング |

### 参考資料

[Overview](https://docs.runpod.io/instant-clusters) ·
[PyTorch](https://docs.runpod.io/instant-clusters/pytorch) ·
[Slurm](https://docs.runpod.io/instant-clusters/slurm-clusters) ·
[Axolotl](https://docs.runpod.io/instant-clusters/axolotl) ·
[Configuration](https://docs.runpod.io/instant-clusters/configuration) ·
[Scaling](https://docs.runpod.io/instant-clusters/scale-clusters) ·
[Observability](https://docs.runpod.io/instant-clusters/cluster-observability) ·
[pytorch-cluster イメージ](https://github.com/runpod/containers/tree/main/official-templates/pytorch-cluster)

</div>
