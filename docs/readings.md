---
layout: default
title: Readings
permalink: /readings/
---

# Readings

<div class="lang" data-lang="en" markdown="1">

## English

Two different kinds of material, kept apart because you read them differently.

**Runpod docs** you consult while doing something. **Background** you read before or between labs, to build the mental model the labs assume.

<div class="note" markdown="1">
Everything below is published by Runpod. The background articles are genuinely instructional — VRAM arithmetic, batching strategy, precision trade-offs — and mostly apply to any GPU provider. Competitor comparisons and "why teams choose us" pieces are excluded; they exist, and they are not on this list.
</div>

## Background — GPU, training, inference, deployment
{: #background }

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

Pages from Runpod's own documentation worth the time, in roughly the order these labs touch them. Descriptions are Runpod's, trimmed.

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

성격이 다른 두 종류를 분리해 두었습니다. 읽는 방식이 다르기 때문입니다.

**Runpod 문서**는 작업하면서 찾아보는 것이고, **배경 자료**는 실습 전후로 읽어 실습이 전제하는 사고 틀을 만드는 것입니다.

<div class="note" markdown="1">
아래는 모두 Runpod 이 발행한 자료입니다. 배경 자료들은 실제로 교육적인 내용입니다 — VRAM 계산, 배칭 전략, 정밀도 트레이드오프 — 그리고 대부분 다른 GPU 제공사에도 적용됩니다. 경쟁사 비교나 "왜 우리를 선택하는가" 류의 글은 제외했습니다. 존재하지만 이 목록에는 없습니다.
</div>

## 배경 — GPU, 학습, 추론, 배포
{: #background-ko }

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

Runpod 공식 문서 중 시간을 들일 만한 페이지들을, 이 실습들이 다루는 순서에 가깝게 정리했습니다. 설명은 Runpod 의 것을 다듬었습니다.

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
