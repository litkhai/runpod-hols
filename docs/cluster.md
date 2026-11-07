---
layout: default
title: Cluster
permalink: /cluster/
---

# Cluster

<div class="lang" data-lang="en" markdown="1">

## English

<div class="note" markdown="1">
**Status: lab 01 stage 1 done (2026-11-07).** Stage 2, a 2-node Instant Cluster, waits for capacity: every cluster type was Unavailable on 2026-11-07 ([#52](https://github.com/litkhai/runpod-hols/issues/52)).
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

### Stage 2 — Instant Cluster

Clusters are created in the console (**Clusters → Create cluster**) or over GraphQL with `createCluster` / `deleteCluster`; the REST API has no cluster endpoints. The form prices the whole cluster per hour and marks each type Available or Unavailable. On 2026-11-07 every type was **Unavailable**, while single A100 SXM and H100 SXM Pods could be deployed at the same time. The form reads this from GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }`, which returns `null` for Unavailable. That evening A100 SXM showed Available from about 19:29 to 19:36 KST and was gone by 19:46, so this lab waits for stock with a script that creates the cluster through GraphQL, runs both nodes and deletes it after at most 75 minutes ([`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)).

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster form: B300, B200, H200 SXM and H100 SXM all Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster, 2026-11-07: 8 GPUs per Pod, price per GPU-hour and per cluster-hour, every type Unavailable.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="Billing page showing a spend rate limit of USD 80 per hour" loading="lazy" width="1400" height="998"></a><figcaption>Billing shows this account's <strong>spend rate limit, USD 80/hr</strong>. The smallest A100 cluster (USD 34.37/hr) and H100 cluster (USD 76.61/hr) fit under it; H200 (USD 101.57) and B200 (USD 153.41) would not — the "default spending limit" the docs mention.</figcaption></figure>

When capacity appears, run on each node:

```bash
git clone https://github.com/litkhai/runpod-hols && cd runpod-hols/cluster/01-pytorch-distributed
bash run.sh cluster-2x8xA100            # NUM_NODES, NODE_RANK, PRIMARY_ADDR come from Runpod; NCCL uses ens1
```

### Possible labs

| Lab | Contents |
|---|---|
| 01-pytorch-distributed | Stage 1 done; stage 2 (2 nodes × 8 A100, cap USD 50) waits for capacity |
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
**상태: 실습 01 의 1단계 완료 (2026-11-07).** 2단계인 노드 2개짜리 Instant Cluster 는 자리를 기다리고 있다. 2026-11-07 에는 모든 클러스터 종류가 Unavailable 이었다 ([#52](https://github.com/litkhai/runpod-hols/issues/52)).
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

### 2단계 — Instant Cluster

클러스터는 콘솔 (**Clusters → Create cluster**) 이나 GraphQL 의 `createCluster` / `deleteCluster` 로 만든다. REST API 에는 클러스터 엔드포인트가 없다. 화면은 클러스터 전체의 시간당 가격과 종류별 Available/Unavailable 을 보여준다. 2026-11-07 에는 모든 종류가 **Unavailable** 이었고, 같은 시각 A100 SXM, H100 SXM 단일 Pod 는 배포할 수 있었다. 화면은 이 값을 GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }` 로 읽으며, Unavailable 이면 `null` 이다. 같은 날 저녁 A100 SXM 이 한국 시간 약 19:29–19:36 에 Available 이었다가 19:46 에는 사라졌다. 그래서 이 실습은 스크립트로 재고를 기다려, GraphQL 로 클러스터를 만들고 두 노드에서 돌린 뒤 늦어도 75분 안에 지운다 ([`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)).

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster 화면: B300, B200, H200 SXM, H100 SXM 모두 Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster, 2026-11-07: Pod 당 GPU 8장, GPU 시간당과 클러스터 시간당 가격, 모든 종류 Unavailable.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="시간당 USD 80 의 지출 속도 한도를 보여주는 Billing 화면" loading="lazy" width="1400" height="998"></a><figcaption>Billing 화면에 이 계정의 <strong>지출 속도 한도, 시간당 USD 80</strong> 이 나온다. 가장 작은 A100 클러스터(시간당 USD 34.37)와 H100 클러스터(USD 76.61)는 그 안에 들어가고, H200(USD 101.57)과 B200(USD 153.41)은 넘는다. 문서가 말하는 "기본 지출 한도" 가 이것이다.</figcaption></figure>

자리가 나면 각 노드에서:

```bash
git clone https://github.com/litkhai/runpod-hols && cd runpod-hols/cluster/01-pytorch-distributed
bash run.sh cluster-2x8xA100            # NUM_NODES, NODE_RANK, PRIMARY_ADDR 는 Runpod 이 넣고, NCCL 은 ens1 사용
```

### 검토 중인 실습

| 실습 | 내용 |
|---|---|
| 01-pytorch-distributed | 1단계 완료. 2단계 (노드 2개 × A100 8장, 상한 USD 50) 는 자리 대기 |
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
**状态：实验 01 第 1 阶段已完成（2026-11-07）。** 第 2 阶段（2 节点 Instant Cluster）正在等待容量：2026-11-07 所有集群类型均为 Unavailable（[#52](https://github.com/litkhai/runpod-hols/issues/52)）。
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

### 第 2 阶段 — Instant Cluster

集群可以在控制台创建（**Clusters → Create cluster**），也可以用 GraphQL 的 `createCluster` / `deleteCluster`；REST API 没有集群端点。表单按小时显示整个集群的价格，并把每种类型标为 Available 或 Unavailable。2026-11-07 所有类型都是 **Unavailable**，而同一时间单台 A100 SXM 和 H100 SXM Pod 可以部署。表单从 GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }` 读取，Unavailable 时返回 `null`。当天晚上 A100 SXM 在韩国时间约 19:29–19:36 显示 Available，到 19:46 又消失了；因此本实验用脚本等待库存，通过 GraphQL 创建集群，在两个节点上运行，最迟 75 分钟后删除（[`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)）。

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster 表单：B300、B200、H200 SXM、H100 SXM 均为 Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster，2026-11-07：每个 Pod 8 块 GPU，按 GPU 小时和集群小时计价，所有类型 Unavailable。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="Billing 页面显示每小时 USD 80 的花费速率上限" loading="lazy" width="1400" height="998"></a><figcaption>Billing 页面显示该账户的<strong>花费速率上限为每小时 USD 80</strong>。最小的 A100 集群（每小时 USD 34.37）和 H100 集群（USD 76.61）在限额内；H200（USD 101.57）和 B200（USD 153.41）则会超出——这就是文档所说的“默认花费限额”。</figcaption></figure>

有容量时，在每个节点上运行：

```bash
git clone https://github.com/litkhai/runpod-hols && cd runpod-hols/cluster/01-pytorch-distributed
bash run.sh cluster-2x8xA100            # NUM_NODES、NODE_RANK、PRIMARY_ADDR 由 Runpod 设置；NCCL 走 ens1
```

### 可能的实验

| 实验 | 内容 |
|---|---|
| 01-pytorch-distributed | 第 1 阶段完成；第 2 阶段（2 节点 × 8 块 A100，上限 USD 50）等待容量 |
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
**状態：ラボ 01 のステージ 1 完了（2026-11-07）。** ステージ 2 の 2 ノード Instant Cluster は空きを待っています。2026-11-07 はすべてのクラスタ種別が Unavailable でした（[#52](https://github.com/litkhai/runpod-hols/issues/52)）。
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

### ステージ 2 — Instant Cluster

クラスタはコンソール（**Clusters → Create cluster**）か、GraphQL の `createCluster` / `deleteCluster` で作成します。REST API にクラスタのエンドポイントはありません。フォームはクラスタ全体の時間あたり価格と、種別ごとの Available／Unavailable を表示します。2026-11-07 はすべての種別が **Unavailable** で、同じ時刻に A100 SXM と H100 SXM の単体 Pod はデプロイできました。フォームはこれを GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }` から読み、Unavailable なら `null` が返ります。同じ日の夜、A100 SXM は韓国時間 19:29〜19:36 ごろ Available になり、19:46 には消えていました。そこでこのラボはスクリプトで在庫を待ち、GraphQL でクラスタを作成して両ノードで実行し、遅くとも 75 分後に削除します（[`cluster.py`](https://github.com/litkhai/runpod-hols/blob/main/cluster/01-pytorch-distributed/cluster.py)）。

<figure class="shot"><a href="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/instant-cluster-unavailable.webp' | relative_url }}" alt="Deploy Instant Cluster 画面：B300、B200、H200 SXM、H100 SXM がすべて Unavailable" loading="lazy" width="1400" height="998"></a><figcaption>Deploy Instant Cluster、2026-11-07：Pod あたり GPU 8 基、GPU 時間あたりとクラスタ時間あたりの価格、すべて Unavailable。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}"><img src="{{ '/assets/img/cluster/spend-rate-limit.webp' | relative_url }}" alt="時間あたり USD 80 の支出レート上限を示す Billing 画面" loading="lazy" width="1400" height="998"></a><figcaption>Billing にこのアカウントの<strong>支出レート上限、時間あたり USD 80</strong> が表示されます。最小の A100 クラスタ（時間あたり USD 34.37）と H100 クラスタ（USD 76.61）は収まり、H200（USD 101.57）と B200（USD 153.41）は超えます。ドキュメントのいう「既定の支出上限」がこれです。</figcaption></figure>

空きが出たら、各ノードで実行します。

```bash
git clone https://github.com/litkhai/runpod-hols && cd runpod-hols/cluster/01-pytorch-distributed
bash run.sh cluster-2x8xA100            # NUM_NODES、NODE_RANK、PRIMARY_ADDR は Runpod が設定。NCCL は ens1 を使う
```

### 候補のラボ

| ラボ | 内容 |
|---|---|
| 01-pytorch-distributed | ステージ 1 完了。ステージ 2（2 ノード × A100 8 基、上限 USD 50）は空き待ち |
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
