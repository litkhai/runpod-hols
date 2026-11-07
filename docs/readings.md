---
layout: default
title: Readings
permalink: /readings/
---

# Readings

<div class="lang" data-lang="en" markdown="1">

## English

## Notes written here
{: #notes }

Concepts that need more than a link — written out, with the Runpod-specific part kept separate from the general one.

| Page | Covers |
|---|---|
| [GPU & LLM Basics]({{ '/readings/gpu-llm-basics/' | relative_url }}) | Hardware and roofline · precision · the four sizing formulas with calculators · serving · cost — each next to what these labs measured |
| [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) | What NVLink and MIG are · bandwidth and isolation · which of them Runpod lets you control |

## Background — GPU, training, inference, deployment
{: #background }

<div class="note" markdown="1">
Links, all published by Runpod. Competitor comparisons and marketing pieces are excluded. The rest is largely provider-agnostic — VRAM arithmetic, batching, precision trade-offs.
</div>

### GPU and memory

| Article | Topic |
|---|---|
| [GPU cloud servers for AI workloads](https://www.runpod.io/articles/guides/gpu-cloud-servers-for-ai-workloads) | The best single starting point: classifying a workload, calculating VRAM with actual formulas, then matching hardware to it |
| [Choosing a GPU for training vs inference](https://www.runpod.io/articles/comparison/choosing-a-gpu-for-training-vs-inference) | Why the right card differs depending on which you are doing |
| [GPU memory sizing for LLM inference](https://www.runpod.io/articles/guides/gpu-memory-sizing-guide-for-llm-inference) | Working out whether a model fits before you rent the machine |
| [Avoiding OOM crashes for large models](https://www.runpod.io/articles/guides/avoid-oom-crashes-for-large-models) | What runs out, and what to do about it |

### Training

| Article | Topic |
|---|---|
| [Inference vs training GPU guide](https://www.runpod.io/articles/guides/ai-inference-vs-training-gpu-guide) | The two workloads want different things from hardware |
| [FP16, BF16, FP8 and mixed precision](https://www.runpod.io/articles/guides/fp16-bf16-fp8-mixed-precision-speed-up-my-model-training) | Numeric formats, and what you trade for the speed |
| [Multi-GPU training](https://www.runpod.io/articles/guides/the-complete-guide-to-multi-gpu-training-scaling-ai-models-beyond-single-card-limitations) | Scaling past one card |
| [Multi-node cluster architecture](https://www.runpod.io/articles/guides/gpu-clusters-for-ai-multi-node-architecture) | Background for the Cluster track |
| [InfiniBand for distributed training](https://www.runpod.io/articles/guides/infiniband-for-distributed-ai-training) | Why interconnect bandwidth decides multi-node performance |

### Inference

| Article | Topic |
|---|---|
| [LLM inference from first principles](https://www.runpod.io/articles/guides/llm-inference-first-principles) | What actually happens per token, and where the time goes |
| [PagedAttention and continuous batching](https://www.runpod.io/articles/guides/vllm-pagedattention-continuous-batching) | The two ideas that make vLLM faster than a naive loop |
| [Inference optimisation playbook](https://www.runpod.io/articles/guides/llm-inference-optimization-playbook) | Levers for latency and throughput, in order |
| [Model quantization](https://www.runpod.io/articles/guides/ai-model-quantization-reducing-memory-usage-without-sacrificing-performance) | Trading precision for memory, and what it costs |
| [vLLM vs TensorRT-LLM](https://www.runpod.io/articles/comparison/vllm-vs-tensorrt-llm) | Choosing a serving engine |

### Deployment and cost

| Article | Topic |
|---|---|
| [Serverless vs Pods](https://www.runpod.io/articles/comparison/serverless-gpu-deployment-vs-pods) | The decision these labs split their tracks along |
| [Scaling up vs scaling out](https://www.runpod.io/articles/comparison/scaling-up-vs-scaling-out) | A bigger GPU or more of them |
| [Docker essentials for AI developers](https://www.runpod.io/articles/guides/docker-essentials-for-ai-developers) | Useful if the container side of the Serverless track feels unfamiliar |
| [Cloud GPU pricing](https://www.runpod.io/articles/guides/cloud-gpu-pricing) | How GPU time is actually billed |
| [Cutting your GPU bill](https://www.runpod.io/articles/guides/how-to-cut-your-gpu-bill) | Practical reductions, most of which apply anywhere |

## Runpod documentation
{: #runpod-docs }

**Before you start**

| Page | Why |
|---|---|
| [Welcome to Runpod](https://docs.runpod.io/overview) | The map. Ten minutes, and the rest makes more sense |
| [Concepts](https://docs.runpod.io/get-started/concepts) | Vocabulary — worker, endpoint, template, volume. Used everywhere without definition |
| [Product overview](https://docs.runpod.io/get-started/products) | "Explore Runpod's major offerings and find the right solution for your workload" — read if unsure whether you want Serverless or a Pod |

**Serverless**

| Page | Why |
|---|---|
| [Overview](https://docs.runpod.io/serverless/overview) | "Pay-as-you-go compute for AI models and compute-intensive workloads" |
| [Quickstart](https://docs.runpod.io/serverless/quickstart) | The official version of Lab 01 |
| [Handler functions](https://docs.runpod.io/serverless/workers/handler-functions) | The contract your code must satisfy. Pair it with [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| [Deploy from GitHub](https://docs.runpod.io/serverless/workers/github-integration) | The deploy path these labs use — note it omits the Build context field |
| [Endpoint settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations) | Reference for every setting on the create form |
| [Job states and metrics](https://docs.runpod.io/serverless/endpoints/job-states) | Read this before wondering why `/runsync` returned `IN_PROGRESS` |
| [Cached models](https://docs.runpod.io/serverless/endpoints/model-caching) | Why the model does not belong in your image. Behind Lab 02 |
| [Fitness checks](https://docs.runpod.io/serverless/development/fitness-checks) | Startup validation. Requires `runpod>=1.9.0` |
| [Local testing](https://docs.runpod.io/serverless/development/local-testing) | The loop that avoids a build cycle per change |
| [Concurrent handlers](https://docs.runpod.io/serverless/workers/concurrent-handler) | One worker, several requests — where `concurrency_modifier` earns its keep |
| [Optimize your endpoints](https://docs.runpod.io/serverless/development/optimization) | "Strategies to reduce latency and cost" |
| [Troubleshooting](https://docs.runpod.io/serverless/troubleshooting) | Worth skimming once so you recognise the failure when it happens |

**Pods**

| Page | Why |
|---|---|
| [Overview](https://docs.runpod.io/pods/overview) | What you actually get when you rent one |
| [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) | Matching GPU to workload rather than guessing |
| [Storage options](https://docs.runpod.io/pods/storage/types) | Container disk vs volume vs network volume. Confusing these is how work gets lost |

**Cost**

| Page | Why |
|---|---|
| [Serverless pricing](https://docs.runpod.io/serverless/pricing) | Why `workers_min = 0` matters |
| [Pods pricing](https://docs.runpod.io/pods/pricing) | Per-minute while running, plus storage on a stopped Pod |
| [Billing information](https://docs.runpod.io/references/billing-information) | Spending limits. Set one before your first lab that creates anything |

**Reference**

| Page | Why |
|---|---|
| [GPU types](https://docs.runpod.io/references/gpu-types) | What is available, and roughly what it costs |
| [Instant Clusters](https://docs.runpod.io/instant-clusters) | If the Cluster track interests you before it is written |

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

## 직접 쓴 글
{: #notes-ko }

링크 하나로 끝나지 않는 개념을 정리했습니다. 일반적인 내용과 Runpod 에 한정된 내용을 분리해 두었습니다.

| 문서 | 다루는 내용 |
|---|---|
| [GPU·LLM 기초]({{ '/readings/gpu-llm-basics/' | relative_url }}) | 하드웨어와 roofline · 정밀도 · 사이징 공식 네 개와 계산기 · 서빙 · 비용 — 각각을 이 실습들의 측정값과 나란히 |
| [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) | NVLink 와 MIG 가 무엇인가 · 대역폭과 격리 · Runpod 에서 제어 가능한 것은 무엇인가 |

## 배경 — GPU, 학습, 추론, 배포
{: #background-ko }

<div class="note" markdown="1">
링크 모음이며 모두 Runpod 이 발행한 자료입니다. 경쟁사 비교와 마케팅성 글은 제외했습니다. 나머지는 대체로 제공사와 무관한 내용입니다 — VRAM 계산, 배칭, 정밀도 트레이드오프.
</div>

### GPU 와 메모리

| 문서 | 주제 |
|---|---|
| [GPU cloud servers for AI workloads](https://www.runpod.io/articles/guides/gpu-cloud-servers-for-ai-workloads) | 출발점으로 가장 좋습니다. 워크로드 분류, 실제 공식으로 VRAM 계산, 그에 맞는 하드웨어 선택 |
| [Choosing a GPU for training vs inference](https://www.runpod.io/articles/comparison/choosing-a-gpu-for-training-vs-inference) | 무엇을 하느냐에 따라 적합한 카드가 달라지는 이유 |
| [GPU memory sizing for LLM inference](https://www.runpod.io/articles/guides/gpu-memory-sizing-guide-for-llm-inference) | 머신을 빌리기 전에 모델이 들어가는지 계산하기 |
| [Avoiding OOM crashes for large models](https://www.runpod.io/articles/guides/avoid-oom-crashes-for-large-models) | 무엇이 부족해지고, 어떻게 대응하는가 |

### 학습 (Training)

| 문서 | 주제 |
|---|---|
| [Inference vs training GPU guide](https://www.runpod.io/articles/guides/ai-inference-vs-training-gpu-guide) | 두 워크로드가 하드웨어에 요구하는 것이 다릅니다 |
| [FP16, BF16, FP8 and mixed precision](https://www.runpod.io/articles/guides/fp16-bf16-fp8-mixed-precision-speed-up-my-model-training) | 수치 형식과, 속도를 얻는 대가로 내주는 것 |
| [Multi-GPU training](https://www.runpod.io/articles/guides/the-complete-guide-to-multi-gpu-training-scaling-ai-models-beyond-single-card-limitations) | 카드 한 장을 넘어서기 |
| [Multi-node cluster architecture](https://www.runpod.io/articles/guides/gpu-clusters-for-ai-multi-node-architecture) | Cluster 트랙의 배경 지식 |
| [InfiniBand for distributed training](https://www.runpod.io/articles/guides/infiniband-for-distributed-ai-training) | 인터커넥트 대역폭이 다중 노드 성능을 결정하는 이유 |

### 추론 (Inference)

| 문서 | 주제 |
|---|---|
| [LLM inference from first principles](https://www.runpod.io/articles/guides/llm-inference-first-principles) | 토큰 하나마다 실제로 무슨 일이 일어나고 시간이 어디로 가는가 |
| [PagedAttention and continuous batching](https://www.runpod.io/articles/guides/vllm-pagedattention-continuous-batching) | vLLM 이 단순 루프보다 빠른 이유가 되는 두 아이디어 |
| [Inference optimisation playbook](https://www.runpod.io/articles/guides/llm-inference-optimization-playbook) | 지연시간과 처리량을 위한 수단들, 순서대로 |
| [Model quantization](https://www.runpod.io/articles/guides/ai-model-quantization-reducing-memory-usage-without-sacrificing-performance) | 정밀도를 메모리와 맞바꾸기, 그 비용 |
| [vLLM vs TensorRT-LLM](https://www.runpod.io/articles/comparison/vllm-vs-tensorrt-llm) | 서빙 엔진 선택 |

### 배포와 비용

| 문서 | 주제 |
|---|---|
| [Serverless vs Pods](https://www.runpod.io/articles/comparison/serverless-gpu-deployment-vs-pods) | 이 실습들이 트랙을 나눈 기준이 된 바로 그 결정 |
| [Scaling up vs scaling out](https://www.runpod.io/articles/comparison/scaling-up-vs-scaling-out) | 더 큰 GPU 하나인가, 여러 개인가 |
| [Docker essentials for AI developers](https://www.runpod.io/articles/guides/docker-essentials-for-ai-developers) | Serverless 트랙의 컨테이너 부분이 낯설다면 |
| [Cloud GPU pricing](https://www.runpod.io/articles/guides/cloud-gpu-pricing) | GPU 시간이 실제로 어떻게 과금되는가 |
| [Cutting your GPU bill](https://www.runpod.io/articles/guides/how-to-cut-your-gpu-bill) | 실용적인 절감 방법. 대부분 다른 곳에도 적용됩니다 |

## Runpod 공식 문서
{: #runpod-docs-ko }

**시작 전에**

| 문서 | 이유 |
|---|---|
| [Welcome to Runpod](https://docs.runpod.io/overview) | 전체 지도. 10분이면 나머지가 훨씬 잘 읽힙니다 |
| [Concepts](https://docs.runpod.io/get-started/concepts) | worker, endpoint, template, volume 같은 용어. 정의 없이 곳곳에서 쓰입니다 |
| [Product overview](https://docs.runpod.io/get-started/products) | "워크로드에 맞는 솔루션 찾기" — Serverless 와 Pod 중 무엇일지 모르겠다면 |

**Serverless**

| 문서 | 이유 |
|---|---|
| [Overview](https://docs.runpod.io/serverless/overview) | "AI 모델과 연산 집약 워크로드를 위한 종량제 컴퓨트" |
| [Quickstart](https://docs.runpod.io/serverless/quickstart) | Lab 01 의 공식 버전 |
| [Handler functions](https://docs.runpod.io/serverless/workers/handler-functions) | 내 코드가 지켜야 할 계약. [Worker SDK]({{ '/sdk/worker/' | relative_url }}) 와 함께 보세요 |
| [Deploy from GitHub](https://docs.runpod.io/serverless/workers/github-integration) | 이 실습들이 쓰는 배포 경로. 단 Build context 필드는 빠져 있습니다 |
| [Endpoint settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations) | 생성 화면의 모든 설정에 대한 레퍼런스 |
| [Job states and metrics](https://docs.runpod.io/serverless/endpoints/job-states) | `/runsync` 가 왜 `IN_PROGRESS` 를 주는지 궁금해지기 전에 |
| [Cached models](https://docs.runpod.io/serverless/endpoints/model-caching) | 모델을 이미지에 넣지 않는 이유. Lab 02 의 근거 |
| [Fitness checks](https://docs.runpod.io/serverless/development/fitness-checks) | 기동 시 검증. `runpod>=1.9.0` 필요 |
| [Local testing](https://docs.runpod.io/serverless/development/local-testing) | 변경마다 빌드하지 않아도 되는 루프 |
| [Concurrent handlers](https://docs.runpod.io/serverless/workers/concurrent-handler) | 워커 하나로 여러 요청 — `concurrency_modifier` 가 쓸모를 발휘하는 지점 |
| [Optimize your endpoints](https://docs.runpod.io/serverless/development/optimization) | "지연시간과 비용을 줄이는 전략" |
| [Troubleshooting](https://docs.runpod.io/serverless/troubleshooting) | 한 번 훑어두면 실제로 겪을 때 알아봅니다 |

**Pods**

| 문서 | 이유 |
|---|---|
| [Overview](https://docs.runpod.io/pods/overview) | 빌렸을 때 실제로 무엇을 받는가 |
| [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) | 추측 대신 워크로드에 GPU 맞추기 |
| [Storage options](https://docs.runpod.io/pods/storage/types) | 컨테이너 디스크 · 볼륨 · 네트워크 볼륨. 혼동하면 작업물을 잃습니다 |

**비용**

| 문서 | 이유 |
|---|---|
| [Serverless pricing](https://docs.runpod.io/serverless/pricing) | `workers_min = 0` 이 왜 중요한지 |
| [Pods pricing](https://docs.runpod.io/pods/pricing) | 실행 중 분 단위 과금, 중지해도 남는 스토리지 비용 |
| [Billing information](https://docs.runpod.io/references/billing-information) | 지출 한도. 무언가를 생성하는 첫 실습 전에 설정하세요 |

**레퍼런스**

| 문서 | 이유 |
|---|---|
| [GPU types](https://docs.runpod.io/references/gpu-types) | 무엇이 있고 대략 얼마인지 |
| [Instant Clusters](https://docs.runpod.io/instant-clusters) | Cluster 트랙이 작성되기 전에 관심이 생겼다면 |

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

## 本站撰写的笔记
{: #notes-zh }

仅靠一个链接说不清的概念——在这里写成文字，并把 Runpod 特有的部分与通用部分分开。

| 页面 | 内容 |
|---|---|
| [GPU 与 LLM 基础]({{ '/readings/gpu-llm-basics/' | relative_url }}) | 硬件与 roofline · 精度 · 四个规模估算公式及计算器 · 推理服务 · 成本——每一项都附上这些实验的实测结果 |
| [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) | NVLink 和 MIG 是什么 · 带宽与隔离 · Runpod 允许你控制其中哪些 |

## 背景——GPU、训练、推理、部署
{: #background-zh }

<div class="note" markdown="1">
以下链接全部由 Runpod 发布。已排除竞品对比和营销类文章。其余内容大多与云厂商无关——VRAM 计算、批处理、精度权衡。
</div>

### GPU 与显存

| 文章 | 主题 |
|---|---|
| [GPU cloud servers for AI workloads](https://www.runpod.io/articles/guides/gpu-cloud-servers-for-ai-workloads) | 最好的单一起点：对工作负载分类，用实际公式计算 VRAM，再据此匹配硬件 |
| [Choosing a GPU for training vs inference](https://www.runpod.io/articles/comparison/choosing-a-gpu-for-training-vs-inference) | 为什么合适的显卡取决于你做的是哪一种 |
| [GPU memory sizing for LLM inference](https://www.runpod.io/articles/guides/gpu-memory-sizing-guide-for-llm-inference) | 在租机器之前算清模型是否放得下 |
| [Avoiding OOM crashes for large models](https://www.runpod.io/articles/guides/avoid-oom-crashes-for-large-models) | 什么会耗尽，以及如何应对 |

### 训练

| 文章 | 主题 |
|---|---|
| [Inference vs training GPU guide](https://www.runpod.io/articles/guides/ai-inference-vs-training-gpu-guide) | 两种工作负载对硬件的需求不同 |
| [FP16, BF16, FP8 and mixed precision](https://www.runpod.io/articles/guides/fp16-bf16-fp8-mixed-precision-speed-up-my-model-training) | 数值格式，以及为速度付出的代价 |
| [Multi-GPU training](https://www.runpod.io/articles/guides/the-complete-guide-to-multi-gpu-training-scaling-ai-models-beyond-single-card-limitations) | 扩展到一张卡之外 |
| [Multi-node cluster architecture](https://www.runpod.io/articles/guides/gpu-clusters-for-ai-multi-node-architecture) | Cluster 路线的背景知识 |
| [InfiniBand for distributed training](https://www.runpod.io/articles/guides/infiniband-for-distributed-ai-training) | 为什么互连带宽决定多节点性能 |

### 推理

| 文章 | 主题 |
|---|---|
| [LLM inference from first principles](https://www.runpod.io/articles/guides/llm-inference-first-principles) | 每个 token 实际发生了什么，时间花在了哪里 |
| [PagedAttention and continuous batching](https://www.runpod.io/articles/guides/vllm-pagedattention-continuous-batching) | 让 vLLM 比朴素循环更快的两个思路 |
| [Inference optimisation playbook](https://www.runpod.io/articles/guides/llm-inference-optimization-playbook) | 针对延迟和吞吐量的手段，按顺序排列 |
| [Model quantization](https://www.runpod.io/articles/guides/ai-model-quantization-reducing-memory-usage-without-sacrificing-performance) | 用精度换显存，以及代价是什么 |
| [vLLM vs TensorRT-LLM](https://www.runpod.io/articles/comparison/vllm-vs-tensorrt-llm) | 选择推理服务引擎 |

### 部署与成本

| 文章 | 主题 |
|---|---|
| [Serverless vs Pods](https://www.runpod.io/articles/comparison/serverless-gpu-deployment-vs-pods) | 这些实验据以划分路线的那个决定 |
| [Scaling up vs scaling out](https://www.runpod.io/articles/comparison/scaling-up-vs-scaling-out) | 更大的 GPU，还是更多的 GPU |
| [Docker essentials for AI developers](https://www.runpod.io/articles/guides/docker-essentials-for-ai-developers) | 如果对 Serverless 路线的容器部分感到陌生，会有帮助 |
| [Cloud GPU pricing](https://www.runpod.io/articles/guides/cloud-gpu-pricing) | GPU 时间实际上如何计费 |
| [Cutting your GPU bill](https://www.runpod.io/articles/guides/how-to-cut-your-gpu-bill) | 实用的降本方法，大多在任何地方都适用 |

## Runpod 文档
{: #runpod-docs-zh }

**开始之前**

| 页面 | 原因 |
|---|---|
| [Welcome to Runpod](https://docs.runpod.io/overview) | 全局地图。十分钟，其余内容就更容易理解 |
| [Concepts](https://docs.runpod.io/get-started/concepts) | 术语——worker、endpoint、template、volume。到处使用却不加定义 |
| [Product overview](https://docs.runpod.io/get-started/products) | “探索 Runpod 的主要产品，为你的工作负载找到合适的方案”——不确定该用 Serverless 还是 Pod 时阅读 |

**Serverless**

| 页面 | 原因 |
|---|---|
| [Overview](https://docs.runpod.io/serverless/overview) | “面向 AI 模型和计算密集型工作负载的按需付费计算” |
| [Quickstart](https://docs.runpod.io/serverless/quickstart) | 实验 01 的官方版本 |
| [Handler functions](https://docs.runpod.io/serverless/workers/handler-functions) | 你的代码必须遵守的契约。与 [Worker SDK]({{ '/sdk/worker/' | relative_url }}) 一起阅读 |
| [Deploy from GitHub](https://docs.runpod.io/serverless/workers/github-integration) | 这些实验所用的部署路径——注意它没有提到 Build context 字段 |
| [Endpoint settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations) | 创建表单上每个设置的参考 |
| [Job states and metrics](https://docs.runpod.io/serverless/endpoints/job-states) | 在疑惑 `/runsync` 为什么返回 `IN_PROGRESS` 之前先读这个 |
| [Cached models](https://docs.runpod.io/serverless/endpoints/model-caching) | 为什么模型不该放进镜像。实验 02 的依据 |
| [Fitness checks](https://docs.runpod.io/serverless/development/fitness-checks) | 启动时校验。需要 `runpod>=1.9.0` |
| [Local testing](https://docs.runpod.io/serverless/development/local-testing) | 避免每次改动都要走一遍构建的循环 |
| [Concurrent handlers](https://docs.runpod.io/serverless/workers/concurrent-handler) | 一个 worker 处理多个请求——`concurrency_modifier` 发挥作用的地方 |
| [Optimize your endpoints](https://docs.runpod.io/serverless/development/optimization) | “降低延迟和成本的策略” |
| [Troubleshooting](https://docs.runpod.io/serverless/troubleshooting) | 值得浏览一遍，这样故障发生时你能认出来 |

**Pods**

| 页面 | 原因 |
|---|---|
| [Overview](https://docs.runpod.io/pods/overview) | 租用之后实际得到的是什么 |
| [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) | 按工作负载匹配 GPU，而不是靠猜 |
| [Storage options](https://docs.runpod.io/pods/storage/types) | 容器磁盘、volume 与 network volume。混淆它们就会丢失工作成果 |

**成本**

| 页面 | 原因 |
|---|---|
| [Serverless pricing](https://docs.runpod.io/serverless/pricing) | 为什么 `workers_min = 0` 很重要 |
| [Pods pricing](https://docs.runpod.io/pods/pricing) | 运行期间按分钟计费，外加已停止 Pod 的存储费用 |
| [Billing information](https://docs.runpod.io/references/billing-information) | 支出上限。在第一个会创建资源的实验之前设置好 |

**参考**

| 页面 | 原因 |
|---|---|
| [GPU types](https://docs.runpod.io/references/gpu-types) | 有哪些可用，以及大致价格 |
| [Instant Clusters](https://docs.runpod.io/instant-clusters) | 如果在 Cluster 路线写好之前就对它感兴趣 |

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

## ここで書いたノート
{: #notes-ja }

リンク 1 本では足りない概念を文章にまとめ、Runpod 固有の部分と一般的な部分を分けています。

| ページ | 扱う内容 |
|---|---|
| [GPU と LLM の基礎]({{ '/readings/gpu-llm-basics/' | relative_url }}) | ハードウェアとルーフライン · 精度 · 計算機付きの 4 つのサイジング式 · サービング · コスト — それぞれをこれらのラボの測定結果と並べて |
| [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) | NVLink と MIG とは何か · 帯域幅と分離 · そのうち Runpod で制御できるもの |

## 背景知識：GPU、学習、推論、デプロイ
{: #background-ja }

<div class="note" markdown="1">
リンク集で、すべて Runpod が公開したものです。競合比較やマーケティング色の強い記事は除いています。残りは大部分がプロバイダーに依存しない内容です。VRAM の計算、バッチ処理、精度のトレードオフなど。
</div>

### GPU とメモリ

| 記事 | トピック |
|---|---|
| [GPU cloud servers for AI workloads](https://www.runpod.io/articles/guides/gpu-cloud-servers-for-ai-workloads) | 出発点として最適の 1 本。ワークロードを分類し、実際の式で VRAM を計算し、それにハードウェアを合わせる |
| [Choosing a GPU for training vs inference](https://www.runpod.io/articles/comparison/choosing-a-gpu-for-training-vs-inference) | どちらを行うかで適したカードが変わる理由 |
| [GPU memory sizing for LLM inference](https://www.runpod.io/articles/guides/gpu-memory-sizing-guide-for-llm-inference) | マシンを借りる前にモデルが載るかを見積もる |
| [Avoiding OOM crashes for large models](https://www.runpod.io/articles/guides/avoid-oom-crashes-for-large-models) | 何が足りなくなり、どう対処するか |

### 学習

| 記事 | トピック |
|---|---|
| [Inference vs training GPU guide](https://www.runpod.io/articles/guides/ai-inference-vs-training-gpu-guide) | 2 つのワークロードはハードウェアに求めるものが違う |
| [FP16, BF16, FP8 and mixed precision](https://www.runpod.io/articles/guides/fp16-bf16-fp8-mixed-precision-speed-up-my-model-training) | 数値形式と、速度と引き換えに手放すもの |
| [Multi-GPU training](https://www.runpod.io/articles/guides/the-complete-guide-to-multi-gpu-training-scaling-ai-models-beyond-single-card-limitations) | 1 枚のカードを超えてスケールする |
| [Multi-node cluster architecture](https://www.runpod.io/articles/guides/gpu-clusters-for-ai-multi-node-architecture) | Cluster トラックの背景知識 |
| [InfiniBand for distributed training](https://www.runpod.io/articles/guides/infiniband-for-distributed-ai-training) | インターコネクトの帯域幅がマルチノード性能を決める理由 |

### 推論

| 記事 | トピック |
|---|---|
| [LLM inference from first principles](https://www.runpod.io/articles/guides/llm-inference-first-principles) | トークンごとに実際に何が起き、時間がどこに使われるか |
| [PagedAttention and continuous batching](https://www.runpod.io/articles/guides/vllm-pagedattention-continuous-batching) | vLLM を素朴なループより速くしている 2 つのアイデア |
| [Inference optimisation playbook](https://www.runpod.io/articles/guides/llm-inference-optimization-playbook) | レイテンシとスループットのための手段を順番に |
| [Model quantization](https://www.runpod.io/articles/guides/ai-model-quantization-reducing-memory-usage-without-sacrificing-performance) | 精度をメモリと引き換えにすることと、その代償 |
| [vLLM vs TensorRT-LLM](https://www.runpod.io/articles/comparison/vllm-vs-tensorrt-llm) | サービングエンジンの選び方 |

### デプロイとコスト

| 記事 | トピック |
|---|---|
| [Serverless vs Pods](https://www.runpod.io/articles/comparison/serverless-gpu-deployment-vs-pods) | これらのラボがトラックを分ける基準にした判断そのもの |
| [Scaling up vs scaling out](https://www.runpod.io/articles/comparison/scaling-up-vs-scaling-out) | より大きな GPU か、より多くの GPU か |
| [Docker essentials for AI developers](https://www.runpod.io/articles/guides/docker-essentials-for-ai-developers) | Serverless トラックのコンテナ周りに馴染みがなければ役立ちます |
| [Cloud GPU pricing](https://www.runpod.io/articles/guides/cloud-gpu-pricing) | GPU 時間が実際にどう課金されるか |
| [Cutting your GPU bill](https://www.runpod.io/articles/guides/how-to-cut-your-gpu-bill) | 実践的な削減策。ほとんどはどこでも通用します |

## Runpod ドキュメント
{: #runpod-docs-ja }

**始める前に**

| ページ | 理由 |
|---|---|
| [Welcome to Runpod](https://docs.runpod.io/overview) | 全体の地図。10 分で、残りがずっと理解しやすくなります |
| [Concepts](https://docs.runpod.io/get-started/concepts) | 用語集。worker、endpoint、template、volume など、定義なしにあちこちで使われます |
| [Product overview](https://docs.runpod.io/get-started/products) | 「Runpod の主要な製品を見て、ワークロードに合ったソリューションを見つける」。Serverless と Pod のどちらが必要か迷ったら読んでください |

**Serverless**

| ページ | 理由 |
|---|---|
| [Overview](https://docs.runpod.io/serverless/overview) | 「AI モデルと計算負荷の高いワークロードのための従量課金コンピュート」 |
| [Quickstart](https://docs.runpod.io/serverless/quickstart) | Lab 01 の公式版 |
| [Handler functions](https://docs.runpod.io/serverless/workers/handler-functions) | コードが満たすべき契約。[Worker SDK]({{ '/sdk/worker/' | relative_url }}) と合わせて読んでください |
| [Deploy from GitHub](https://docs.runpod.io/serverless/workers/github-integration) | これらのラボが使うデプロイ経路。Build context フィールドが書かれていない点に注意 |
| [Endpoint settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations) | 作成フォームの全設定のリファレンス |
| [Job states and metrics](https://docs.runpod.io/serverless/endpoints/job-states) | `/runsync` がなぜ `IN_PROGRESS` を返したのか悩む前に読んでください |
| [Cached models](https://docs.runpod.io/serverless/endpoints/model-caching) | モデルをイメージに入れるべきでない理由。Lab 02 の土台 |
| [Fitness checks](https://docs.runpod.io/serverless/development/fitness-checks) | 起動時の検証。`runpod>=1.9.0` が必要 |
| [Local testing](https://docs.runpod.io/serverless/development/local-testing) | 変更のたびにビルドしなくて済むループ |
| [Concurrent handlers](https://docs.runpod.io/serverless/workers/concurrent-handler) | 1 つの worker で複数のリクエスト。`concurrency_modifier` が真価を発揮するところ |
| [Optimize your endpoints](https://docs.runpod.io/serverless/development/optimization) | 「レイテンシとコストを下げるための戦略」 |
| [Troubleshooting](https://docs.runpod.io/serverless/troubleshooting) | 一度ざっと目を通しておけば、障害が起きたときに見分けられます |

**Pods**

| ページ | 理由 |
|---|---|
| [Overview](https://docs.runpod.io/pods/overview) | 借りたときに実際に何が手に入るか |
| [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) | 当て推量ではなくワークロードに GPU を合わせる |
| [Storage options](https://docs.runpod.io/pods/storage/types) | コンテナディスク、volume、network volume の違い。これを混同すると作業が失われます |

**コスト**

| ページ | 理由 |
|---|---|
| [Serverless pricing](https://docs.runpod.io/serverless/pricing) | `workers_min = 0` が重要な理由 |
| [Pods pricing](https://docs.runpod.io/pods/pricing) | 稼働中は分単位、加えて停止中の Pod のストレージ |
| [Billing information](https://docs.runpod.io/references/billing-information) | 支出上限。何かを作成する最初のラボの前に設定してください |

**リファレンス**

| ページ | 理由 |
|---|---|
| [GPU types](https://docs.runpod.io/references/gpu-types) | 何が利用でき、おおよそいくらか |
| [Instant Clusters](https://docs.runpod.io/instant-clusters) | Cluster トラックが書かれる前に興味が湧いたら |

</div>
