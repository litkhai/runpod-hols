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

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

<div class="note" markdown="1">
**状态：待定。** 占位页面。下面只勾勒了范围；尚未编写任何实验。
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) 是 Runpod 的多节点产品：带高速互连的全托管集群，用于分布式训练和大规模推理。

| 属性 | 值 |
|---|---|
| GPU | B200, H200, H100, A100 |
| 集群规模 | 2–8 个节点（16–64 块 GPU）；通过销售最多可达 512 块 GPU |
| 互连 | 节点间 1600–3200 Gbps，以 `ens1`–`ens8` 暴露 |
| 框架 | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### 可能的实验

| 实验 | 内容 |
|---|---|
| 01-pytorch-distributed | 多节点 `torchrun`，通过高速接口运行 NCCL |
| 02-slurm-cluster | 部署托管 Slurm 集群并提交作业 |
| 03-axolotl-finetune | 用 Axolotl 进行多节点 LLM 微调 |

### 为什么暂缓

Instant Clusters 比单个 Pod 贵得多——你一次租用多个多 GPU 节点，并按整个集群计费。应先把 Serverless 和 Pod 路线做扎实，因为集群工作大体上就是把 Pod 工作流成倍放大，再叠加分布式训练的问题。

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
**状態：未定。** プレースホルダーです。範囲を下に描いただけで、ラボはまだ書いていません。
</div>

[Instant Clusters](https://docs.runpod.io/instant-clusters) は Runpod のマルチノード製品です。分散学習と大規模推論のための、高速インターコネクトを備えたフルマネージドのクラスタです。

| 項目 | 値 |
|---|---|
| GPU | B200, H200, H100, A100 |
| クラスタ規模 | 2–8 ノード（GPU 16–64 基）。営業経由で最大 512 GPU |
| インターコネクト | ノード間 1600–3200 Gbps、`ens1`–`ens8` として公開 |
| フレームワーク | PyTorch distributed, TensorFlow, Slurm, Axolotl |

### 候補のラボ

| ラボ | 内容 |
|---|---|
| 01-pytorch-distributed | マルチノードの `torchrun`、高速インターフェース上の NCCL |
| 02-slurm-cluster | マネージド Slurm クラスタをデプロイしてジョブを投入 |
| 03-axolotl-finetune | Axolotl によるマルチノードの LLM ファインチューニング |

### 後回しにしている理由

Instant Clusters は単一の Pod よりかなり高価です。マルチ GPU ノードを複数台まとめて借り、クラスタ全体に対して課金されます。クラスタの作業はおおむね Pod のワークフローを何倍にもして、その上に分散学習の問題を重ねたものなので、まず Serverless と Pod のトラックを固めるべきです。

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
