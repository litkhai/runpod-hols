# Cluster Lab 01 — PyTorch Distributed: `torchrun` and NCCL

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** measure how fast GPUs exchange gradients, first inside one Pod, then across the nodes of an Instant Cluster, and see what that does to data-parallel training.

**Time:** ~15 minutes per Pod · **Cost:** stage 1 about USD 0.40 on 2026-11-07 (two Pods, 7 and 3 minutes); stage 2 capped at USD 50 ([#52](https://github.com/litkhai/runpod-hols/issues/52))

### Files

| File | Role |
|---|---|
| `nccl_bench.py` | All-reduce sweep, 1 MiB – 1 GiB, over NCCL; reports `algbw` and `busbw` with the nccl-tests definitions |
| `ddp_train.py` | 101 M-parameter MLP on synthetic data under `DistributedDataParallel`; about 400 MB of fp32 gradients to all-reduce per step |
| `run.sh` | Runs inside a Pod or on every cluster node: topology (`nvidia-smi topo -m`, interfaces), then `nccl_bench.py`, then `ddp_train.py` on 1 GPU and on all GPUs |
| `lab.py` | Stage 1 over the REST API: create a multi-GPU Pod, copy the scripts, run, fetch `results/`, delete |
| `cluster.py` | Stage 2 over GraphQL: wait for stock, create the cluster, watchdog delete at 75 min, run both nodes, fetch, delete |
| `results/<tag>/` | What each run produced |

On a cluster, Runpod sets `NUM_NODES`, `NUM_TRAINERS`, `NODE_RANK`, `PRIMARY_ADDR` and `PRIMARY_PORT`; `run.sh` passes them to `torchrun` and sets `NCCL_SOCKET_IFNAME=ens1`, because `eth0` (172.x) is for internet traffic only ([configuration](https://docs.runpod.io/instant-clusters/configuration)). On a single Pod those variables are absent and it runs one node.

### Stage 1 — one Pod, two GPUs

```bash
cd cluster/01-pytorch-distributed
python3 lab.py create                                  # 2x RTX 4090, Secure Cloud
python3 lab.py show                                    # wait for the SSH line
python3 lab.py push && python3 lab.py run 2x4090 && python3 lab.py pull
python3 lab.py delete
python3 lab.py create --gpu "NVIDIA A100-SXM4-80GB"     # then the same with tag 2xA100SXM
```

Image `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404` (torch 2.9.1, NCCL 2.27.5).

| | 2x RTX 4090 | 2x A100 SXM 80GB |
|---|---|---|
| Price | USD 1.78/hr | USD 3.58/hr |
| Link between the GPUs (`topo -m`) | `SYS`: PCIe across two NUMA nodes | `NV12`: 12 NVLinks |
| NCCL transport (log) | `SHM/direct` — through host memory | `P2P/CUMEM/read` — GPU to GPU |
| all-reduce `busbw`, 1 MiB | 10.9 GB/s | 18.2 GB/s |
| all-reduce `busbw`, 1 GiB | **15.6 GB/s** | **201.0 GB/s** |
| DDP, 1 GPU | 39,453 samples/s (6.5 ms/step) | 23,132 samples/s (11.1 ms/step) |
| DDP, 2 GPUs | 16,244 samples/s (31.5 ms/step) | 41,871 samples/s (12.2 ms/step) |
| Scaling efficiency (2 GPUs / 2 × 1 GPU) | **0.21** | **0.91** |

What the numbers say:

- **Two RTX 4090s trained 2.4× slower than one.** Each step all-reduces about 400 MB of gradients; at 15.6 GB/s that alone is about 26 ms, against 6.5 ms of compute. The two cards sat on different NUMA nodes (`SYS`), and consumer GeForce cards do not do GPU-to-GPU P2P, so NCCL staged the data through host shared memory.
- **The A100 pair scaled at 91%.** Over NVLink the same 400 MB moves in about 2 ms, so a step grew only from 11.1 to 12.2 ms.
- **The single A100 was slower than the single 4090** on this model: the script runs plain fp32 matrix multiplies with TF32 off (the PyTorch default), where the 4090 has more fp32 throughput. The A100's case is TF32/BF16 and the link, not fp32.
- **GPU utilization does not show it.** During the 2x 4090 run the console showed both GPUs at 100% (screenshot below) while most of each step was waiting on the transfer: NCCL kernels occupy the GPU while they wait.
- Per dollar, one RTX 4090 (39,453 samples/s at USD 0.89/hr) beat both pairs for this model. More GPUs pay only when the link keeps up with the gradient size.

Raw files: [`results/2x4090/`](./results/2x4090/), [`results/2xA100SXM/`](./results/2xA100SXM/).

![Pod deploy form with RTX 4090 and GPU count 2](../../docs/assets/img/cluster/pod-deploy-2gpu.webp)
![Pod Telemetry during the 2x RTX 4090 DDP run: both GPUs at 100%](../../docs/assets/img/cluster/pod-telemetry-2x4090.webp)

### Stage 2 — Instant Cluster, 2 nodes × 8 GPUs

Created in the console (**Clusters → Create cluster**) or over GraphQL: the REST API has no cluster endpoints, but `createCluster` and `deleteCluster` exist (found 2026-11-07; introspection is off, so the input fields below were read from validation errors). Pricing read from the form on 2026-11-07: A100 SXM USD 2.15 per GPU-hour, USD 34.37/hr for the smallest cluster (2 Pods × 8 GPUs, 1600 Gbps between nodes); H100 SXM USD 4.79 (USD 76.61/hr); H200 USD 6.35; B200 USD 9.59; B300 USD 10.79.

**On 2026-11-07 every type was Unavailable**, while single A100 SXM and H100 SXM Pods could be deployed. The console reads availability from GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }`; `stockStatus` is `null` when the form says Unavailable. That evening A100 SXM showed `Available` from about 19:29 to 19:36 KST and was gone again by 19:46: stock comes and goes within minutes, so waiting for it is a job for a script.

![Create cluster form: every GPU type Unavailable](../../docs/assets/img/cluster/instant-cluster-unavailable.webp)

`cluster.py` does the whole stage unattended:

```bash
python3 cluster.py stock                      # stockStatus and price per GPU-hour
python3 cluster.py auto 2x8xA100SXM --hours 48 # wait for stock, then everything below
```

`auto` checks stock every 2 minutes; when A100 SXM is available it calls

```graphql
createCluster(input: {clusterName: "hol-cluster-01", gpuTypeId: "NVIDIA A100-SXM4-80GB", podCount: 2,
  gpuCountPerPod: 8, type: TRAINING, imageName: "runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404",
  containerDiskInGb: 50, volumeInGb: 0, ports: "22/tcp", startSsh: true}) { id pods { id } }
```

(`type` takes `TRAINING` or `SLURM`), starts a detached watchdog that runs `deleteCluster(input: {id})` 75 minutes later whatever happens, waits for SSH on both nodes, runs `run.sh` on both at once (the cluster variables are read from the container's PID 1, since an SSH session does not inherit them), fetches `results/`, and deletes the cluster. It refuses to create anything above USD 40/hr. Manual steps: `create`, `show`, `push`, `run <tag>`, `pull`, `delete`.

---

## 한국어

**목표:** GPU 끼리 기울기를 얼마나 빨리 주고받는지 Pod 한 대 안에서, 그다음 Instant Cluster 의 노드 사이에서 재고, 그것이 데이터 병렬 학습에 어떤 영향을 주는지 본다.

**시간:** Pod 당 약 15분 · **비용:** 1단계는 2026-11-07 기준 약 USD 0.40 (Pod 두 대, 7분과 3분). 2단계는 상한 USD 50 ([#52](https://github.com/litkhai/runpod-hols/issues/52))

### 파일

| 파일 | 역할 |
|---|---|
| `nccl_bench.py` | NCCL all-reduce 를 1 MiB – 1 GiB 로 측정. nccl-tests 와 같은 정의의 `algbw`, `busbw` |
| `ddp_train.py` | 합성 데이터로 도는 1억 1백만 파라미터 MLP, `DistributedDataParallel`. 스텝마다 fp32 기울기 약 400 MB 를 all-reduce |
| `run.sh` | Pod 안 또는 클러스터의 모든 노드에서 실행: 토폴로지(`nvidia-smi topo -m`, 인터페이스), `nccl_bench.py`, `ddp_train.py` 1 GPU 와 전체 GPU |
| `lab.py` | REST API 로 하는 1단계: 멀티 GPU Pod 생성, 스크립트 복사, 실행, `results/` 회수, 삭제 |
| `cluster.py` | GraphQL 로 2단계: 재고 대기, 클러스터 생성, 75분 감시 삭제, 두 노드 실행, 회수, 삭제 |
| `results/<tag>/` | 실행마다 나온 결과 |

클러스터에서는 Runpod 이 `NUM_NODES`, `NUM_TRAINERS`, `NODE_RANK`, `PRIMARY_ADDR`, `PRIMARY_PORT` 를 넣어 준다. `run.sh` 는 이를 `torchrun` 에 넘기고 `NCCL_SOCKET_IFNAME=ens1` 을 설정한다. `eth0`(172.x) 는 인터넷용이기 때문이다 ([configuration](https://docs.runpod.io/instant-clusters/configuration)). 단일 Pod 에서는 이 변수가 없으므로 노드 1개로 돈다.

### 1단계 — Pod 한 대, GPU 두 장

```bash
cd cluster/01-pytorch-distributed
python3 lab.py create                                  # RTX 4090 두 장, Secure Cloud
python3 lab.py show                                    # SSH 줄이 나올 때까지
python3 lab.py push && python3 lab.py run 2x4090 && python3 lab.py pull
python3 lab.py delete
python3 lab.py create --gpu "NVIDIA A100-SXM4-80GB"     # 이어서 태그 2xA100SXM 로 같은 순서
```

이미지 `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404` (torch 2.9.1, NCCL 2.27.5).

| | RTX 4090 두 장 | A100 SXM 80GB 두 장 |
|---|---|---|
| 가격 | USD 1.78/hr | USD 3.58/hr |
| GPU 사이 연결 (`topo -m`) | `SYS`: NUMA 노드 두 개에 걸친 PCIe | `NV12`: NVLink 12개 |
| NCCL 전송 방식 (로그) | `SHM/direct` — 호스트 메모리 경유 | `P2P/CUMEM/read` — GPU 간 직접 |
| all-reduce `busbw`, 1 MiB | 10.9 GB/s | 18.2 GB/s |
| all-reduce `busbw`, 1 GiB | **15.6 GB/s** | **201.0 GB/s** |
| DDP, GPU 1장 | 초당 39,453 샘플 (스텝 6.5 ms) | 초당 23,132 샘플 (스텝 11.1 ms) |
| DDP, GPU 2장 | 초당 16,244 샘플 (스텝 31.5 ms) | 초당 41,871 샘플 (스텝 12.2 ms) |
| 확장 효율 (2장 / 2 × 1장) | **0.21** | **0.91** |

숫자가 말하는 것:

- **RTX 4090 두 장이 한 장보다 2.4배 느렸다.** 스텝마다 기울기 약 400 MB 를 all-reduce 하는데, 15.6 GB/s 로는 그것만 약 26 ms 다. 계산은 6.5 ms 였다. 두 카드는 서로 다른 NUMA 노드에 있었고(`SYS`), GeForce 카드는 GPU 간 P2P 를 하지 않으므로 NCCL 이 호스트 공유 메모리를 거쳐 보냈다.
- **A100 두 장은 91% 로 확장됐다.** NVLink 로는 같은 400 MB 가 약 2 ms 에 오가므로 스텝이 11.1 ms 에서 12.2 ms 로만 늘었다.
- **이 모델에서는 A100 한 장이 4090 한 장보다 느렸다.** 스크립트는 TF32 를 끈 (PyTorch 기본값) 순수 fp32 행렬곱인데, fp32 처리량은 4090 이 더 높다. A100 의 강점은 TF32/BF16 과 링크이지 fp32 가 아니다.
- **GPU 사용률로는 보이지 않는다.** 4090 두 장 실행 중 콘솔은 두 GPU 모두 100% 로 보여줬지만(아래 캡처) 실제로는 스텝 대부분이 전송 대기였다. NCCL 커널은 기다리는 동안에도 GPU 를 점유한다.
- 달러당으로는 이 모델에서 RTX 4090 한 장(USD 0.89/hr 에 초당 39,453)이 두 조합보다 나았다. GPU 를 늘리는 것은 링크가 기울기 크기를 감당할 때만 이득이다.

원본: [`results/2x4090/`](./results/2x4090/), [`results/2xA100SXM/`](./results/2xA100SXM/).

![RTX 4090, GPU count 2 를 고른 Pod 배포 화면](../../docs/assets/img/cluster/pod-deploy-2gpu.webp)
![RTX 4090 두 장 DDP 실행 중 Pod Telemetry: 두 GPU 모두 100%](../../docs/assets/img/cluster/pod-telemetry-2x4090.webp)

### 2단계 — Instant Cluster, 노드 2개 × GPU 8장

콘솔 (**Clusters → Create cluster**) 이나 GraphQL 로 만든다. REST API 에는 클러스터 엔드포인트가 없지만 `createCluster`, `deleteCluster` 가 있다 (2026-11-07 확인. 인트로스펙션이 꺼져 있어 아래 입력 필드는 검증 오류 메시지로 알아냈다). 2026-11-07 화면의 가격: A100 SXM GPU 시간당 USD 2.15, 가장 작은 클러스터(Pod 2개 × GPU 8장, 노드 간 1600 Gbps) 시간당 USD 34.37. H100 SXM USD 4.79 (시간당 USD 76.61), H200 USD 6.35, B200 USD 9.59, B300 USD 10.79.

**2026-11-07 에는 모든 종류가 Unavailable 이었다.** 같은 시각 A100 SXM, H100 SXM 단일 Pod 는 배포할 수 있었다. 콘솔은 가용 여부를 GraphQL `gpuTypes { lowestPrice(input: {isCluster: true, podCount: 2, gpuCount: 8, …}) { stockStatus } }` 로 읽고, 화면이 Unavailable 일 때 `stockStatus` 는 `null` 이다. 같은 날 저녁 A100 SXM 이 한국 시간 약 19:29–19:36 에 `Available` 이었다가 19:46 에는 다시 사라졌다. 재고는 몇 분 단위로 나고 빠지므로, 기다리는 일은 스크립트에 맡긴다.

![Create cluster 화면: 모든 GPU 종류가 Unavailable](../../docs/assets/img/cluster/instant-cluster-unavailable.webp)

`cluster.py` 가 이 단계를 사람 없이 끝까지 진행한다:

```bash
python3 cluster.py stock                      # stockStatus 와 GPU 시간당 가격
python3 cluster.py auto 2x8xA100SXM --hours 48 # 재고를 기다렸다가 아래를 모두 진행
```

`auto` 는 2분마다 재고를 확인하고, A100 SXM 이 나오면 위의 영어 절에 있는 `createCluster` 를 호출한다 (`type` 은 `TRAINING` 또는 `SLURM`). 그다음 무슨 일이 있어도 75분 뒤 `deleteCluster(input: {id})` 를 부르는 분리된 감시 프로세스를 띄우고, 두 노드의 SSH 를 기다려 `run.sh` 를 동시에 돌린다 (SSH 세션은 클러스터 변수를 물려받지 않으므로 컨테이너 PID 1 에서 읽는다). 이어서 `results/` 를 받아 오고 클러스터를 지운다. 시간당 USD 40 을 넘는 것은 만들지 않는다. 수동 단계: `create`, `show`, `push`, `run <tag>`, `pull`, `delete`.
