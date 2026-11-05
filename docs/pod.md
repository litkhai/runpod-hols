---
layout: default
title: Pod
permalink: /pod/
---

# Pod

<div class="lang" data-lang="en" markdown="1">

## English

<div class="note" markdown="1">
**Lab 01 runs end to end** — launch from Python, connect over SSH, tear down, CPU by default. Run on 2026-11-05 with `runpod` 1.12.0: a `cpu3c-2-4` CPU Pod at $0.06/hr, SSH reachable about 4 minutes after launch, under one cent in total. [See the lab](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect).
</div>

A Pod is a GPU or CPU container you rent and control. Unlike Serverless it stays up until you stop it, keeps its filesystem, and gives you shell access. This is where development, experimentation and fine-tuning happen.

### Labs

| Lab | Status |
|---|---|
| [01-launch-connect](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect) | ✅ Run 2026-11-05 — launch from Python, connect over SSH, tear down. CPU by default |
| 02-storage | 📋 Planned — Container Disk vs Volume vs Network Volume, what survives a stop |
| 03-custom-template | 📋 Planned — build a custom Pod template, environment variables, secrets |
| 04-pod-to-serverless | 📋 Planned — develop on a Pod, then package the result as a Serverless worker |

### Storage — the concept that matters most

Three tiers, and confusing them is how people lose work:

| Type | Lifetime | Mount | Use for |
|---|---|---|---|
| Container Disk | Destroyed on stop or terminate | `/` | OS, temp files |
| Volume Disk | Survives stop, dies on terminate | `/workspace` | Working code, datasets |
| Network Volume | Independent of any Pod, shareable | configurable | Weights reused across Pods |

Anything you want to keep goes in `/workspace` or a Network Volume. Never leave work on the container disk.

<div class="warn" markdown="1">
**CPU Pods are the exception.** Launched from SDK 1.12 with `volume_in_gb=10`, a CPU Pod came up with `volumeInGb` 0 — the SDK does not send the field for CPU Pods — and `/workspace` sat on the same 10 GB overlay as `/`. There, `/workspace` is container disk.
</div>

### What changed in the SDK

| | `runpod` 1.12.0 | `runpod` 2.0.0+ (2026-10-30) |
|---|---|---|
| Pod calls | GraphQL | REST API v2 |
| CPU Pod without an instance id | Sent; the API rejects it: `instanceId` is required | Rejected in the SDK |
| CPU Pod with `volume_mount_path` and no network volume | Sent; the volume is dropped | Rejected in the SDK |

Lab 01 pins `runpod~=1.12.0`. Instance ids look like `cpu3c-2-4` — flavor, vCPU, memory in GB.

### Billing

Per minute, for as long as the Pod is running, idle or not. Stopping releases the GPU but still bills volume storage. Terminating removes everything.

<div class="danger" markdown="1">
This is the single biggest difference from Serverless and the easiest way to run up a bill by accident. Set a spending limit, and get into the habit of terminating the moment a lab ends.
</div>

### References

Pods need no code repository — you launch them from the console, CLI or SDK — so unlike the Serverless track there is no template repo to fork.

[Pods overview](https://docs.runpod.io/pods/overview) ·
[Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) ·
[Connect](https://docs.runpod.io/pods/connect-to-a-pod) ·
[Storage types](https://docs.runpod.io/pods/storage/types) ·
[Network volumes](https://docs.runpod.io/pods/storage/create-network-volumes) ·
[Templates](https://docs.runpod.io/pods/templates/overview) ·
[Pricing](https://docs.runpod.io/pods/pricing) ·
[runpod/containers](https://github.com/runpod/containers/tree/main/official-templates)

Note that `runpod/containers` is shared ground with the Serverless track — `runpod/base` is both the Pod template base and the image the Serverless `worker-template` builds on.

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

<div class="note" markdown="1">
**Lab 01 은 처음부터 끝까지 실행됩니다** — Python 으로 기동, SSH 접속, 정리, 기본값 CPU. 2026-11-05 `runpod` 1.12.0 으로 실행했습니다. `cpu3c-2-4` CPU Pod 시간당 $0.06, 기동 후 약 4분 뒤 SSH 접속, 총비용 1센트 미만. [실습 보기](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect).
</div>

Pod 는 직접 빌려서 제어하는 GPU 또는 CPU 컨테이너입니다. Serverless 와 달리 중지할 때까지 떠 있고, 파일시스템이 유지되며, 셸 접속이 가능합니다. 개발, 실험, 파인튜닝이 이루어지는 곳입니다.

### 실습 목록

| 실습 | 상태 |
|---|---|
| [01-launch-connect](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect) | ✅ 2026-11-05 실행 — Python 으로 기동, SSH 접속, 정리. 기본값 CPU |
| 02-storage | 📋 계획됨 — Container Disk vs Volume vs Network Volume, 중지 시 무엇이 남는가 |
| 03-custom-template | 📋 계획됨 — 커스텀 Pod 템플릿 제작, 환경변수, 시크릿 |
| 04-pod-to-serverless | 📋 계획됨 — Pod 에서 개발한 결과물을 Serverless 워커로 패키징 |

### 스토리지 — 가장 중요한 개념

세 계층이 있고, 이걸 혼동하면 작업물을 잃습니다.

| 종류 | 수명 | 마운트 위치 | 용도 |
|---|---|---|---|
| Container Disk | 중지·삭제 시 소멸 | `/` | OS, 임시 파일 |
| Volume Disk | 중지해도 유지, 삭제 시 소멸 | `/workspace` | 작업 코드, 데이터셋 |
| Network Volume | Pod 와 독립적, 공유 가능 | 설정 가능 | 여러 Pod 에서 재사용하는 가중치 |

보존할 것은 반드시 `/workspace` 또는 Network Volume 에 둡니다. 컨테이너 디스크에 작업물을 남기지 마세요.

<div class="warn" markdown="1">
**CPU Pod 은 예외입니다.** SDK 1.12 에서 `volume_in_gb=10` 으로 띄운 CPU Pod 이 `volumeInGb` 0 으로 떴습니다. SDK 가 CPU Pod 에는 이 필드를 보내지 않기 때문입니다. `/workspace` 는 `/` 와 같은 10 GB overlay 위에 있었습니다. 즉 여기서 `/workspace` 는 컨테이너 디스크입니다.
</div>

### SDK 에서 바뀐 것

| | `runpod` 1.12.0 | `runpod` 2.0.0+ (2026-10-30) |
|---|---|---|
| Pod 호출 | GraphQL | REST API v2 |
| 인스턴스 ID 없는 CPU Pod | 전송됨. API 가 거부: `instanceId` 필수 | SDK 에서 거부 |
| 네트워크 볼륨 없이 `volume_mount_path` 를 준 CPU Pod | 전송됨. 볼륨은 빠짐 | SDK 에서 거부 |

Lab 01 은 `runpod~=1.12.0` 으로 고정합니다. 인스턴스 ID 는 `cpu3c-2-4` 처럼 flavor, vCPU, 메모리(GB) 순입니다.

### 과금

Pod 가 실행 중인 동안 유휴 여부와 무관하게 분 단위로 과금됩니다. Stop 하면 GPU 는 반납되지만 볼륨 스토리지 요금은 계속 나갑니다. Terminate 해야 전부 제거됩니다.

<div class="danger" markdown="1">
Serverless 와의 가장 큰 차이이자, 실수로 비용이 늘어나는 가장 흔한 경로입니다. 지출 한도를 설정하고, 실습이 끝나는 즉시 Terminate 하는 습관을 들이세요.
</div>

### 참조 자료

Pod 는 코드 저장소가 필요 없습니다. 콘솔, CLI, SDK 로 기동하므로 Serverless 트랙처럼 포크할 템플릿 레포가 없습니다.

[Pods overview](https://docs.runpod.io/pods/overview) ·
[Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) ·
[Connect](https://docs.runpod.io/pods/connect-to-a-pod) ·
[Storage types](https://docs.runpod.io/pods/storage/types) ·
[Network volumes](https://docs.runpod.io/pods/storage/create-network-volumes) ·
[Templates](https://docs.runpod.io/pods/templates/overview) ·
[Pricing](https://docs.runpod.io/pods/pricing) ·
[runpod/containers](https://github.com/runpod/containers/tree/main/official-templates)

`runpod/containers` 는 Serverless 트랙과 겹치는 지점입니다. `runpod/base` 는 Pod 템플릿의 베이스이면서 동시에 Serverless `worker-template` 이 사용하는 이미지이기도 합니다.

</div>
