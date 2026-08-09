---
layout: default
title: Cluster
permalink: /cluster/
---

# Cluster

<div class="lang" data-lang="en" markdown="1">

## English

<div class="note" markdown="1">
**Status: TBD.** Placeholder. Scope is sketched below; no labs written yet.
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) are Runpod's multi-node offering: fully managed clusters with high-speed interconnect for distributed training and large-scale inference.

| Property | Value |
|---|---|
| GPUs | B200, H200, H100, A100 |
| Cluster size | 2–8 nodes (16–64 GPUs); up to 512 GPUs via sales |
| Interconnect | 1600–3200 Gbps between nodes, exposed as `ens1`–`ens8` |
| Frameworks | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### Possible labs

| Lab | Contents |
|---|---|
| 01-pytorch-distributed | Multi-node `torchrun`, NCCL over the high-speed interfaces |
| 02-slurm-cluster | Deploy a managed Slurm cluster and submit a job |
| 03-axolotl-finetune | Multi-node LLM fine-tuning with Axolotl |

### Why this is deferred

Instant Clusters are considerably more expensive than a single Pod — you lease multiple multi-GPU nodes at once and are billed for the whole cluster. The Serverless and Pod tracks should be solid first, since cluster work is mostly the Pod workflow multiplied, with distributed-training concerns layered on.

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
**상태: TBD.** 자리만 잡아둔 상태입니다. 아래에 범위만 정리했고 실습은 아직 없습니다.
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) 는 Runpod 의 다중 노드 제품입니다. 분산 학습과 대규모 추론을 위한, 고속 인터커넥트를 갖춘 완전관리형 클러스터입니다.

| 항목 | 값 |
|---|---|
| GPU | B200, H200, H100, A100 |
| 클러스터 규모 | 2~8 노드 (16~64 GPU), 영업 문의 시 최대 512 GPU |
| 인터커넥트 | 노드 간 1600~3200 Gbps, `ens1`~`ens8` 인터페이스로 노출 |
| 프레임워크 | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### 검토 중인 실습

| 실습 | 내용 |
|---|---|
| 01-pytorch-distributed | 다중 노드 `torchrun`, 고속 인터페이스 위의 NCCL |
| 02-slurm-cluster | 관리형 Slurm 클러스터 배포 및 잡 제출 |
| 03-axolotl-finetune | Axolotl 을 이용한 다중 노드 LLM 파인튜닝 |

### 보류하는 이유

Instant Cluster 는 Pod 한 대보다 비용이 상당히 큽니다. 멀티 GPU 노드를 여러 대 한꺼번에 임대하고 클러스터 전체에 대해 과금됩니다. 클러스터 작업은 대체로 Pod 워크플로를 여러 배로 늘리고 그 위에 분산 학습 이슈를 얹은 것에 가까우므로, Serverless 와 Pod 트랙을 먼저 탄탄히 다지는 편이 낫습니다.

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
