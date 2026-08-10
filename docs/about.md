---
layout: default
title: About
permalink: /about/
---

# About This Repository

<div class="lang" data-lang="en" markdown="1">

## English

An unofficial set of hands-on labs for [Runpod](https://runpod.io), written while learning the platform. Source at [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols).

The aim is to understand the Runpod SDK and the AI infrastructure around it by running things, not by reading about them.

### Everything here was run

Command output, image sizes, latency figures and error messages are from a real account. Where something has **not** been run — `terraform apply`, the Pod track — the page says so.

That matters because it is what makes the disagreements trustworthy:

| Finding | Where it is documented |
|---|---|
| The console's **Build context** field is undocumented, and required for a nested Dockerfile | [Serverless]({{ '/serverless/' | relative_url }}) |
| `{"input": {}}` never returns — 90 s, zero bytes, `retries: 1` | [Serverless]({{ '/serverless/' | relative_url }}) |
| `/runsync` can return `IN_PROGRESS`, not just `COMPLETED` | [Client SDK]({{ '/sdk/client/' | relative_url }}) |
| Returning `{"error": ...}` fails the job — it is a control key, not data | [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| Terraform provider v1.0.9 is published but its schema will not load | [Terraform]({{ '/terraform/' | relative_url }}) |
| Homebrew's `terraform` is frozen at 1.5.7 and cannot install the provider | [Terraform]({{ '/terraform/' | relative_url }}) |

### Recommended reading
{: #recommended-reading }

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

### License

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE). Take anything here and use it.

`serverless/01-hello-worker` derives from `runpod-workers/worker-template`, which is MIT licensed; its copyright notice travels with the repo in [NOTICE](https://github.com/litkhai/runpod-hols/blob/main/NOTICE).

### Not affiliated with Runpod

An independent learning exercise. Nothing here is reviewed or endorsed by Runpod. Where it disagrees with the official documentation, the disagreement is recorded with evidence — but the official docs remain the authority.

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

[Runpod](https://runpod.io) 을 배우면서 작성한 비공식 실습 자료입니다. 소스는 [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols) 에 있습니다.

목표는 Runpod SDK 와 그 주변 AI 인프라를, 읽어서가 아니라 직접 돌려보면서 이해하는 것입니다.

### 여기 있는 것은 전부 실행해본 것입니다

명령 출력, 이미지 크기, 지연시간 수치, 오류 메시지는 실제 계정에서 얻었습니다. 아직 실행하지 **않은** 것 — `terraform apply`, Pod 트랙 — 은 그렇다고 명시합니다.

공식 문서와 어긋나는 지점을 신뢰할 수 있게 만드는 것이 이 원칙입니다.

| 발견 | 문서 위치 |
|---|---|
| 콘솔의 **Build context** 필드가 미문서화, 하위 디렉토리 Dockerfile 에는 필수 | [Serverless]({{ '/serverless/' | relative_url }}) |
| `{"input": {}}` 은 응답이 오지 않음 — 90초, 0바이트, `retries: 1` | [Serverless]({{ '/serverless/' | relative_url }}) |
| `/runsync` 가 `COMPLETED` 뿐 아니라 `IN_PROGRESS` 도 반환 | [Client SDK]({{ '/sdk/client/' | relative_url }}) |
| `{"error": ...}` 반환은 작업을 실패시킴 — 데이터가 아니라 제어 키 | [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| Terraform 프로바이더 v1.0.9 는 배포됐지만 스키마가 로드되지 않음 | [Terraform]({{ '/terraform/' | relative_url }}) |
| Homebrew 의 `terraform` 은 1.5.7 에 멈춰 있어 프로바이더 설치 불가 | [Terraform]({{ '/terraform/' | relative_url }}) |

### 추천 읽을거리
{: #recommended-reading-ko }

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

### 라이선스

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE). 여기 있는 것은 무엇이든 가져다 쓰셔도 됩니다.

`serverless/01-hello-worker` 는 MIT 라이선스인 `runpod-workers/worker-template` 에서 파생됐으며, 원본 저작권 표시는 [NOTICE](https://github.com/litkhai/runpod-hols/blob/main/NOTICE) 에 함께 담았습니다.

### Runpod 과 무관합니다

독립적인 학습 자료입니다. 여기 있는 어떤 내용도 Runpod 의 검토나 승인을 거치지 않았습니다. 공식 문서와 어긋나는 부분은 근거와 함께 기록했지만, 공식 문서가 여전히 권위 있는 출처입니다.

</div>
