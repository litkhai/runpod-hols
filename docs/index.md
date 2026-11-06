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

Start with [Welcome to Runpod](https://docs.runpod.io/overview) and [Concepts](https://docs.runpod.io/get-started/concepts); [Product overview](https://docs.runpod.io/get-started/products) covers the choice between the three. GPU, training, inference and deployment background is under [Readings]({{ '/readings/' | relative_url }}).

<div class="cards" markdown="0">
  <div class="card">
    <h3><a href="{{ '/setup/' | relative_url }}">Setup</a></h3>
    <p>API keys, tool checks, auth verification, MCP.</p>
    <span class="badge ready">Start here</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/serverless/' | relative_url }}">Serverless</a></h3>
    <p>Autoscaling inference endpoints. Billed per execution.</p>
    <span class="badge ready">Labs 01–03 run</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/pod/' | relative_url }}">Pod</a></h3>
    <p>GPU containers with SSH and Jupyter. Billed per minute.</p>
    <span class="badge ready">Labs 01–04 run</span>
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

[Welcome to Runpod](https://docs.runpod.io/overview) 과 [Concepts](https://docs.runpod.io/get-started/concepts) 부터 보세요. 셋 중 무엇을 쓸지는 [Product overview](https://docs.runpod.io/get-started/products) 가 다룹니다. GPU·학습·추론·배포 배경은 [Readings]({{ '/readings/' | relative_url }}) 에 있습니다.

<div class="cards" markdown="0">
  <div class="card">
    <h3><a href="{{ '/setup/' | relative_url }}">사전 구성</a></h3>
    <p>API 키, 도구 검사, 인증 확인, MCP.</p>
    <span class="badge ready">여기서 시작</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/serverless/' | relative_url }}">Serverless</a></h3>
    <p>오토스케일 추론 엔드포인트. 실행 시간만큼 과금.</p>
    <span class="badge ready">Lab 01–03 실행</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/pod/' | relative_url }}">Pod</a></h3>
    <p>SSH·Jupyter 로 쓰는 GPU 컨테이너. 분 단위 과금.</p>
    <span class="badge ready">Lab 01–04 실행</span>
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

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

面向 [Runpod](https://runpod.io) 的实践实验。Runpod 是用于 AI/ML 工作负载的 GPU 云。Runpod 的每一种计算产品各有一条实验路线，另有一条 Terraform 路线，用代码完成同样的事情。

这里的所有内容都经过实际运行验证——文档中的输出、镜像大小和错误信息都是真实的，而不是从厂商文档中照抄的。

### Runpod 是什么

一个按秒或按分钟出租加速器的 GPU 云，无需预约，也无需申请配额。有三种使用方式，选对其中一种就是大部分的决定：

- **Serverless**——你提供一个带 `handler` 函数的容器；Runpod 将其作为 HTTP 端点运行，按需启动 worker，只在执行期间计费。用于推理。
- **Pods**——你租用一个 GPU 容器并一直保留，可通过 SSH、JupyterLab 访问，并有持久化的 `/workspace`。运行期间全程计费。用于开发和微调。
- **Instant Clusters**——2–8 个多 GPU 节点互连，用于分布式训练。

围绕这三者，还有预构建 worker 的 Hub、用于共享存储的 Network Volume，以及一个既在 worker 内部运行、又能从外部操控平台的 Python SDK。

建议先读 [Welcome to Runpod](https://docs.runpod.io/overview) 和 [Concepts](https://docs.runpod.io/get-started/concepts)；三者之间如何选择见 [Product overview](https://docs.runpod.io/get-started/products)。GPU、训练、推理和部署的背景知识见 [Readings]({{ '/readings/' | relative_url }})。

<div class="cards" markdown="0">
  <div class="card">
    <h3><a href="{{ '/setup/' | relative_url }}">Setup</a></h3>
    <p>API 密钥、工具检查、认证验证、MCP。</p>
    <span class="badge ready">从这里开始</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/serverless/' | relative_url }}">Serverless</a></h3>
    <p>自动扩缩的推理端点。按执行计费。</p>
    <span class="badge ready">实验 01–03 已运行</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/pod/' | relative_url }}">Pod</a></h3>
    <p>带 SSH 和 Jupyter 的 GPU 容器。按分钟计费。</p>
    <span class="badge ready">实验 01–04 已运行</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/cluster/' | relative_url }}">Cluster</a></h3>
    <p>多节点分布式训练。</p>
    <span class="badge tbd">待定</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/terraform/' | relative_url }}">Terraform</a></h3>
    <p>以基础设施即代码方式管理同样的资源。</p>
    <span class="badge ready">2 个实验就绪</span>
  </div>
</div>

### 产品对比

| | Serverless | Pod | Instant Cluster |
|---|---|---|---|
| 形态 | 自动扩缩的 worker 端点 | 单个 GPU 容器 | 2–8 个节点（16–64 块 GPU） |
| 需要 | `handler.py` + 镜像 | 无——从控制台启动 | 分布式训练脚本 |
| 访问 | HTTP API | SSH / Jupyter / VS Code | 每个节点 SSH |
| 计费 | 仅在执行期间 | 运行期间持续计费 | 集群租用时间 |
| 状态 | 无——每个请求重置 | 持久化（`/workspace`） | 持久化 |

关键区别在于**状态是否持久**。Pod 在停止和启动之间保留 `/workspace`，模型和数据集可以重复使用。Serverless 每个请求都是一个新容器，所以较重的内容必须打包进镜像，或通过 Network Volume 挂载。

### 前提条件

| 项目 | 要求 |
|---|---|
| Python | 3.10+——macOS 自带的 Python 是 3.9，无法使用 |
| Docker | Serverless 路线需要 |
| Terraform | Terraform 路线需要 1.6+——见该页面的注意事项 |
| Runpod 账号 | [console.runpod.io](https://console.runpod.io) |

<div class="warn" markdown="1">
**费用警告。** Pod 在运行期间全程计费，即使空闲也一样——用完务必 Stop 或 Terminate。只要 Active Workers 保持为 0，没有请求时 Serverless 不产生费用。在第一个会创建资源的实验之前，先在控制台设置支出上限。
</div>

### 开始

```bash
git clone https://github.com/litkhai/runpod-hols
cd runpod-hols
./setup/check-setup.sh
```

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

AI/ML ワークロード向けの GPU クラウド [Runpod](https://runpod.io) のハンズオンラボです。Runpod のコンピュート製品ごとにトラックがあり、同じことをコードで行う Terraform トラックもあります。

ここにあるものはすべて実際に動かして確認しています。ドキュメント中の出力、イメージサイズ、エラーメッセージは本物で、ベンダーのドキュメントから書き写したものではありません。

### Runpod とは

予約もクォータ申請もなしに、アクセラレータを秒単位・分単位で借りられる GPU クラウドです。使い方は 3 通りあり、どれを選ぶかが判断の大部分を占めます。

- **Serverless**：`handler` 関数を持つコンテナを用意すると、Runpod がそれを HTTP エンドポイントとして動かし、必要に応じて worker を起動し、実行中だけ課金します。推論向け。
- **Pods**：GPU コンテナを借りてそのまま保持します。SSH、JupyterLab、永続的な `/workspace` が使えます。稼働中はずっと課金されます。開発とファインチューニング向け。
- **Instant Clusters**：2–8 台のマルチ GPU ノードを相互接続したもの。分散学習向け。

その周りに、ビルド済み worker の Hub、共有ストレージ用の Network Volume、そして worker の中で動きつつ外からプラットフォームを操作もできる Python SDK があります。

まず [Welcome to Runpod](https://docs.runpod.io/overview) と [Concepts](https://docs.runpod.io/get-started/concepts) を読んでください。3 つの選び方は [Product overview](https://docs.runpod.io/get-started/products) にあります。GPU、学習、推論、デプロイの背景知識は [Readings]({{ '/readings/' | relative_url }}) にまとめています。

<div class="cards" markdown="0">
  <div class="card">
    <h3><a href="{{ '/setup/' | relative_url }}">Setup</a></h3>
    <p>API キー、ツールの確認、認証の検証、MCP。</p>
    <span class="badge ready">ここから開始</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/serverless/' | relative_url }}">Serverless</a></h3>
    <p>オートスケールする推論エンドポイント。実行単位で課金。</p>
    <span class="badge ready">ラボ 01–03 実行済み</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/pod/' | relative_url }}">Pod</a></h3>
    <p>SSH と Jupyter 付きの GPU コンテナ。分単位で課金。</p>
    <span class="badge ready">ラボ 01–04 実行済み</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/cluster/' | relative_url }}">Cluster</a></h3>
    <p>マルチノードの分散学習。</p>
    <span class="badge tbd">未定</span>
  </div>
  <div class="card">
    <h3><a href="{{ '/terraform/' | relative_url }}">Terraform</a></h3>
    <p>同じリソースを Infrastructure as Code で。</p>
    <span class="badge ready">ラボ 2 本準備済み</span>
  </div>
</div>

### 製品の比較

| | Serverless | Pod | Instant Cluster |
|---|---|---|---|
| 形態 | オートスケールする worker エンドポイント | 単一の GPU コンテナ | 2–8 ノード（GPU 16–64 基） |
| 必要なもの | `handler.py` + イメージ | なし（コンソールから起動） | 分散学習スクリプト |
| アクセス | HTTP API | SSH / Jupyter / VS Code | ノードごとに SSH |
| 課金 | 実行中のみ | 稼働中は継続して課金 | クラスタのリース時間 |
| 状態 | なし（リクエストごとにリセット） | 永続（`/workspace`） | 永続 |

最大の違いは**状態が残るかどうか**です。Pod は停止と起動をまたいで `/workspace` を保持するので、モデルやデータセットを使い回せます。Serverless はリクエストごとに新しいコンテナなので、重いものはイメージに焼き込むか、Network Volume でアタッチする必要があります。

### 前提条件

| 項目 | 要件 |
|---|---|
| Python | 3.10 以上。macOS 標準の Python は 3.9 なので動きません |
| Docker | Serverless トラックで必要 |
| Terraform | Terraform トラックでは 1.6 以上。そのページの注意事項を参照 |
| Runpod アカウント | [console.runpod.io](https://console.runpod.io) |

<div class="warn" markdown="1">
**コストに関する警告。** Pod は稼働中ずっと課金されます。アイドル状態でも同じです。終わったら必ず Stop か Terminate してください。Serverless は Active Workers を 0 にしておけば、リクエストがないときは費用がかかりません。何かを作成する最初のラボの前に、コンソールで支出上限を設定してください。
</div>

### はじめに

```bash
git clone https://github.com/litkhai/runpod-hols
cd runpod-hols
./setup/check-setup.sh
```

</div>
