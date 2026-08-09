# Pod Track

[English](#english) | [한국어](#한국어)

> **Status: 📋 Planned.** The structure and references below are settled; the lab files are not written yet.
> **상태: 📋 계획됨.** 아래 구조와 참조 자료는 확정했고, 실습 파일은 아직 작성 전입니다.

---

## English

A Pod is a **GPU or CPU container you rent and control**. Unlike Serverless, it stays up until you stop it, keeps its filesystem, and you get shell access. This is where development, experimentation, and fine-tuning happen.

### 📚 Planned Labs

| Lab | Contents |
|---|---|
| 01-launch-and-connect | Pick a GPU, launch from a template, connect via SSH / JupyterLab / VS Code, verify with `nvidia-smi` |
| 02-storage | Container Disk vs Volume vs Network Volume — what survives a stop, what does not |
| 03-custom-template | Build a custom Pod template, environment variables, secrets |
| 04-pod-to-serverless | Develop on a Pod, then package the result as a Serverless worker |

### Core Concepts

**Storage — the concept that matters most.** Three tiers, and confusing them is how people lose work:

| Type | Lifetime | Mount | Use for |
|---|---|---|---|
| Container Disk | Destroyed on stop/terminate | `/` | OS, temp files |
| Volume Disk | Survives stop, dies on terminate | `/workspace` | Working code, datasets |
| Network Volume | Independent of any Pod, shareable | configurable | Model weights reused across Pods |

Anything you want to keep goes in `/workspace` or a Network Volume. Never leave work on the container disk.

**Choosing a data center for a Network Volume matters more than it looks.** The docs put it plainly: location "does not affect pricing, but the datacenter location will determine which GPU types your network volume can be used with." Pick a thinly-provisioned one and you quietly narrow your GPU options later.

Queried from the live API (`runpod_data_centers`, read-only, costs nothing):

| | Count |
|---|---|
| Data centers total | 49 |
| Reporting `global_network = true` | 20 |
| Supporting the S3-compatible API | 5 — `EUR-IS-1`, `EU-RO-1`, `EU-CZ-1`, `US-KS-2`, `US-CA-2` |

`US-KS-2` is the default in [`terraform/02-pod`](../terraform/02-pod) because it is in both sets.

**Access** — SSH, JupyterLab, VS Code / Cursor via Remote-SSH, or a web proxy for services you expose.

**Billing** — per minute, for as long as the Pod is running, idle or not. Stopping releases the GPU but still bills volume storage. Terminating removes everything. This is the single biggest difference from Serverless and the easiest way to run up a bill by accident.

### 🔍 Reference Review

Pods need no code repository — you launch them from the console, CLI, or SDK — so unlike the Serverless track there is no template repo to fork. The references are documentation and images.

| Resource | Notes |
|---|---|
| [Pods overview](https://docs.runpod.io/pods/overview) | Product concepts |
| [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) | GPU selection guidance |
| [Connect to a Pod](https://docs.runpod.io/pods/connect-to-a-pod) | SSH / Jupyter / VS Code |
| [Storage types](https://docs.runpod.io/pods/storage/types) | The three-tier model above |
| [Network volumes](https://docs.runpod.io/pods/storage/create-network-volumes) | Shared persistent storage |
| [Templates](https://docs.runpod.io/pods/templates/overview) | Official and custom templates |
| [Pricing](https://docs.runpod.io/pods/pricing) | Per-minute rates, savings plans |
| [runpod/containers](https://github.com/runpod/containers/tree/main/official-templates) | Dockerfiles behind official templates: `base`, `pytorch`, `nvidia-pytorch`, `rocm`, `pytorch-cluster` |
| [runpod/runpodctl](https://github.com/runpod/runpodctl) | CLI for launching and managing Pods |

Note that `runpod/containers` is shared ground with the Serverless track — `runpod/base` is both the Pod template base and the image the Serverless `worker-template` builds on.

### ⚠️ Before You Start

Set a spending limit in the console, and get into the habit of terminating Pods the moment a lab ends. A forgotten Pod is the most common surprise on a Runpod bill.

---

## 한국어

Pod 는 **직접 빌려서 제어하는 GPU 또는 CPU 컨테이너**입니다. Serverless 와 달리 중지할 때까지 계속 떠 있고, 파일시스템이 유지되며, 셸 접속이 가능합니다. 개발, 실험, 파인튜닝이 이루어지는 곳입니다.

### 📚 계획된 실습

| 실습 | 내용 |
|---|---|
| 01-launch-and-connect | GPU 선택, 템플릿으로 Pod 기동, SSH / JupyterLab / VS Code 접속, `nvidia-smi` 확인 |
| 02-storage | Container Disk vs Volume vs Network Volume — 중지 시 무엇이 남고 무엇이 사라지는가 |
| 03-custom-template | 커스텀 Pod 템플릿 제작, 환경변수, 시크릿 |
| 04-pod-to-serverless | Pod 에서 개발한 결과물을 Serverless 워커로 패키징 |

### 핵심 개념

**스토리지 — 가장 중요한 개념입니다.** 세 계층이 있고, 이걸 혼동하면 작업물을 잃습니다.

| 종류 | 수명 | 마운트 위치 | 용도 |
|---|---|---|---|
| Container Disk | 중지/삭제 시 소멸 | `/` | OS, 임시 파일 |
| Volume Disk | 중지해도 유지, 삭제 시 소멸 | `/workspace` | 작업 코드, 데이터셋 |
| Network Volume | Pod 와 독립적, 공유 가능 | 설정 가능 | 여러 Pod 에서 재사용하는 모델 가중치 |

보존해야 할 것은 반드시 `/workspace` 또는 Network Volume 에 둡니다. 컨테이너 디스크에 작업물을 남기지 마세요.

**Network Volume 의 데이터센터 선택은 보기보다 중요합니다.** 문서에 이렇게 적혀 있습니다. 위치가 "가격에 영향을 주지는 않지만, 볼륨을 어떤 GPU 타입과 함께 쓸 수 있는지를 결정한다." 물량이 적은 데이터센터를 고르면 나중에 GPU 선택지가 조용히 좁아집니다.

실제 API 조회 결과입니다 (`runpod_data_centers`, 읽기 전용, 비용 없음).

| | 개수 |
|---|---|
| 전체 데이터센터 | 49 |
| `global_network = true` | 20 |
| S3 호환 API 지원 | 5 — `EUR-IS-1`, `EU-RO-1`, `EU-CZ-1`, `US-KS-2`, `US-CA-2` |

[`terraform/02-pod`](../terraform/02-pod) 의 기본값이 `US-KS-2` 인 것은 두 집합에 모두 속하기 때문입니다.

**접속** — SSH, JupyterLab, Remote-SSH 를 통한 VS Code / Cursor, 그리고 노출한 서비스용 웹 프록시.

**과금** — Pod 가 실행 중인 동안 유휴 여부와 무관하게 분 단위로 과금됩니다. Stop 하면 GPU 는 반납되지만 볼륨 스토리지 요금은 계속 나갑니다. Terminate 해야 전부 제거됩니다. Serverless 와의 가장 큰 차이이자, 실수로 비용이 늘어나는 가장 흔한 경로입니다.

### 🔍 참조 자료 검토

Pod 는 코드 저장소가 필요 없습니다. 콘솔, CLI, SDK 로 기동하기 때문에 Serverless 트랙처럼 포크할 템플릿 레포가 없습니다. 참조 대상은 문서와 이미지입니다.

| 리소스 | 비고 |
|---|---|
| [Pods overview](https://docs.runpod.io/pods/overview) | 제품 개념 |
| [Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) | GPU 선택 가이드 |
| [Connect to a Pod](https://docs.runpod.io/pods/connect-to-a-pod) | SSH / Jupyter / VS Code |
| [Storage types](https://docs.runpod.io/pods/storage/types) | 위 3계층 모델 |
| [Network volumes](https://docs.runpod.io/pods/storage/create-network-volumes) | 공유 영구 스토리지 |
| [Templates](https://docs.runpod.io/pods/templates/overview) | 공식 및 커스텀 템플릿 |
| [Pricing](https://docs.runpod.io/pods/pricing) | 분 단위 요금, 절약 플랜 |
| [runpod/containers](https://github.com/runpod/containers/tree/main/official-templates) | 공식 템플릿의 Dockerfile: `base`, `pytorch`, `nvidia-pytorch`, `rocm`, `pytorch-cluster` |
| [runpod/runpodctl](https://github.com/runpod/runpodctl) | Pod 기동 및 관리용 CLI |

`runpod/containers` 는 Serverless 트랙과 겹치는 지점입니다. `runpod/base` 는 Pod 템플릿의 베이스이면서 동시에 Serverless `worker-template` 이 사용하는 이미지이기도 합니다.

### ⚠️ 시작하기 전에

콘솔에서 지출 한도(spending limit)를 설정하고, 실습이 끝나는 즉시 Pod 를 Terminate 하는 습관을 들이세요. 깜빡하고 켜둔 Pod 가 Runpod 청구서에서 가장 흔한 사고입니다.
