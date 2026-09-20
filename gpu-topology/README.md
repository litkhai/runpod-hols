# GPU Topology and Partitioning — NVLink, MIG, and What You Can Control

[English](#english) | [한국어](#한국어)

> NVLink and MIG decide two things about a GPU: how fast it can talk to its neighbours, and whether it can be split. Both are worth understanding on their own, independently of any provider. What Runpod does with them comes second — and the two answers are opposite.
>
> Concepts are from vendor documentation. The Runpod half is from the live GPU catalogue and the published REST OpenAPI spec; no multi-GPU machine was rented, and anything that would need one is marked as unverified.
>
> NVLink 와 MIG 는 GPU 에 대해 두 가지를 결정합니다. 옆의 GPU 와 얼마나 빠르게 대화하는가, 그리고 쪼갤 수 있는가. 둘 다 특정 제공사와 무관하게 그 자체로 알아둘 가치가 있는 개념이며, Runpod 이 이를 어떻게 제공하는지는 그 다음 이야기입니다. 두 답이 서로 반대입니다.
>
> 개념은 벤더 문서 기준입니다. Runpod 쪽은 살아있는 GPU 카탈로그와 발행된 REST OpenAPI 스펙에서 확인했으며, 멀티 GPU 머신은 빌리지 않았고 그것이 필요한 항목은 미검증으로 표시했습니다.

---

## English

## The concepts

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
| CUDA MPS | No | No |

That hardware isolation is the whole point — and the reason it cannot be set up from inside a container.

## How Runpod exposes them

### The short answer

| | Available? | Who controls it |
|---|---|---|
| **NVLink** | Yes, on SXM/NVL hardware | Nobody — it is a property of the machine you land on |
| **MIG** | Yes, as pre-cut SKUs | Runpod. You buy slices; you cannot cut them |

Both are *available* and neither is *configurable*. What you choose is a GPU type; the topology follows from it.

### What the API lets you control

`POST /pods` in the [published OpenAPI spec](https://rest.runpod.io/v1/openapi.json) has 33 properties. None of them mention interconnect, topology, NVLink, MIG, or partitioning. The GPU-related ones are:

| Property | Meaning |
|---|---|
| `gpuTypeIds` | Which GPU models are acceptable |
| `gpuCount` | How many to attach |
| `gpuTypePriority` | Whether to fall back on availability |
| `minRAMPerGPU`, `minVCPUPerGPU` | Host resources per GPU |

`POST /endpoints` is narrower still — it requires a `templateId` and carries no GPU-topology field at all. The whole REST surface is 23 paths, with nothing for builds, topology, or partitioning.

So the lever is SKU selection. Everything below is about reading that lever correctly.

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

And the ones that deliberately do not: **A100 PCIe** and **H100 PCIe**, same silicon, same VRAM, PCIe instead of NVLink.

> **The name is a hint, not a contract.** `B200` carries NVLink and says nothing about it, while `A100 PCIe` and `A100 SXM` differ only in the suffix. Runpod exposes no field asserting topology, so the name is all you have before boot — and it is not enough.

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

> Not verified here. Confirming this output costs a multi-GPU pod — 8×H100 runs into tens of dollars per hour — and this repo does not spend on GPU time without a reason. The command and the legend are documented; the output on a given Runpod host is not.

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
| `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` | PRO 6000 MIG 24GB | 24GB | 32 |
| `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 2g.48gb` | PRO 6000 MIG 48GB | 48GB | 16 |

Both are Secure Cloud only. The parent card, RTX PRO 6000 (96GB), is also sold whole.

Runpod's [announcement](https://www.runpod.io/blog/multi-instance-gpu-on-runpod) is explicit that this is their decision, not yours: *"Note that we will never time-slice or segment a GPU without being completely up front that we are doing it. If you pay for the whole card, you get the whole card, full stop."* Serverless endpoints can opt out with a checkbox under **Advanced** in the endpoint configuration. Pods are stated as coming later.

> **The blog undercounts.** It describes 24GB chunks only, but the catalogue carries both `1g.24gb` and `2g.48gb`. The API is ahead of the announcement — check the catalogue, not the blog post.

### Why you cannot slice it yourself

Not a licensing or silicon limit. MIG configuration is a host-privileged device operation:

| Requirement | Command / condition |
|---|---|
| Enable MIG mode | `sudo nvidia-smi -i 0 -mig 1` — elevated privileges |
| No other work on the card | All GPU processes must be stopped, or you get `In use by another client` |
| Device reset | Required pre-Hopper; Hopper and newer no longer need it |
| Create instances | `nvidia-smi mig -cgi <profile> -i 0` |

A Runpod tenant has none of these. Pods and Serverless workers are containers; Instant Clusters are too — Runpod describes them as [*"Containerized: Runs on Docker"*](https://www.runpod.io/blog/bare-metal-vs-instant-clusters-whats-best-for-your-ai-workload). You are not host root, you cannot stop another tenant's processes, and you cannot reset a shared device.

**Clusters do not change this.** Multi-node gets you more GPUs, not more privilege. The tier that does is **Bare Metal**, which Runpod positions for teams needing *"full system access or specialized configurations"*.

The irony is worth stating plainly: every GPU offered in Instant Clusters — B200, H200, H100, A100 — is MIG-capable silicon. What stops you is the access tier, not the hardware.

| Tier | Form | Can you run `nvidia-smi -mig 1`? |
|---|---|---|
| Serverless | Container | No |
| Pod | Container | No |
| Instant Cluster | Container (Docker), 2–8 nodes | No |
| Bare Metal | Physical server, no container layer | This is the tier where it becomes plausible |

> Bare Metal is not verified here. The claim rests on Runpod's own positioning, not on a machine rented and tested.

### If you need a fraction and no SKU fits

MIG is one way to share a card, and the only one giving hardware-enforced isolation. When it is not available to you, the alternatives trade isolation for availability:

| Approach | Isolation | Works on Runpod today |
|---|---|---|
| Buy the MIG SKU | Hardware — separate memory and fault domains | Yes, RTX PRO 6000 only |
| Several models in one worker process | None — one OOM takes down everything | Yes, plain Python |
| Concurrent handler (`concurrency_modifier`) | None — same process, same memory | Yes, see [Worker SDK](../sdk/worker.md) |
| CUDA MPS | Partial — shared context, no memory cap | Needs the MPS daemon inside your container; untested here |
| Just rent a smaller card | Total — it is a different machine | Yes, RTX 3070 8GB upward |

The last row is the one people skip. The catalogue runs from 8GB at $0.13/hr, and a smaller whole card is often simpler and cheaper than partitioning a large one.

### Across nodes

[Instant Clusters](https://docs.runpod.io/instant-clusters) scale to 2–8 nodes, 16–64 GPUs, with larger deployments by arrangement:

| GPU | Inter-node bandwidth | Nodes |
|---|---|---|
| B200 | 3200 Gbps | 2–8 |
| H200 | 3200 Gbps | 2–8 |
| H100 | 3200 Gbps | 2–8 |
| A100 | 1600 Gbps | 2–8 |

Inter-node traffic runs over interfaces `ens1`–`ens8`; the primary node reaches the outside through `eth0`.

> Runpod's cluster documentation never names the interconnect technology. It quotes bandwidth figures in the InfiniBand/RDMA class but does not say InfiniBand, RDMA, GPUDirect, or NVLink anywhere. If your framework needs to know — and NCCL does — determine it at runtime rather than from the docs.

### What is verified here

| Claim | How |
|---|---|
| 48 GPU types; two are MIG SKUs | Live catalogue query against this account |
| `POST /pods` has no topology field | Published OpenAPI spec, 33 properties enumerated |
| REST surface is 23 paths, no build or partition control | Same spec |
| MIG needs root, stopped processes, reset pre-Hopper | NVIDIA documentation |
| `topo -m` legend | NVIDIA documentation |
| Clusters are Docker containers | Runpod's own comparison page |
| Actual `topo -m` output on a Runpod host | **Not run** — needs a paid multi-GPU pod |
| Bare Metal permitting MIG | **Not run** — vendor positioning only |
| MPS inside a Runpod container | **Not run** |

---

## 한국어

## 개념

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
| CUDA MPS | 없음 | 안 됨 |

그 하드웨어 격리가 MIG 의 존재 이유이자, 컨테이너 안에서 설정할 수 없는 이유입니다.

## Runpod 은 이를 어떻게 제공하는가

### 짧은 답

| | 되는가 | 누가 정하는가 |
|---|---|---|
| **NVLink** | 됩니다. SXM/NVL 하드웨어에서 | 아무도 아닙니다 — 내가 배정받은 머신의 속성입니다 |
| **MIG** | 됩니다. 미리 잘린 SKU 로 | Runpod. 슬라이스를 사는 것이지 자르는 게 아닙니다 |

둘 다 *제공은* 되고 둘 다 *설정 대상은* 아닙니다. 내가 고르는 것은 GPU 타입이고, 토폴로지는 거기서 따라옵니다.

### API 로 제어할 수 있는 것

[발행된 OpenAPI 스펙](https://rest.runpod.io/v1/openapi.json)의 `POST /pods` 는 속성이 33개인데, interconnect·topology·NVLink·MIG·partition 관련 항목이 하나도 없습니다. GPU 관련은 이게 전부입니다.

| 속성 | 의미 |
|---|---|
| `gpuTypeIds` | 허용할 GPU 모델 |
| `gpuCount` | 붙일 개수 |
| `gpuTypePriority` | 가용성에 따라 대체할지 여부 |
| `minRAMPerGPU`, `minVCPUPerGPU` | GPU 당 호스트 자원 |

`POST /endpoints` 는 더 좁아서 `templateId` 를 요구할 뿐 GPU 토폴로지 필드가 아예 없습니다. REST 전체가 23개 경로이며 빌드·토폴로지·파티셔닝용 경로는 없습니다.

즉 레버는 SKU 선택 하나입니다. 아래는 그 레버를 제대로 읽는 방법입니다.

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

> **이름은 힌트지 계약이 아닙니다.** `B200` 은 NVLink 를 갖고도 이름에 아무 표시가 없고, `A100 PCIe` 와 `A100 SXM` 은 접미사만 다릅니다. Runpod 은 토폴로지를 알려주는 필드를 제공하지 않으므로 부팅 전에는 이름이 전부인데, 그것으로는 부족합니다.

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

> 여기서는 검증하지 않았습니다. 이 출력을 확인하려면 멀티 GPU Pod 을 띄워야 하고 8×H100 은 시간당 수십 달러입니다. 이 저장소는 이유 없이 GPU 시간에 돈을 쓰지 않습니다. 명령과 범례는 문서로 확인했지만, 특정 Runpod 호스트에서의 출력은 확인하지 않았습니다.

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
| `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb` | PRO 6000 MIG 24GB | 24GB | 32 |
| `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 2g.48gb` | PRO 6000 MIG 48GB | 48GB | 16 |

둘 다 Secure Cloud 전용입니다. 원본 카드인 RTX PRO 6000(96GB)도 통째로 판매됩니다.

Runpod [발표](https://www.runpod.io/blog/multi-instance-gpu-on-runpod)는 이것이 자기들 결정이지 사용자 결정이 아님을 분명히 합니다. *"Note that we will never time-slice or segment a GPU without being completely up front that we are doing it. If you pay for the whole card, you get the whole card, full stop."* Serverless 엔드포인트는 설정의 **Advanced** 에서 체크박스로 해제할 수 있고, Pod 은 추후 적용 예정이라고 합니다.

> **블로그가 과소 표기하고 있습니다.** 24GB 조각만 설명하지만 카탈로그에는 `1g.24gb` 와 `2g.48gb` 가 모두 있습니다. API 가 발표보다 앞서 있으니 블로그가 아니라 카탈로그를 보세요.

### 왜 직접 자를 수 없는가

라이선스나 실리콘 문제가 아닙니다. MIG 설정은 호스트 특권이 필요한 디바이스 조작입니다.

| 요구사항 | 명령 / 조건 |
|---|---|
| MIG 모드 활성화 | `sudo nvidia-smi -i 0 -mig 1` — 상승된 권한 필요 |
| 해당 카드에 다른 작업이 없을 것 | 모든 GPU 프로세스가 멈춰야 하며, 아니면 `In use by another client` |
| 디바이스 리셋 | Hopper 이전 세대는 필요. Hopper 이상은 불필요 |
| 인스턴스 생성 | `nvidia-smi mig -cgi <profile> -i 0` |

Runpod 테넌트에게는 이 중 아무것도 없습니다. Pod 과 Serverless 워커는 컨테이너이고, Instant Cluster 도 마찬가지입니다 — Runpod 이 직접 [*"Containerized: Runs on Docker"*](https://www.runpod.io/blog/bare-metal-vs-instant-clusters-whats-best-for-your-ai-workload) 라고 표현합니다. 호스트 root 가 아니고, 다른 테넌트의 프로세스를 멈출 수 없으며, 공유 디바이스를 리셋할 수 없습니다.

**Cluster 라고 달라지지 않습니다.** 멀티 노드는 GPU 를 더 주는 것이지 권한을 더 주는 게 아닙니다. 권한이 달라지는 계층은 **Bare Metal** 이고, Runpod 은 이를 *"full system access or specialized configurations"* 가 필요한 팀용으로 소개합니다.

역설은 분명히 적어둘 가치가 있습니다. Instant Cluster 에서 제공되는 GPU — B200, H200, H100, A100 — 는 **전부 MIG 가능한 실리콘**입니다. 막는 것은 하드웨어가 아니라 접근 계층입니다.

| 계층 | 형태 | `nvidia-smi -mig 1` 가능? |
|---|---|---|
| Serverless | 컨테이너 | 불가 |
| Pod | 컨테이너 | 불가 |
| Instant Cluster | 컨테이너(Docker), 2–8 노드 | 불가 |
| Bare Metal | 물리 서버, 컨테이너 계층 없음 | 가능해지는 계층 |

> Bare Metal 은 검증하지 않았습니다. 이 항목은 Runpod 의 제품 소개에 근거한 것이지 실제로 빌려서 시험해 본 결과가 아닙니다.

### 조각이 필요한데 맞는 SKU 가 없다면

MIG 는 카드를 나눠 쓰는 여러 방법 중 하나이며, 하드웨어로 격리가 보장되는 유일한 방법입니다. 쓸 수 없을 때의 대안은 격리를 가용성과 맞바꿉니다.

| 방법 | 격리 | 지금 Runpod 에서 |
|---|---|---|
| MIG SKU 구매 | 하드웨어 — 메모리와 장애 도메인이 분리 | 가능. RTX PRO 6000 한정 |
| 워커 프로세스 하나에 모델 여러 개 | 없음 — OOM 하나로 전부 죽음 | 가능. 평범한 Python |
| 동시 핸들러 (`concurrency_modifier`) | 없음 — 같은 프로세스, 같은 메모리 | 가능. [Worker SDK](../sdk/worker.md) 참조 |
| CUDA MPS | 부분적 — 컨텍스트 공유, 메모리 상한 없음 | 컨테이너 안에 MPS 데몬이 필요. 여기서는 미검증 |
| 그냥 더 작은 카드를 빌리기 | 완전 — 애초에 다른 머신 | 가능. RTX 3070 8GB 부터 |

마지막 줄을 다들 건너뜁니다. 카탈로그는 8GB $0.13/hr 부터 시작하고, 큰 카드를 쪼개는 것보다 작은 카드를 통째로 쓰는 쪽이 더 간단하고 싼 경우가 많습니다.

### 노드를 넘어갈 때

[Instant Clusters](https://docs.runpod.io/instant-clusters) 는 2–8 노드, 16–64 GPU 규모이며 그 이상은 별도 협의입니다.

| GPU | 노드 간 대역폭 | 노드 수 |
|---|---|---|
| B200 | 3200 Gbps | 2–8 |
| H200 | 3200 Gbps | 2–8 |
| H100 | 3200 Gbps | 2–8 |
| A100 | 1600 Gbps | 2–8 |

노드 간 트래픽은 `ens1`–`ens8` 인터페이스를 쓰고, 프라이머리 노드가 `eth0` 로 외부와 통신합니다.

> Runpod 의 클러스터 문서는 인터커넥트 기술 이름을 한 번도 쓰지 않습니다. InfiniBand/RDMA 급의 대역폭 수치를 제시하면서도 InfiniBand·RDMA·GPUDirect·NVLink 중 어느 것도 언급하지 않습니다. 프레임워크가 그것을 알아야 한다면 — NCCL 은 알아야 합니다 — 문서가 아니라 런타임에 판단하게 하세요.

### 여기서 검증한 것

| 주장 | 방법 |
|---|---|
| GPU 타입 48개, 그중 둘이 MIG SKU | 이 계정으로 카탈로그 실시간 조회 |
| `POST /pods` 에 토폴로지 필드 없음 | 발행된 OpenAPI 스펙, 속성 33개 전수 확인 |
| REST 전체 23개 경로, 빌드·파티션 제어 없음 | 같은 스펙 |
| MIG 는 root·프로세스 정지·Hopper 이전 리셋 필요 | NVIDIA 문서 |
| `topo -m` 범례 | NVIDIA 문서 |
| Cluster 는 Docker 컨테이너 | Runpod 자체 비교 페이지 |
| Runpod 호스트에서의 실제 `topo -m` 출력 | **미실행** — 유료 멀티 GPU Pod 필요 |
| Bare Metal 에서 MIG 가능 여부 | **미실행** — 벤더 소개 문구에만 근거 |
| Runpod 컨테이너 안에서의 MPS | **미실행** |
