---
layout: default
title: Overview
permalink: /
---

# Runpod Hands-On Labs

<div class="lang" data-lang="en" markdown="1">

## English

Practical labs for [Runpod](https://runpod.io), the GPU cloud for AI/ML workloads. Each of Runpod's compute products gets its own track, plus a Terraform track for doing the same thing as code.

Everything here was verified by actually running it — the outputs, image sizes and error messages in these docs are real, not transcribed from vendor documentation.

### What Runpod is

A GPU cloud that rents you accelerators by the second or the minute, without a reservation or a quota request. You reach it three ways, and picking the right one is most of the decision:

- **Serverless** — you supply a container with a `handler` function; Runpod runs it as an HTTP endpoint, starting workers on demand and billing only while they execute. For inference.
- **Pods** — you rent a GPU container and keep it, with SSH, JupyterLab and a persistent `/workspace`. Billed the whole time it runs. For development and fine-tuning.
- **Instant Clusters** — 2–8 multi-GPU nodes wired together for distributed training.

Around those sit a Hub of prebuilt workers, Network Volumes for shared storage, and a Python SDK that both runs inside your worker and drives the platform from outside.

New to the platform? [Welcome to Runpod](https://docs.runpod.io/overview) and [Concepts](https://docs.runpod.io/get-started/concepts) are the two pages worth reading before starting, and [Product overview](https://docs.runpod.io/get-started/products) helps if you are unsure which of the three you want. A wider list — GPU, training, inference and deployment background — is under [Readings]({{ '/readings/' | relative_url }}).

<div class="cards" markdown="0">
  <div class="card">
    <h3><a href="{{ '/setup/' | relative_url }}">Setup</a></h3>
    <p>API keys, tool checks, auth verification, MCP.</p>
    <span class="badge ready">Start here</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/serverless/' | relative_url }}">Serverless</a></h3>
    <p>Autoscaling inference endpoints. Billed per execution.</p>
    <span class="badge ready">Lab 01 ready</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/pod/' | relative_url }}">Pod</a></h3>
    <p>GPU containers with SSH and Jupyter. Billed per minute.</p>
    <span class="badge planned">Planned</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/cluster/' | relative_url }}">Cluster</a></h3>
    <p>Multi-node distributed training.</p>
    <span class="badge tbd">TBD</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/terraform/' | relative_url }}">Terraform</a></h3>
    <p>The same resources as infrastructure as code.</p>
    <span class="badge ready">2 labs ready</span>
  </div>
</div>

### Comparing the products

| | Serverless | Pod | Instant Cluster |
|---|---|---|---|
| Form | Autoscaling worker endpoint | A single GPU container | 2–8 nodes (16–64 GPUs) |
| Requires | `handler.py` + image | Nothing — launch from console | Distributed training script |
| Access | HTTP API | SSH / Jupyter / VS Code | SSH per node |
| Billing | Only while executing | Continuously while running | Cluster lease time |
| State | None — reset per request | Persistent (`/workspace`) | Persistent |

The key difference is **state persistence**. A Pod keeps `/workspace` across stop and start, so models and datasets can be reused. Serverless gives you a fresh container per request, so anything heavy must be baked into the image or attached via a Network Volume.

### Prerequisites

| Item | Required |
|---|---|
| Python | 3.10+ — the macOS system Python is 3.9 and will not work |
| Docker | For the Serverless track |
| Terraform | 1.6+ for the Terraform track — see the caveat on that page |
| Runpod account | [console.runpod.io](https://console.runpod.io) |

<div class="warn" markdown="1">
**Cost warning.** A Pod bills the entire time it is running, even when idle — always Stop or Terminate when you finish. Serverless costs nothing when there are no requests, provided Active Workers stays at 0. Set a spending limit in the console before your first lab that creates anything.
</div>

### Getting started

```bash
git clone https://github.com/litkhai/runpod-hols
cd runpod-hols
./setup/check-setup.sh
```

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

AI/ML 워크로드를 위한 GPU 클라우드 [Runpod](https://runpod.io) 의 실습 자료입니다. Runpod 의 컴퓨트 제품별로 트랙을 나누고, 같은 작업을 코드로 하는 Terraform 트랙을 더했습니다.

여기 있는 내용은 전부 실제로 실행해서 확인한 것입니다. 문서에 나오는 출력, 이미지 크기, 오류 메시지는 벤더 문서를 옮긴 것이 아니라 직접 얻은 결과입니다.

### Runpod 이란

예약이나 쿼터 신청 없이 초 단위·분 단위로 GPU 를 빌려 쓰는 클라우드입니다. 접근 방식이 세 가지이고, 어느 것을 고르느냐가 사실상 결정의 대부분입니다.

- **Serverless** — `handler` 함수를 담은 컨테이너를 올리면 Runpod 이 HTTP 엔드포인트로 실행합니다. 요청이 오면 워커를 띄우고, 실행되는 동안만 과금합니다. 추론용.
- **Pods** — GPU 컨테이너를 빌려 계속 점유합니다. SSH, JupyterLab, 유지되는 `/workspace` 를 쓸 수 있고, 켜져 있는 내내 과금됩니다. 개발과 파인튜닝용.
- **Instant Clusters** — 분산 학습을 위해 2~8개의 멀티 GPU 노드를 묶은 구성.

그 주변에 미리 만들어진 워커를 모아둔 Hub, 공유 스토리지인 Network Volume, 그리고 워커 안에서도 돌고 밖에서 플랫폼을 조종하기도 하는 Python SDK 가 있습니다.

플랫폼이 처음이라면 [Welcome to Runpod](https://docs.runpod.io/overview) 과 [Concepts](https://docs.runpod.io/get-started/concepts) 두 페이지를 먼저 읽을 만하고, 셋 중 무엇을 쓸지 모르겠다면 [Product overview](https://docs.runpod.io/get-started/products) 가 도움이 됩니다. GPU·학습·추론·배포 배경까지 포함한 더 넓은 목록은 [Readings]({{ '/readings/' | relative_url }}) 에 있습니다.

<div class="cards" markdown="0">
  <div class="card">
    <h3><a href="{{ '/setup/' | relative_url }}">사전 구성</a></h3>
    <p>API 키, 도구 검사, 인증 확인, MCP.</p>
    <span class="badge ready">여기서 시작</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/serverless/' | relative_url }}">Serverless</a></h3>
    <p>오토스케일 추론 엔드포인트. 실행 시간만큼 과금.</p>
    <span class="badge ready">Lab 01 준비됨</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/pod/' | relative_url }}">Pod</a></h3>
    <p>SSH·Jupyter 로 쓰는 GPU 컨테이너. 분 단위 과금.</p>
    <span class="badge planned">계획됨</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/cluster/' | relative_url }}">Cluster</a></h3>
    <p>다중 노드 분산 학습.</p>
    <span class="badge tbd">TBD</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/terraform/' | relative_url }}">Terraform</a></h3>
    <p>같은 리소스를 코드형 인프라로.</p>
    <span class="badge ready">2개 준비됨</span>
  </div>
</div>

### 제품 비교

| | Serverless | Pod | Instant Cluster |
|---|---|---|---|
| 형태 | 오토스케일 워커 엔드포인트 | GPU 컨테이너 1대 | 2~8 노드 (16~64 GPU) |
| 필요한 것 | `handler.py` + 이미지 | 없음 — 콘솔에서 기동 | 분산 학습 스크립트 |
| 접속 | HTTP API | SSH / Jupyter / VS Code | 노드별 SSH |
| 과금 | 실행된 시간만 | 켜져 있는 동안 계속 | 클러스터 임대 시간 |
| 상태 유지 | 없음 — 요청마다 초기화 | 있음 (`/workspace`) | 있음 |

가장 중요한 차이는 **상태 유지**입니다. Pod 는 껐다 켜도 `/workspace` 가 남아 모델과 데이터셋을 재사용할 수 있지만, Serverless 는 요청마다 새 컨테이너이므로 무거운 것은 이미지에 미리 굽거나 Network Volume 에 붙여야 합니다.

### 사전 준비

| 항목 | 필요 조건 |
|---|---|
| Python | 3.10 이상 — macOS 기본 Python 은 3.9 이라 동작하지 않음 |
| Docker | Serverless 트랙에 필요 |
| Terraform | Terraform 트랙은 1.6 이상 — 해당 페이지의 주의사항 참조 |
| Runpod 계정 | [console.runpod.io](https://console.runpod.io) |

<div class="warn" markdown="1">
**비용 주의.** Pod 는 유휴 상태여도 켜져 있는 내내 과금되므로 실습이 끝나면 반드시 Stop 또는 Terminate 하세요. Serverless 는 Active Worker 가 0 이면 요청이 없을 때 비용이 발생하지 않습니다. 리소스를 생성하는 첫 실습 전에 콘솔에서 지출 한도를 설정해 두세요.
</div>

### 시작하기

```bash
git clone https://github.com/litkhai/runpod-hols
cd runpod-hols
./setup/check-setup.sh
```

</div>
