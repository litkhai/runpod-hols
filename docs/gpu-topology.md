---
layout: default
title: GPU Topology
permalink: /readings/gpu-topology/
---

# GPU Topology

<div class="lang" data-lang="en" markdown="1">

## English

NVLink and MIG decide two things about a GPU: how fast it can talk to its neighbours, and whether it can be split. Both are worth understanding on their own, independently of any provider.

What Runpod does with them comes second — and the two answers are opposite. NVLink is available but never configurable. MIG is available only as slices Runpod has already cut.

Concepts are from vendor documentation. The Runpod half is from the live GPU catalogue and the published REST OpenAPI spec; the hardware claims were run on one 2× A100 SXM Pod on 2026-11-05. Bare Metal was not rented and stays unverified.

## The concepts
{: #concepts }

### What NVLink is

A direct GPU-to-GPU link. Without it, one GPU reaches another by going out over PCIe, through the CPU and system memory, and back — a detour that becomes the bottleneck the moment GPUs have to exchange data every step.

| Path | Bidirectional bandwidth |
|---|---|
| NVLink 4 on H100 SXM — 18 lanes | 900 GB/s |
| PCIe 5.0 x16 | 128 GB/s |
| Practical peer-to-peer across a PCIe switch fabric | 50–100 GB/s |

Roughly 7× or more, and it is a different shape of connection: NVLink GPUs form a mesh, while PCIe routes through a central host bridge.

It matters in proportion to how chatty your parallelism is. Tensor parallelism exchanges activations at every layer and suffers most; data parallelism all-reduces gradients once per step; a single-GPU job never notices.

### What MIG is

Multi-Instance GPU cuts one physical card into **GPU Instances** that behave like separate smaller GPUs — dedicated SMs, dedicated memory, and their own fault domain, so one instance crashing does not take the others with it.

Profiles are named `<N>g.<M>gb`: `N` is how many compute slices the instance gets, `M` is its dedicated memory in GB. `1g.24gb` is one slice with 24GB; `7g` is the whole card. Inside a GPU Instance you can subdivide further into **Compute Instances**, which share that instance's memory but split its compute. Some fixed-function engines — copy, encode, decode, JPEG, OFA — still show up as shared.

This is what separates MIG from the other ways to share a card:

| | Memory isolation | Fault isolation |
|---|---|---|
| MIG | Yes, hardware-enforced | Yes |
| Time-slicing | No | No |
| CUDA MPS | No — an allocation cap at most | No |

That hardware isolation is the whole point — and the reason it cannot be set up from inside a container.

## How Runpod exposes them
{: #on-runpod }

### The short answer

| | Available? | Who controls it |
|---|---|---|
| **NVLink** | Yes, on SXM/NVL hardware | Nobody — it is a property of the machine you land on |
| **MIG** | Yes, as pre-cut SKUs | Runpod. You buy slices; you cannot cut them |

Both are *available* and neither is *configurable*. What you choose is a GPU type; the topology follows from it.

### What the API lets you control

`POST /pods` in the [published OpenAPI spec](https://rest.runpod.io/v1/openapi.json) has 33 properties. None mention interconnect, topology, NVLink, MIG, or partitioning. The GPU-related ones are `gpuTypeIds`, `gpuCount`, `gpuTypePriority`, `minRAMPerGPU` and `minVCPUPerGPU`.

`POST /endpoints` is narrower — it requires a `templateId` and carries no GPU-topology field at all. The whole REST surface is 23 paths, with nothing for builds, topology, or partitioning.

So the lever is SKU selection.

### NVLink — you get it by picking the right SKU

Runpod's catalogue returns 48 GPU types. The ones carrying NVLink are identifiable by name:

| GPU type | VRAM | Notes |
|---|---|---|
| B200 | 180GB | NVLink 5 — but the name does not say so |
| H200 NVL | 143GB | |
| H200 SXM | 141GB | |
| H100 NVL | 94GB | |
| A100 SXM | 80GB | |
| H100 SXM | 80GB | |
| A100 SXM 40GB | 40GB | |
| V100 SXM2 | 16GB | NVLink 2 |

And the ones that deliberately do not: **A100 PCIe** and **H100 PCIe** — same silicon, same VRAM, PCIe instead of NVLink.

<div class="warn" markdown="1">
**The name is a hint, not a contract.** `B200` carries NVLink and says nothing about it, while `A100 PCIe` and `A100 SXM` differ only in the suffix. Runpod exposes no field asserting topology, so the name is all you have before boot — and it is not enough.
</div>

### Verifying what you actually got

```bash
nvidia-smi topo -m
```

The legend, [from NVIDIA](https://docs.nvidia.com/deploy/nvidia-smi/index.html):

| Code | Meaning |
|---|---|
| `X` | Self |
| `NV#` | Connection traversing a bonded set of # NVLinks |
| `PIX` | Traversing a single PCIe switch |
| `PXB` | Traversing multiple PCIe switches, without the host bridge |
| `PHB` | Traversing a PCIe host bridge (typically the CPU) |
| `NODE` | Traversing PCIe plus the interconnect between host bridges in one NUMA node |
| `SYS` | Traversing PCIe plus the SMP interconnect between NUMA nodes (QPI/UPI) |

`NV#` between every GPU pair is what you want. Anything from `PIX` downwards means your all-reduce traffic is crossing PCIe, and `SYS` means it is also crossing sockets.

Run on a Runpod Secure Cloud Pod, 2× `NVIDIA A100-SXM4-80GB`, driver 595.91.07, 2026-11-05 ([#14](https://github.com/litkhai/runpod-hols/issues/14)):

```
	GPU0	GPU1	NIC0 … NIC9	CPU Affinity	NUMA Affinity
GPU0	 X 	NV12	SYS … NODE	64-127	1
GPU1	NV12	 X 	SYS … NODE	64-127	1
```

`NV12` — twelve bonded NVLinks, and `nvidia-smi nvlink -s` listed links 0–11 at 25 GB/s each. A 1 GiB `torch` copy from GPU 0 to GPU 1 ran at 276 GB/s; the same copy from pinned host memory ran at 24 GB/s. The host also exposed ten Mellanox NICs (`mlx5_0`–`mlx5_9`) to the container. One machine, one pair: another A100 SXM host, or an 8-GPU one, can show a different matrix — run the command on yours.

### If you land on PCIe instead

Nothing to reconfigure — you tune around it.

| | |
|---|---|
| Re-deploy | Pick an SXM/NVL SKU explicitly rather than letting `gpuTypePriority` fall back |
| Lower the parallelism degree | Tensor parallelism is the most communication-hungry; pipeline or data parallelism tolerates PCIe better |
| Shard less often | Larger micro-batches mean fewer all-reduces for the same work |
| Check NCCL is not silently degrading | `NCCL_DEBUG=INFO` prints the transport it selected per pair |

### MIG — Runpod slices, you buy slices

Two MIG profiles are live in the catalogue right now, as ordinary selectable GPU types:

| GPU type id | Shown as | VRAM | Max count |
|---|---|---|---|
| `…RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` | PRO 6000 MIG 24GB | 24GB | 32 |
| `…RTX PRO 6000 Blackwell Server Edition MIG 2g.48gb` | PRO 6000 MIG 48GB | 48GB | 16 |

Both are Secure Cloud only. The parent card, RTX PRO 6000 (96GB), is also sold whole.

Runpod's [announcement](https://www.runpod.io/blog/multi-instance-gpu-on-runpod) is explicit that this is their decision, not yours: *"we will never time-slice or segment a GPU without being completely up front that we are doing it. If you pay for the whole card, you get the whole card, full stop."* Serverless endpoints can opt out with a checkbox under **Advanced**. Pods are stated as coming later.

<div class="warn" markdown="1">
**The blog undercounts.** It describes 24GB chunks only, but the catalogue carries both `1g.24gb` and `2g.48gb`. The API is ahead of the announcement — check the catalogue, not the blog post.
</div>

### Why you cannot slice it yourself

Not a licensing or silicon limit. MIG configuration is a host-privileged device operation:

| Requirement | Command / condition |
|---|---|
| Enable MIG mode | `sudo nvidia-smi -i 0 -mig 1` — elevated privileges |
| No other work on the card | All GPU processes must be stopped, or you get `In use by another client` |
| Device reset | Required pre-Hopper; Hopper and newer no longer need it |
| Create instances | `nvidia-smi mig -cgi <profile> -i 0` |

A Runpod tenant has none of these. Pods and Serverless workers are containers; Instant Clusters are too — Runpod describes them as [*"Containerized: Runs on Docker"*](https://www.runpod.io/blog/bare-metal-vs-instant-clusters-whats-best-for-your-ai-workload). You are not host root, you cannot stop another tenant's processes, and you cannot reset a shared device.

Tried on the same Pod. The container runs as uid 0, but without `cap_sys_admin`:

```
$ nvidia-smi -i 0 -mig 1
Unable to enable MIG Mode for GPU 00000000:90:00.0: Insufficient Permissions
```

`mig.mode.pending` stayed `Disabled`. Root inside the container is not root on the device.

**Clusters do not change this.** Multi-node gets you more GPUs, not more privilege. The tier that does is **Bare Metal**, positioned for teams needing *"full system access or specialized configurations"*.

| Tier | Form | Can you run `nvidia-smi -mig 1`? |
|---|---|---|
| Serverless | Container | No |
| Pod | Container | No — tried, `Insufficient Permissions` |
| Instant Cluster | Container (Docker), 2–8 nodes | No |
| Bare Metal | Physical server, no container layer | This is the tier where it becomes plausible |

Every GPU offered in Instant Clusters — B200, H200, H100, A100 — is MIG-capable silicon. What stops you is the access tier, not the hardware.

<div class="note" markdown="1">
Bare Metal is not verified here. The claim rests on Runpod's own positioning, not on a machine rented and tested.
</div>

### If you need a fraction and no SKU fits

MIG is one way to share a card, and the only one giving hardware-enforced isolation. When it is not available to you, the alternatives trade isolation for availability:

| Approach | Isolation | Works on Runpod today |
|---|---|---|
| Buy the MIG SKU | Hardware — separate memory and fault domains | Yes, RTX PRO 6000 only |
| Several models in one worker process | None — one OOM takes down everything | Yes, plain Python |
| Concurrent handler (`concurrency_modifier`) | None — same process, same memory | Yes, see [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| CUDA MPS | Partial — shared context, optional per-client allocation cap | Yes — daemon runs inside a Pod, see below |
| Just rent a smaller card | Total — it is a different machine | Yes, RTX 3070 8GB upward |

The last row is the one people skip. The catalogue runs from 8GB at $0.13/hr, and a smaller whole card is often simpler and cheaper than partitioning a large one.

### CUDA MPS inside a Pod

CUDA MPS runs inside a Pod with no extra setup — the image ships `nvidia-cuda-mps-control`. Measured on GPU 0 of the same Pod:

| Check | Result |
|---|---|
| `nvidia-cuda-mps-control -d` | Starts, exit 0 |
| Two `torch` matmul processes | Both listed as type `M+C`, beside `nvidia-cuda-mps-server` |
| `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT="0=2G"`, allocate 4 GiB | `CUDA out of memory` |
| Same limit, allocate 1 GiB | Allocated |
| Same limit with the daemon stopped, allocate 4 GiB | Allocated — the cap comes from MPS |

Set `CUDA_MPS_PIPE_DIRECTORY` and `CUDA_MPS_LOG_DIRECTORY` to writable paths before starting the daemon, and give clients the same values. The cap limits allocation; it is not memory protection, and one faulting client can still take the others down.

### Across nodes

[Instant Clusters](https://docs.runpod.io/instant-clusters) scale to 2–8 nodes, 16–64 GPUs, with larger deployments by arrangement:

| GPU | Inter-node bandwidth | Nodes |
|---|---|---|
| B200 | 3200 Gbps | 2–8 |
| H200 | 3200 Gbps | 2–8 |
| H100 | 3200 Gbps | 2–8 |
| A100 | 1600 Gbps | 2–8 |

Inter-node traffic runs over interfaces `ens1`–`ens8`; the primary node reaches the outside through `eth0`.

<div class="warn" markdown="1">
Runpod's cluster documentation never names the interconnect technology. It quotes bandwidth figures in the InfiniBand/RDMA class but does not say InfiniBand, RDMA, GPUDirect, or NVLink anywhere. If your framework needs to know — and NCCL does — determine it at runtime rather than from the docs.
</div>

### What is verified here

| Claim | How |
|---|---|
| 48 GPU types; two are MIG SKUs | Live catalogue query |
| `POST /pods` has no topology field | Published OpenAPI spec, 33 properties enumerated |
| REST surface is 23 paths, no build or partition control | Same spec |
| MIG needs root, stopped processes, reset pre-Hopper | NVIDIA documentation |
| `topo -m` legend | NVIDIA documentation |
| Clusters are Docker containers | Runpod's own comparison page |
| Actual `topo -m` output on a Runpod host | Run 2026-11-05 — 2× A100 SXM, `NV12`, 276 GB/s GPU-to-GPU copy |
| `nvidia-smi -mig 1` inside a Pod | Run 2026-11-05 — `Insufficient Permissions` |
| Bare Metal permitting MIG | **Not run** — vendor positioning only |
| MPS inside a Runpod container | Run 2026-11-05 — `M+C` clients, per-client cap enforced |

[Full reference in the repo →](https://github.com/litkhai/runpod-hols/blob/main/gpu-topology/README.md)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

NVLink 와 MIG 는 GPU 에 대해 두 가지를 결정합니다. 옆의 GPU 와 얼마나 빠르게 대화하는가, 그리고 쪼갤 수 있는가. 둘 다 특정 제공사와 무관하게 그 자체로 알아둘 가치가 있는 개념입니다.

Runpod 이 이를 어떻게 제공하는지는 그 다음 이야기이고, 두 답이 서로 반대입니다. NVLink 는 제공되지만 설정할 수 없고, MIG 는 Runpod 이 이미 잘라놓은 조각으로만 제공됩니다.

개념은 벤더 문서 기준입니다. Runpod 쪽은 살아있는 GPU 카탈로그와 발행된 REST OpenAPI 스펙에서 확인했으며, 하드웨어 항목은 2026-11-05 A100 SXM 2장 Pod 하나에서 실행했습니다. Bare Metal 은 빌리지 않았으므로 미검증입니다.

## 개념
{: #concepts-ko }

### NVLink 란

GPU 끼리 직접 연결하는 링크입니다. 없으면 한 GPU 가 다른 GPU 에 닿기 위해 PCIe 로 나가 CPU 와 시스템 메모리를 거쳐 돌아와야 하고, GPU 들이 매 스텝 데이터를 주고받아야 하는 순간 이 우회가 병목이 됩니다.

| 경로 | 양방향 대역폭 |
|---|---|
| H100 SXM 의 NVLink 4 — 18 레인 | 900 GB/s |
| PCIe 5.0 x16 | 128 GB/s |
| PCIe 스위치 패브릭을 통한 실사용 peer-to-peer | 50–100 GB/s |

대략 7배 이상이며, 연결의 생김새 자체가 다릅니다. NVLink 는 GPU 들이 메시를 이루고, PCIe 는 중앙 호스트 브리지를 경유합니다.

병렬화가 얼마나 수다스러운지에 비례해 중요해집니다. 텐서 병렬은 레이어마다 활성값을 주고받아 가장 크게 영향받고, 데이터 병렬은 스텝당 한 번 gradient 를 all-reduce 하며, 단일 GPU 작업은 아예 체감하지 못합니다.

### MIG 란

Multi-Instance GPU 는 물리 카드 하나를 **GPU Instance** 로 잘라 각각을 더 작은 별개의 GPU 처럼 쓰게 합니다. SM 과 메모리가 전용으로 배정되고 장애 도메인도 분리되어, 한 인스턴스가 죽어도 나머지를 끌고 내려가지 않습니다.

프로파일 이름은 `<N>g.<M>gb` 형식입니다. `N` 은 인스턴스가 받는 연산 슬라이스 수, `M` 은 전용 메모리 용량(GB)입니다. `1g.24gb` 는 슬라이스 하나에 24GB 이고, `7g` 는 카드 전체입니다. GPU Instance 안을 다시 **Compute Instance** 로 나눌 수 있는데, 이들은 해당 인스턴스의 메모리를 공유하면서 연산만 나눠 씁니다. 복사·인코딩·디코딩·JPEG·OFA 같은 고정 기능 엔진은 여전히 공유로 표시됩니다.

카드를 나눠 쓰는 다른 방식과 MIG 를 가르는 지점이 여기입니다.

| | 메모리 격리 | 장애 격리 |
|---|---|---|
| MIG | 하드웨어로 보장 | 됨 |
| 타임 슬라이싱 | 없음 | 안 됨 |
| CUDA MPS | 없음 — 할당 상한까지만 | 안 됨 |

그 하드웨어 격리가 MIG 의 존재 이유이자, 컨테이너 안에서 설정할 수 없는 이유입니다.

## Runpod 은 이를 어떻게 제공하는가
{: #on-runpod-ko }

### 짧은 답

| | 되는가 | 누가 정하는가 |
|---|---|---|
| **NVLink** | 됩니다. SXM/NVL 하드웨어에서 | 아무도 아닙니다 — 내가 배정받은 머신의 속성입니다 |
| **MIG** | 됩니다. 미리 잘린 SKU 로 | Runpod. 슬라이스를 사는 것이지 자르는 게 아닙니다 |

둘 다 *제공은* 되고 둘 다 *설정 대상은* 아닙니다. 내가 고르는 것은 GPU 타입이고, 토폴로지는 거기서 따라옵니다.

### API 로 제어할 수 있는 것

[발행된 OpenAPI 스펙](https://rest.runpod.io/v1/openapi.json)의 `POST /pods` 는 속성이 33개인데, interconnect·topology·NVLink·MIG·partition 관련 항목이 하나도 없습니다. GPU 관련은 `gpuTypeIds`, `gpuCount`, `gpuTypePriority`, `minRAMPerGPU`, `minVCPUPerGPU` 가 전부입니다.

`POST /endpoints` 는 더 좁아서 `templateId` 를 요구할 뿐 GPU 토폴로지 필드가 아예 없습니다. REST 전체가 23개 경로이며 빌드·토폴로지·파티셔닝용 경로는 없습니다.

즉 레버는 SKU 선택 하나입니다.

### NVLink — 맞는 SKU 를 고르면 따라옵니다

카탈로그에 GPU 타입이 48개 있고, NVLink 를 가진 것은 이름으로 구분됩니다.

| GPU 타입 | VRAM | 비고 |
|---|---|---|
| B200 | 180GB | NVLink 5 — 그런데 이름에 표시가 없습니다 |
| H200 NVL | 143GB | |
| H200 SXM | 141GB | |
| H100 NVL | 94GB | |
| A100 SXM | 80GB | |
| H100 SXM | 80GB | |
| A100 SXM 40GB | 40GB | |
| V100 SXM2 | 16GB | NVLink 2 |

반대로 의도적으로 없는 것: **A100 PCIe**, **H100 PCIe**. 같은 실리콘, 같은 VRAM, NVLink 대신 PCIe 입니다.

<div class="warn" markdown="1">
**이름은 힌트지 계약이 아닙니다.** `B200` 은 NVLink 를 갖고도 이름에 아무 표시가 없고, `A100 PCIe` 와 `A100 SXM` 은 접미사만 다릅니다. Runpod 은 토폴로지를 알려주는 필드를 제공하지 않으므로 부팅 전에는 이름이 전부인데, 그것으로는 부족합니다.
</div>

### 실제로 무엇을 받았는지 확인하기

```bash
nvidia-smi topo -m
```

범례는 [NVIDIA 문서](https://docs.nvidia.com/deploy/nvidia-smi/index.html) 기준입니다.

| 코드 | 의미 |
|---|---|
| `X` | 자기 자신 |
| `NV#` | NVLink # 개를 묶은 연결 |
| `PIX` | PCIe 스위치 한 개를 경유 |
| `PXB` | PCIe 스위치 여러 개를 경유, 호스트 브리지는 거치지 않음 |
| `PHB` | PCIe 호스트 브리지(보통 CPU)를 경유 |
| `NODE` | PCIe 와 같은 NUMA 노드 내 호스트 브리지 간 연결을 경유 |
| `SYS` | PCIe 와 NUMA 노드 간 SMP 연결(QPI/UPI)을 경유 |

모든 GPU 쌍이 `NV#` 인 것이 목표입니다. `PIX` 이하라면 all-reduce 트래픽이 PCIe 를 건너고 있다는 뜻이고, `SYS` 라면 소켓까지 넘고 있다는 뜻입니다.

Runpod Secure Cloud Pod, `NVIDIA A100-SXM4-80GB` 2장, 드라이버 595.91.07, 2026-11-05 에 실행했습니다 ([#14](https://github.com/litkhai/runpod-hols/issues/14)).

```
	GPU0	GPU1	NIC0 … NIC9	CPU Affinity	NUMA Affinity
GPU0	 X 	NV12	SYS … NODE	64-127	1
GPU1	NV12	 X 	SYS … NODE	64-127	1
```

`NV12` — NVLink 12개 묶음이고, `nvidia-smi nvlink -s` 는 링크 0–11 을 각각 25 GB/s 로 보여줬습니다. GPU 0 에서 GPU 1 로 1 GiB `torch` 복사가 276 GB/s, 같은 복사를 pinned 호스트 메모리에서 하면 24 GB/s 였습니다. 호스트의 Mellanox NIC 10개 (`mlx5_0`–`mlx5_9`) 도 컨테이너에 보였습니다. 머신 한 대, GPU 한 쌍의 결과입니다. 다른 A100 SXM 호스트나 8 GPU 머신은 다른 행렬을 보일 수 있으니 직접 실행해 보세요.

### PCIe 로 떨어졌다면

재설정할 것은 없습니다. 우회해서 튜닝하는 영역입니다.

| | |
|---|---|
| 재배포 | `gpuTypePriority` 대체에 맡기지 말고 SXM/NVL SKU 를 명시적으로 지정 |
| 병렬화 차수 낮추기 | 텐서 병렬이 통신을 가장 많이 씁니다. 파이프라인·데이터 병렬이 PCIe 를 더 잘 견딥니다 |
| 덜 자주 샤딩 | 마이크로배치를 키우면 같은 작업에 all-reduce 횟수가 줄어듭니다 |
| NCCL 이 조용히 성능을 떨구고 있지 않은지 확인 | `NCCL_DEBUG=INFO` 가 쌍별로 선택한 전송 방식을 출력합니다 |

### MIG — Runpod 이 자르고, 나는 조각을 삽니다

지금 카탈로그에 MIG 프로파일 두 개가 일반 GPU 타입처럼 올라와 있습니다.

| GPU 타입 id | 표시 이름 | VRAM | 최대 개수 |
|---|---|---|---|
| `…RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` | PRO 6000 MIG 24GB | 24GB | 32 |
| `…RTX PRO 6000 Blackwell Server Edition MIG 2g.48gb` | PRO 6000 MIG 48GB | 48GB | 16 |

둘 다 Secure Cloud 전용입니다. 원본 카드인 RTX PRO 6000(96GB)도 통째로 판매됩니다.

Runpod [발표](https://www.runpod.io/blog/multi-instance-gpu-on-runpod)는 이것이 자기들 결정이지 사용자 결정이 아님을 분명히 합니다. *"we will never time-slice or segment a GPU without being completely up front that we are doing it. If you pay for the whole card, you get the whole card, full stop."* Serverless 엔드포인트는 설정의 **Advanced** 에서 체크박스로 해제할 수 있고, Pod 은 추후 적용 예정이라고 합니다.

<div class="warn" markdown="1">
**블로그가 과소 표기하고 있습니다.** 24GB 조각만 설명하지만 카탈로그에는 `1g.24gb` 와 `2g.48gb` 가 모두 있습니다. API 가 발표보다 앞서 있으니 블로그가 아니라 카탈로그를 보세요.
</div>

### 왜 직접 자를 수 없는가

라이선스나 실리콘 문제가 아닙니다. MIG 설정은 호스트 특권이 필요한 디바이스 조작입니다.

| 요구사항 | 명령 / 조건 |
|---|---|
| MIG 모드 활성화 | `sudo nvidia-smi -i 0 -mig 1` — 상승된 권한 필요 |
| 해당 카드에 다른 작업이 없을 것 | 모든 GPU 프로세스가 멈춰야 하며, 아니면 `In use by another client` |
| 디바이스 리셋 | Hopper 이전 세대는 필요. Hopper 이상은 불필요 |
| 인스턴스 생성 | `nvidia-smi mig -cgi <profile> -i 0` |

Runpod 테넌트에게는 이 중 아무것도 없습니다. Pod 과 Serverless 워커는 컨테이너이고, Instant Cluster 도 마찬가지입니다 — Runpod 이 직접 [*"Containerized: Runs on Docker"*](https://www.runpod.io/blog/bare-metal-vs-instant-clusters-whats-best-for-your-ai-workload) 라고 표현합니다. 호스트 root 가 아니고, 다른 테넌트의 프로세스를 멈출 수 없으며, 공유 디바이스를 리셋할 수 없습니다.

같은 Pod 에서 시도했습니다. 컨테이너는 uid 0 으로 돌지만 `cap_sys_admin` 이 없습니다.

```
$ nvidia-smi -i 0 -mig 1
Unable to enable MIG Mode for GPU 00000000:90:00.0: Insufficient Permissions
```

`mig.mode.pending` 은 `Disabled` 그대로였습니다. 컨테이너 안의 root 는 디바이스의 root 가 아닙니다.

**Cluster 라고 달라지지 않습니다.** 멀티 노드는 GPU 를 더 주는 것이지 권한을 더 주는 게 아닙니다. 권한이 달라지는 계층은 **Bare Metal** 이고, Runpod 은 이를 *"full system access or specialized configurations"* 가 필요한 팀용으로 소개합니다.

| 계층 | 형태 | `nvidia-smi -mig 1` 가능? |
|---|---|---|
| Serverless | 컨테이너 | 불가 |
| Pod | 컨테이너 | 불가 — 시도 결과 `Insufficient Permissions` |
| Instant Cluster | 컨테이너(Docker), 2–8 노드 | 불가 |
| Bare Metal | 물리 서버, 컨테이너 계층 없음 | 가능해지는 계층 |

Instant Cluster 에서 제공되는 GPU — B200, H200, H100, A100 — 는 전부 MIG 가능한 실리콘입니다. 막는 것은 하드웨어가 아니라 접근 계층입니다.

<div class="note" markdown="1">
Bare Metal 은 검증하지 않았습니다. 이 항목은 Runpod 의 제품 소개에 근거한 것이지 실제로 빌려서 시험해 본 결과가 아닙니다.
</div>

### 조각이 필요한데 맞는 SKU 가 없다면

MIG 는 카드를 나눠 쓰는 여러 방법 중 하나이며, 하드웨어로 격리가 보장되는 유일한 방법입니다. 쓸 수 없을 때의 대안은 격리를 가용성과 맞바꿉니다.

| 방법 | 격리 | 지금 Runpod 에서 |
|---|---|---|
| MIG SKU 구매 | 하드웨어 — 메모리와 장애 도메인이 분리 | 가능. RTX PRO 6000 한정 |
| 워커 프로세스 하나에 모델 여러 개 | 없음 — OOM 하나로 전부 죽음 | 가능. 평범한 Python |
| 동시 핸들러 (`concurrency_modifier`) | 없음 — 같은 프로세스, 같은 메모리 | 가능. [Worker SDK]({{ '/sdk/worker/' | relative_url }}) 참조 |
| CUDA MPS | 부분적 — 컨텍스트 공유, 클라이언트별 할당 상한 선택 가능 | 됨 — Pod 안에서 데몬 실행, 아래 참고 |
| 그냥 더 작은 카드를 빌리기 | 완전 — 애초에 다른 머신 | 가능. RTX 3070 8GB 부터 |

마지막 줄을 다들 건너뜁니다. 카탈로그는 8GB $0.13/hr 부터 시작하고, 큰 카드를 쪼개는 것보다 작은 카드를 통째로 쓰는 쪽이 더 간단하고 싼 경우가 많습니다.

### Pod 안의 CUDA MPS

CUDA MPS 는 Pod 안에서 별도 준비 없이 동작합니다. 이미지에 `nvidia-cuda-mps-control` 이 들어 있습니다. 같은 Pod 의 GPU 0 에서 측정했습니다.

| 확인 항목 | 결과 |
|---|---|
| `nvidia-cuda-mps-control -d` | 기동, exit 0 |
| `torch` matmul 프로세스 2개 | 둘 다 `nvidia-cuda-mps-server` 옆에 타입 `M+C` 로 표시 |
| `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT="0=2G"`, 4 GiB 할당 | `CUDA out of memory` |
| 같은 제한, 1 GiB 할당 | 할당됨 |
| 같은 제한, 데몬 중지 상태에서 4 GiB 할당 | 할당됨 — 상한은 MPS 가 건다 |

데몬을 띄우기 전에 `CUDA_MPS_PIPE_DIRECTORY` 와 `CUDA_MPS_LOG_DIRECTORY` 를 쓰기 가능한 경로로 정하고, 클라이언트에도 같은 값을 주세요. 이 상한은 할당 제한일 뿐 메모리 보호가 아니며, 한 클라이언트의 장애가 나머지를 함께 쓰러뜨릴 수 있습니다.

### 노드를 넘어갈 때

[Instant Clusters](https://docs.runpod.io/instant-clusters) 는 2–8 노드, 16–64 GPU 규모이며 그 이상은 별도 협의입니다.

| GPU | 노드 간 대역폭 | 노드 수 |
|---|---|---|
| B200 | 3200 Gbps | 2–8 |
| H200 | 3200 Gbps | 2–8 |
| H100 | 3200 Gbps | 2–8 |
| A100 | 1600 Gbps | 2–8 |

노드 간 트래픽은 `ens1`–`ens8` 인터페이스를 쓰고, 프라이머리 노드가 `eth0` 로 외부와 통신합니다.

<div class="warn" markdown="1">
Runpod 의 클러스터 문서는 인터커넥트 기술 이름을 한 번도 쓰지 않습니다. InfiniBand/RDMA 급의 대역폭 수치를 제시하면서도 InfiniBand·RDMA·GPUDirect·NVLink 중 어느 것도 언급하지 않습니다. 프레임워크가 그것을 알아야 한다면 — NCCL 은 알아야 합니다 — 문서가 아니라 런타임에 판단하게 하세요.
</div>

### 여기서 검증한 것

| 주장 | 방법 |
|---|---|
| GPU 타입 48개, 그중 둘이 MIG SKU | 카탈로그 실시간 조회 |
| `POST /pods` 에 토폴로지 필드 없음 | 발행된 OpenAPI 스펙, 속성 33개 전수 확인 |
| REST 전체 23개 경로, 빌드·파티션 제어 없음 | 같은 스펙 |
| MIG 는 root·프로세스 정지·Hopper 이전 리셋 필요 | NVIDIA 문서 |
| `topo -m` 범례 | NVIDIA 문서 |
| Cluster 는 Docker 컨테이너 | Runpod 자체 비교 페이지 |
| Runpod 호스트에서의 실제 `topo -m` 출력 | 2026-11-05 실행 — A100 SXM 2장, `NV12`, GPU 간 복사 276 GB/s |
| Pod 안에서 `nvidia-smi -mig 1` | 2026-11-05 실행 — `Insufficient Permissions` |
| Bare Metal 에서 MIG 가능 여부 | **미실행** — 벤더 소개 문구에만 근거 |
| Runpod 컨테이너 안에서의 MPS | 2026-11-05 실행 — `M+C` 클라이언트, 클라이언트별 상한 적용됨 |

[저장소에서 전체 레퍼런스 보기 →](https://github.com/litkhai/runpod-hols/blob/main/gpu-topology/README.md)

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

NVLink 和 MIG 决定了 GPU 的两件事：它与相邻 GPU 通信有多快，以及它能否被切分。两者都值得脱离任何云厂商单独理解。

Runpod 如何对待它们是第二个问题——而两者的答案恰好相反。NVLink 可用，但永远不可配置。MIG 只能以 Runpod 已经切好的切片形式使用。

概念部分来自厂商文档。Runpod 部分来自实时 GPU 目录和公开的 REST OpenAPI 规范；硬件相关的结论是在 2026-11-05 于一台 2× A100 SXM Pod 上实际运行得出的。Bare Metal 没有租用，仍未验证。

## 概念
{: #concepts-zh }

### NVLink 是什么

一条 GPU 到 GPU 的直连链路。没有它，一块 GPU 要访问另一块，就得经由 PCIe 出去，穿过 CPU 和系统内存再回来——一旦 GPU 每一步都要交换数据，这段绕路就会成为瓶颈。

| 路径 | 双向带宽 |
|---|---|
| H100 SXM 上的 NVLink 4——18 条链路 | 900 GB/s |
| PCIe 5.0 x16 | 128 GB/s |
| 经 PCIe 交换结构的实际点对点 | 50–100 GB/s |

大约 7 倍甚至更多，而且连接的形态也不同：NVLink GPU 组成网状结构，而 PCIe 要经过中央的主机桥。

它的重要程度与并行方式的通信频繁程度成正比。张量并行在每一层都要交换激活值，受影响最大；数据并行每一步对梯度做一次 all-reduce；单 GPU 作业则完全察觉不到。

### MIG 是什么

Multi-Instance GPU 把一块物理卡切成若干 **GPU Instance**，它们的行为就像彼此独立的小 GPU——专用的 SM、专用的显存，以及各自的故障域，一个实例崩溃不会连带其他实例。

配置文件命名为 `<N>g.<M>gb`：`N` 是该实例获得的计算切片数，`M` 是其专用显存（GB）。`1g.24gb` 是一个切片加 24GB；`7g` 是整张卡。在 GPU Instance 内部还可以进一步细分为 **Compute Instance**，它们共享该实例的显存但分割其算力。一些固定功能引擎——复制、编码、解码、JPEG、OFA——仍显示为共享。

这正是 MIG 与其他共享 GPU 方式的区别：

| | 显存隔离 | 故障隔离 |
|---|---|---|
| MIG | 有，由硬件强制 | 有 |
| 时间切片 | 无 | 无 |
| CUDA MPS | 无——最多只有分配上限 | 无 |

硬件隔离正是关键所在——也正因如此，它无法在容器内部设置。

## Runpod 如何提供它们
{: #on-runpod-zh }

### 简短的回答

| | 可用吗？ | 由谁控制 |
|---|---|---|
| **NVLink** | 可用，在 SXM/NVL 硬件上 | 没有人——它是你被分配到的机器的属性 |
| **MIG** | 可用，以预切好的 SKU 形式 | Runpod。你购买切片，但不能自己切 |

两者都*可用*，但都*不可配置*。你选择的是 GPU 类型，拓扑随之而定。

### API 允许你控制什么

[公开的 OpenAPI 规范](https://rest.runpod.io/v1/openapi.json)中的 `POST /pods` 有 33 个属性。没有一个涉及互连、拓扑、NVLink、MIG 或分区。与 GPU 相关的有 `gpuTypeIds`、`gpuCount`、`gpuTypePriority`、`minRAMPerGPU` 和 `minVCPUPerGPU`。

`POST /endpoints` 范围更窄——它要求 `templateId`，完全没有 GPU 拓扑字段。整个 REST 接口共 23 个路径，没有任何关于构建、拓扑或分区的内容。

所以唯一的手段就是选择 SKU。

### NVLink——选对 SKU 就能得到

Runpod 的目录返回 48 种 GPU 类型。带 NVLink 的可以通过名称识别：

| GPU 类型 | 显存 | 备注 |
|---|---|---|
| B200 | 180GB | NVLink 5——但名称中没有体现 |
| H200 NVL | 143GB | |
| H200 SXM | 141GB | |
| H100 NVL | 94GB | |
| A100 SXM | 80GB | |
| H100 SXM | 80GB | |
| A100 SXM 40GB | 40GB | |
| V100 SXM2 | 16GB | NVLink 2 |

而刻意不带 NVLink 的是：**A100 PCIe** 和 **H100 PCIe**——相同的芯片、相同的显存，用 PCIe 代替 NVLink。

<div class="warn" markdown="1">
**名称只是提示，不是承诺。** `B200` 带有 NVLink，却在名称中只字未提；而 `A100 PCIe` 和 `A100 SXM` 只有后缀不同。Runpod 没有任何声明拓扑的字段，所以启动之前你手里只有名称——而这还不够。
</div>

### 验证你实际得到了什么

```bash
nvidia-smi topo -m
```

图例，[来自 NVIDIA](https://docs.nvidia.com/deploy/nvidia-smi/index.html)：

| 代码 | 含义 |
|---|---|
| `X` | 自身 |
| `NV#` | 经过 # 条绑定 NVLink 的连接 |
| `PIX` | 经过单个 PCIe 交换机 |
| `PXB` | 经过多个 PCIe 交换机，不经过主机桥 |
| `PHB` | 经过 PCIe 主机桥（通常是 CPU） |
| `NODE` | 经过 PCIe 以及同一 NUMA 节点内主机桥之间的互连 |
| `SYS` | 经过 PCIe 以及 NUMA 节点之间的 SMP 互连（QPI/UPI） |

每对 GPU 之间都是 `NV#` 才是你想要的。从 `PIX` 往下的任何一项都意味着你的 all-reduce 流量在走 PCIe，而 `SYS` 意味着它还要跨越 CPU 插槽。

在 Runpod Secure Cloud Pod 上运行，2× `NVIDIA A100-SXM4-80GB`，驱动 595.91.07，2026-11-05（[#14](https://github.com/litkhai/runpod-hols/issues/14)）：

```
	GPU0	GPU1	NIC0 … NIC9	CPU Affinity	NUMA Affinity
GPU0	 X 	NV12	SYS … NODE	64-127	1
GPU1	NV12	 X 	SYS … NODE	64-127	1
```

`NV12`——十二条绑定的 NVLink，`nvidia-smi nvlink -s` 列出了链路 0–11，每条 25 GB/s。从 GPU 0 到 GPU 1 的 1 GiB `torch` 复制达到 276 GB/s；同样的复制从锁页主机内存发起则为 24 GB/s。主机还向容器暴露了十块 Mellanox 网卡（`mlx5_0`–`mlx5_9`）。只是一台机器、一对 GPU：另一台 A100 SXM 主机，或者 8-GPU 的主机，可能显示不同的矩阵——请在你自己的机器上运行这条命令。

### 如果你分到的是 PCIe

没什么可重新配置的——只能围绕它调优。

| | |
|---|---|
| 重新部署 | 明确选择 SXM/NVL SKU，而不是让 `gpuTypePriority` 回退 |
| 降低并行度 | 张量并行对通信需求最大；流水线并行或数据并行对 PCIe 的容忍度更好 |
| 减少分片频率 | 更大的 micro-batch 意味着同样的工作量下 all-reduce 次数更少 |
| 检查 NCCL 是否在悄悄降级 | `NCCL_DEBUG=INFO` 会打印每对 GPU 所选择的传输方式 |

### MIG——Runpod 切，你买切片

目录中目前有两个 MIG 配置文件在售，作为普通的可选 GPU 类型：

| GPU type id | 显示名称 | 显存 | 最大数量 |
|---|---|---|---|
| `…RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` | PRO 6000 MIG 24GB | 24GB | 32 |
| `…RTX PRO 6000 Blackwell Server Edition MIG 2g.48gb` | PRO 6000 MIG 48GB | 48GB | 16 |

两者都仅限 Secure Cloud。母卡 RTX PRO 6000（96GB）也整卡出售。

Runpod 的[公告](https://www.runpod.io/blog/multi-instance-gpu-on-runpod)明确表示这是他们的决定，而不是你的：*"we will never time-slice or segment a GPU without being completely up front that we are doing it. If you pay for the whole card, you get the whole card, full stop."* Serverless 端点可以通过 **Advanced** 下的复选框选择退出。Pod 据称稍后支持。

<div class="warn" markdown="1">
**博客少算了。** 它只描述了 24GB 的切块，但目录中同时有 `1g.24gb` 和 `2g.48gb`。API 走在公告前面——请查目录，而不是博客文章。
</div>

### 为什么你不能自己切

不是授权或芯片的限制。MIG 配置是一种需要主机特权的设备操作：

| 要求 | 命令 / 条件 |
|---|---|
| 启用 MIG 模式 | `sudo nvidia-smi -i 0 -mig 1`——需要提升权限 |
| 卡上没有其他工作 | 必须停止所有 GPU 进程，否则会得到 `In use by another client` |
| 设备重置 | Hopper 之前需要；Hopper 及更新的架构不再需要 |
| 创建实例 | `nvidia-smi mig -cgi <profile> -i 0` |

Runpod 租户一样都不具备。Pod 和 Serverless worker 都是容器；Instant Cluster 也是——Runpod 将其描述为 [*"Containerized: Runs on Docker"*](https://www.runpod.io/blog/bare-metal-vs-instant-clusters-whats-best-for-your-ai-workload)。你不是主机 root，不能停止其他租户的进程，也不能重置共享设备。

在同一台 Pod 上试过。容器以 uid 0 运行，但没有 `cap_sys_admin`：

```
$ nvidia-smi -i 0 -mig 1
Unable to enable MIG Mode for GPU 00000000:90:00.0: Insufficient Permissions
```

`mig.mode.pending` 保持为 `Disabled`。容器内的 root 不是设备上的 root。

**集群也改变不了这一点。** 多节点给你更多的 GPU，而不是更多的权限。能做到的层级是 **Bare Metal**，其定位面向需要 *"full system access or specialized configurations"* 的团队。

| 层级 | 形态 | 能运行 `nvidia-smi -mig 1` 吗？ |
|---|---|---|
| Serverless | 容器 | 不能 |
| Pod | 容器 | 不能——试过，`Insufficient Permissions` |
| Instant Cluster | 容器（Docker），2–8 个节点 | 不能 |
| Bare Metal | 物理服务器，没有容器层 | 在这个层级才变得有可能 |

Instant Cluster 提供的每一种 GPU——B200、H200、H100、A100——都是支持 MIG 的芯片。阻止你的是访问层级，而不是硬件。

<div class="note" markdown="1">
这里没有验证 Bare Metal。这一结论基于 Runpod 自己的定位说明，而不是实际租用并测试过的机器。
</div>

### 如果你只需要一部分算力而没有合适的 SKU

MIG 是共享一张卡的方式之一，也是唯一提供硬件强制隔离的方式。当你无法使用它时，替代方案以隔离性换取可用性：

| 方式 | 隔离性 | 目前能否在 Runpod 上使用 |
|---|---|---|
| 购买 MIG SKU | 硬件——独立的显存和故障域 | 能，仅限 RTX PRO 6000 |
| 在一个 worker 进程中运行多个模型 | 无——一次 OOM 会拖垮全部 | 能，普通 Python |
| 并发 handler（`concurrency_modifier`） | 无——同一进程、同一显存 | 能，见 [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| CUDA MPS | 部分——共享上下文，可选的每客户端分配上限 | 能——守护进程在 Pod 内运行，见下文 |
| 直接租一张更小的卡 | 完全——那是另一台机器 | 能，RTX 3070 8GB 起 |

最后一行是人们常常忽略的。目录从 8GB、$0.13/hr 起步，一张更小的整卡往往比切分一张大卡更简单、更便宜。

### 在 Pod 内使用 CUDA MPS

CUDA MPS 无需额外设置即可在 Pod 内运行——镜像自带 `nvidia-cuda-mps-control`。在同一台 Pod 的 GPU 0 上测得：

| 检查项 | 结果 |
|---|---|
| `nvidia-cuda-mps-control -d` | 启动，exit 0 |
| 两个 `torch` matmul 进程 | 都以类型 `M+C` 列出，旁边是 `nvidia-cuda-mps-server` |
| `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT="0=2G"`，分配 4 GiB | `CUDA out of memory` |
| 同样的上限，分配 1 GiB | 分配成功 |
| 同样的上限但停止守护进程，分配 4 GiB | 分配成功——上限来自 MPS |

启动守护进程之前，把 `CUDA_MPS_PIPE_DIRECTORY` 和 `CUDA_MPS_LOG_DIRECTORY` 设为可写路径，并给客户端设置相同的值。该上限限制的是分配，而不是内存保护，一个出错的客户端仍然可能拖垮其他客户端。

### 跨节点

[Instant Clusters](https://docs.runpod.io/instant-clusters) 可扩展到 2–8 个节点、16–64 块 GPU，更大规模的部署需另行安排：

| GPU | 节点间带宽 | 节点数 |
|---|---|---|
| B200 | 3200 Gbps | 2–8 |
| H200 | 3200 Gbps | 2–8 |
| H100 | 3200 Gbps | 2–8 |
| A100 | 1600 Gbps | 2–8 |

节点间流量走 `ens1`–`ens8` 接口；主节点通过 `eth0` 访问外部。

<div class="warn" markdown="1">
Runpod 的集群文档从未说明互连技术的名称。它给出的带宽数据属于 InfiniBand/RDMA 级别，但任何地方都没有提到 InfiniBand、RDMA、GPUDirect 或 NVLink。如果你的框架需要知道——NCCL 就需要——请在运行时确定，而不是依赖文档。
</div>

### 这里验证了什么

| 结论 | 方法 |
|---|---|
| 48 种 GPU 类型；其中两种是 MIG SKU | 实时目录查询 |
| `POST /pods` 没有拓扑字段 | 公开的 OpenAPI 规范，逐一列出 33 个属性 |
| REST 接口共 23 个路径，没有构建或分区控制 | 同一规范 |
| MIG 需要 root、停止进程、Hopper 之前需重置 | NVIDIA 文档 |
| `topo -m` 图例 | NVIDIA 文档 |
| 集群是 Docker 容器 | Runpod 自己的对比页面 |
| Runpod 主机上实际的 `topo -m` 输出 | 2026-11-05 运行——2× A100 SXM，`NV12`，GPU 到 GPU 复制 276 GB/s |
| Pod 内运行 `nvidia-smi -mig 1` | 2026-11-05 运行——`Insufficient Permissions` |
| Bare Metal 允许 MIG | **未运行**——仅为厂商定位说明 |
| Runpod 容器内的 MPS | 2026-11-05 运行——`M+C` 客户端，每客户端上限生效 |

[仓库中的完整参考 →](https://github.com/litkhai/runpod-hols/blob/main/gpu-topology/README.md)

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

NVLink と MIG は GPU について 2 つのことを決めます。隣の GPU とどれだけ速く通信できるか、そして分割できるかどうかです。どちらも、特定のプロバイダとは切り離してそれ自体として理解しておく価値があります。

Runpod がそれらをどう扱うかは二の次で、しかも 2 つの答えは正反対です。NVLink は利用できますが、決して設定できません。MIG は Runpod がすでに切り分けたスライスとしてのみ利用できます。

概念はベンダーのドキュメントによるものです。Runpod 側はライブの GPU カタログと公開されている REST OpenAPI 仕様によるもので、ハードウェアに関する主張は 2026-11-05 に 2× A100 SXM の Pod 1 台で実際に実行して確かめました。Bare Metal は借りておらず、未検証のままです。

## 概念
{: #concepts-ja }

### NVLink とは

GPU 同士を直接つなぐリンクです。これがないと、ある GPU から別の GPU へは PCIe を出て CPU とシステムメモリを経由して戻ってくることになります。GPU がステップごとにデータを交換しなければならなくなった瞬間、この回り道がボトルネックになります。

| 経路 | 双方向帯域幅 |
|---|---|
| H100 SXM の NVLink 4（18 レーン） | 900 GB/s |
| PCIe 5.0 x16 | 128 GB/s |
| PCIe スイッチファブリック越しの実用的なピアツーピア | 50–100 GB/s |

おおよそ 7 倍以上で、接続の形も違います。NVLink の GPU はメッシュを形成し、PCIe は中央のホストブリッジを経由します。

重要度は、並列化がどれだけ通信を多用するかに比例します。テンソル並列はレイヤーごとにアクティベーションを交換するので最も影響を受けます。データ並列はステップごとに 1 回勾配を all-reduce します。単一 GPU のジョブはまったく気づきません。

### MIG とは

Multi-Instance GPU は、1 枚の物理カードを複数の **GPU Instance** に切り分け、それぞれが独立した小さな GPU のように振る舞うようにします。専用の SM、専用のメモリ、独自の障害ドメインを持つので、1 つのインスタンスがクラッシュしても他を巻き込みません。

プロファイルは `<N>g.<M>gb` という名前です。`N` はインスタンスが得るコンピュートスライスの数、`M` は専用メモリ（GB）です。`1g.24gb` は 1 スライスと 24GB、`7g` はカード全体です。GPU Instance の中はさらに **Compute Instance** に細分でき、これらはそのインスタンスのメモリを共有しつつコンピュートを分け合います。一部の固定機能エンジン（コピー、エンコード、デコード、JPEG、OFA）は引き続き共有として表示されます。

これが MIG とカードを共有する他の方法との違いです。

| | メモリ分離 | 障害分離 |
|---|---|---|
| MIG | あり、ハードウェアで強制 | あり |
| タイムスライシング | なし | なし |
| CUDA MPS | なし（せいぜい割り当て上限） | なし |

このハードウェア分離こそが要点であり、コンテナの中から設定できない理由でもあります。

## Runpod での提供のされ方
{: #on-runpod-ja }

### 短い答え

| | 利用できるか | 誰が制御するか |
|---|---|---|
| **NVLink** | はい、SXM/NVL ハードウェアで | 誰も制御しない。割り当てられたマシンの性質 |
| **MIG** | はい、切り分け済みの SKU として | Runpod。スライスは買えるが、自分では切れない |

どちらも*利用でき*、どちらも*設定できません*。選ぶのは GPU タイプで、トポロジーはそれに従って決まります。

### API で制御できること

[公開されている OpenAPI 仕様](https://rest.runpod.io/v1/openapi.json)の `POST /pods` には 33 個のプロパティがあります。インターコネクト、トポロジー、NVLink、MIG、パーティショニングに触れるものは 1 つもありません。GPU に関係するのは `gpuTypeIds`、`gpuCount`、`gpuTypePriority`、`minRAMPerGPU`、`minVCPUPerGPU` です。

`POST /endpoints` はさらに範囲が狭く、`templateId` を必須とし、GPU トポロジーのフィールドはまったくありません。REST 全体で 23 パスあり、ビルド、トポロジー、パーティショニングに関するものは何もありません。

つまり使える手段は SKU の選択です。

### NVLink：正しい SKU を選べば手に入る

Runpod のカタログは 48 種類の GPU タイプを返します。NVLink を持つものは名前で見分けられます。

| GPU タイプ | VRAM | 備考 |
|---|---|---|
| B200 | 180GB | NVLink 5。ただし名前からはわからない |
| H200 NVL | 143GB | |
| H200 SXM | 141GB | |
| H100 NVL | 94GB | |
| A100 SXM | 80GB | |
| H100 SXM | 80GB | |
| A100 SXM 40GB | 40GB | |
| V100 SXM2 | 16GB | NVLink 2 |

そして意図的に NVLink を持たないのが **A100 PCIe** と **H100 PCIe** です。同じシリコン、同じ VRAM で、NVLink の代わりに PCIe を使います。

<div class="warn" markdown="1">
**名前はヒントであって、保証ではありません。** `B200` は NVLink を持っているのに名前では何も示さず、`A100 PCIe` と `A100 SXM` はサフィックスが違うだけです。Runpod にはトポロジーを明示するフィールドがないので、起動前に手がかりになるのは名前だけで、それでは足りません。
</div>

### 実際に何を得たかを確認する

```bash
nvidia-smi topo -m
```

凡例（[NVIDIA より](https://docs.nvidia.com/deploy/nvidia-smi/index.html)）：

| コード | 意味 |
|---|---|
| `X` | 自分自身 |
| `NV#` | # 本の束ねられた NVLink を通る接続 |
| `PIX` | 単一の PCIe スイッチを経由 |
| `PXB` | 複数の PCIe スイッチを経由、ホストブリッジは通らない |
| `PHB` | PCIe ホストブリッジ（通常は CPU）を経由 |
| `NODE` | PCIe と、1 つの NUMA ノード内のホストブリッジ間インターコネクトを経由 |
| `SYS` | PCIe と、NUMA ノード間の SMP インターコネクト（QPI/UPI）を経由 |

すべての GPU ペアの間が `NV#` であることが望ましい状態です。`PIX` 以下のどれかであれば all-reduce のトラフィックが PCIe を通っており、`SYS` ならソケットもまたいでいます。

Runpod Secure Cloud の Pod、2× `NVIDIA A100-SXM4-80GB`、ドライバ 595.91.07、2026-11-05 に実行（[#14](https://github.com/litkhai/runpod-hols/issues/14)）：

```
	GPU0	GPU1	NIC0 … NIC9	CPU Affinity	NUMA Affinity
GPU0	 X 	NV12	SYS … NODE	64-127	1
GPU1	NV12	 X 	SYS … NODE	64-127	1
```

`NV12` は 12 本の束ねられた NVLink で、`nvidia-smi nvlink -s` はリンク 0–11 をそれぞれ 25 GB/s と表示しました。GPU 0 から GPU 1 への 1 GiB の `torch` コピーは 276 GB/s、同じコピーをピン留めしたホストメモリから行うと 24 GB/s でした。ホストはさらに 10 枚の Mellanox NIC（`mlx5_0`–`mlx5_9`）をコンテナに公開していました。これは 1 台のマシン、1 つのペアでの結果です。別の A100 SXM ホストや 8 GPU のホストでは異なる行列になることがあるので、自分の環境でコマンドを実行してください。

### PCIe に当たってしまったら

再設定できるものはありません。それを前提にチューニングします。

| | |
|---|---|
| 再デプロイ | `gpuTypePriority` にフォールバックさせず、SXM/NVL の SKU を明示的に選ぶ |
| 並列度を下げる | テンソル並列が最も通信を必要とする。パイプライン並列やデータ並列のほうが PCIe に耐えやすい |
| シャーディングの頻度を減らす | マイクロバッチを大きくすれば、同じ作業量でも all-reduce の回数が減る |
| NCCL が黙って劣化していないか確認する | `NCCL_DEBUG=INFO` でペアごとに選ばれたトランスポートが出力される |

### MIG：Runpod が切り、あなたはスライスを買う

現在カタログには 2 つの MIG プロファイルが、通常の選択可能な GPU タイプとして並んでいます。

| GPU type id | 表示名 | VRAM | 最大数 |
|---|---|---|---|
| `…RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` | PRO 6000 MIG 24GB | 24GB | 32 |
| `…RTX PRO 6000 Blackwell Server Edition MIG 2g.48gb` | PRO 6000 MIG 48GB | 48GB | 16 |

どちらも Secure Cloud のみです。親カードの RTX PRO 6000（96GB）も丸ごと販売されています。

Runpod の[発表](https://www.runpod.io/blog/multi-instance-gpu-on-runpod)は、これがあなたではなく Runpod の判断であることを明言しています：*"we will never time-slice or segment a GPU without being completely up front that we are doing it. If you pay for the whole card, you get the whole card, full stop."* Serverless エンドポイントは **Advanced** の下のチェックボックスでオプトアウトできます。Pod は後日対応とされています。

<div class="warn" markdown="1">
**ブログは数え漏らしています。** 24GB 単位のチャンクしか説明していませんが、カタログには `1g.24gb` と `2g.48gb` の両方があります。API は発表より先を行っているので、ブログ記事ではなくカタログを確認してください。
</div>

### なぜ自分で切り分けられないのか

ライセンスやシリコンの制限ではありません。MIG の設定はホスト特権が必要なデバイス操作です。

| 要件 | コマンド / 条件 |
|---|---|
| MIG モードを有効化 | `sudo nvidia-smi -i 0 -mig 1`（昇格した権限が必要） |
| カード上で他の処理がない | すべての GPU プロセスを止める必要があり、そうでなければ `In use by another client` になる |
| デバイスのリセット | Hopper より前では必要。Hopper 以降は不要 |
| インスタンスの作成 | `nvidia-smi mig -cgi <profile> -i 0` |

Runpod のテナントはこのどれも持っていません。Pod と Serverless の worker はコンテナで、Instant Cluster もそうです。Runpod はそれを [*"Containerized: Runs on Docker"*](https://www.runpod.io/blog/bare-metal-vs-instant-clusters-whats-best-for-your-ai-workload) と説明しています。あなたはホストの root ではなく、他のテナントのプロセスを止めることも、共有デバイスをリセットすることもできません。

同じ Pod で試しました。コンテナは uid 0 で動いていますが、`cap_sys_admin` はありません。

```
$ nvidia-smi -i 0 -mig 1
Unable to enable MIG Mode for GPU 00000000:90:00.0: Insufficient Permissions
```

`mig.mode.pending` は `Disabled` のままでした。コンテナ内の root はデバイス上の root ではありません。

**クラスタでもこれは変わりません。** マルチノードで増えるのは GPU であって、権限ではありません。それが変わる層は **Bare Metal** で、*"full system access or specialized configurations"* を必要とするチーム向けと位置づけられています。

| 層 | 形態 | `nvidia-smi -mig 1` を実行できるか |
|---|---|---|
| Serverless | コンテナ | いいえ |
| Pod | コンテナ | いいえ（試した結果、`Insufficient Permissions`） |
| Instant Cluster | コンテナ（Docker）、2–8 ノード | いいえ |
| Bare Metal | 物理サーバー、コンテナ層なし | 可能性が出てくるのはこの層 |

Instant Cluster で提供される GPU（B200、H200、H100、A100）はすべて MIG 対応のシリコンです。妨げているのはアクセス層であって、ハードウェアではありません。

<div class="note" markdown="1">
ここでは Bare Metal を検証していません。この主張は Runpod 自身の位置づけに基づくもので、実際に借りてテストしたマシンに基づくものではありません。
</div>

### 一部だけ必要で、合う SKU がない場合

MIG はカードを共有する方法の 1 つで、ハードウェアで強制された分離を提供する唯一の方法です。それが使えない場合、代替手段は分離性と引き換えに入手しやすさを得ることになります。

| 方法 | 分離 | 現在 Runpod で使えるか |
|---|---|---|
| MIG SKU を買う | ハードウェア（独立したメモリと障害ドメイン） | はい、RTX PRO 6000 のみ |
| 1 つの worker プロセスで複数モデル | なし（1 回の OOM ですべて落ちる） | はい、普通の Python |
| 並行 handler（`concurrency_modifier`） | なし（同じプロセス、同じメモリ） | はい、[Worker SDK]({{ '/sdk/worker/' | relative_url }}) を参照 |
| CUDA MPS | 部分的（共有コンテキスト、クライアントごとの割り当て上限は任意） | はい（デーモンは Pod 内で動作、下記参照） |
| 小さいカードを借りるだけ | 完全（別のマシン） | はい、RTX 3070 8GB から |

最後の行は見落とされがちです。カタログは 8GB・$0.13/hr からあり、小さいカードを丸ごと借りるほうが、大きなカードを分割するより簡単で安いことがよくあります。

### Pod 内での CUDA MPS

CUDA MPS は追加の設定なしで Pod 内で動きます。イメージに `nvidia-cuda-mps-control` が入っています。同じ Pod の GPU 0 で測定しました。

| 確認項目 | 結果 |
|---|---|
| `nvidia-cuda-mps-control -d` | 起動、exit 0 |
| `torch` の matmul プロセス 2 つ | どちらもタイプ `M+C` として、`nvidia-cuda-mps-server` と並んで表示 |
| `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT="0=2G"`、4 GiB を割り当て | `CUDA out of memory` |
| 同じ上限で 1 GiB を割り当て | 割り当て成功 |
| 同じ上限でデーモンを止めて 4 GiB を割り当て | 割り当て成功（上限は MPS によるもの） |

デーモンを起動する前に `CUDA_MPS_PIPE_DIRECTORY` と `CUDA_MPS_LOG_DIRECTORY` を書き込み可能なパスに設定し、クライアントにも同じ値を渡してください。この上限は割り当てを制限するもので、メモリ保護ではありません。障害を起こした 1 つのクライアントが他を巻き込んで落とすことは依然としてありえます。

### ノードをまたぐ場合

[Instant Clusters](https://docs.runpod.io/instant-clusters) は 2–8 ノード、16–64 GPU までスケールし、それより大きな構成は個別の相談になります。

| GPU | ノード間帯域幅 | ノード数 |
|---|---|---|
| B200 | 3200 Gbps | 2–8 |
| H200 | 3200 Gbps | 2–8 |
| H100 | 3200 Gbps | 2–8 |
| A100 | 1600 Gbps | 2–8 |

ノード間のトラフィックは `ens1`–`ens8` インターフェースを通り、プライマリノードは `eth0` を通じて外部に出ます。

<div class="warn" markdown="1">
Runpod のクラスタのドキュメントは、インターコネクト技術の名前を一度も挙げていません。InfiniBand/RDMA クラスの帯域幅の数値は示していますが、InfiniBand、RDMA、GPUDirect、NVLink のいずれもどこにも書かれていません。フレームワークがそれを知る必要がある場合（NCCL は必要とします）、ドキュメントからではなく実行時に判定してください。
</div>

### ここで検証したこと

| 主張 | 方法 |
|---|---|
| GPU タイプは 48 種類、うち 2 つが MIG SKU | ライブのカタログ照会 |
| `POST /pods` にトポロジーのフィールドはない | 公開 OpenAPI 仕様、33 プロパティを列挙 |
| REST は 23 パスで、ビルドやパーティションの制御はない | 同じ仕様 |
| MIG には root、プロセスの停止、Hopper より前ではリセットが必要 | NVIDIA のドキュメント |
| `topo -m` の凡例 | NVIDIA のドキュメント |
| クラスタは Docker コンテナ | Runpod 自身の比較ページ |
| Runpod ホストでの実際の `topo -m` 出力 | 2026-11-05 に実行（2× A100 SXM、`NV12`、GPU 間コピー 276 GB/s） |
| Pod 内での `nvidia-smi -mig 1` | 2026-11-05 に実行（`Insufficient Permissions`） |
| Bare Metal で MIG が可能 | **未実行**（ベンダーの位置づけのみ） |
| Runpod コンテナ内での MPS | 2026-11-05 に実行（`M+C` クライアント、クライアントごとの上限が有効） |

[リポジトリの完全なリファレンス →](https://github.com/litkhai/runpod-hols/blob/main/gpu-topology/README.md)

</div>
