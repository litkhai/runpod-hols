---
layout: default
title: Pod
permalink: /pod/
---

# Pod

<div class="lang" data-lang="en" markdown="1">

## English

<div class="note" markdown="1">
**Status: planned.** The structure and references are settled; the lab files are not written yet. The Terraform track already provisions a Pod — see [02-pod]({{ '/terraform/' | relative_url }}).
</div>

A Pod is a GPU or CPU container you rent and control. Unlike Serverless it stays up until you stop it, keeps its filesystem, and gives you shell access. This is where development, experimentation and fine-tuning happen.

### Planned labs

| Lab | Contents |
|---|---|
| 01-launch-and-connect | Pick a GPU, launch from a template, connect via SSH / JupyterLab / VS Code, verify with `nvidia-smi` |
| 02-storage | Container Disk vs Volume vs Network Volume — what survives a stop |
| 03-custom-template | Build a custom Pod template, environment variables, secrets |
| 04-pod-to-serverless | Develop on a Pod, then package the result as a Serverless worker |

### Storage — the concept that matters most

Three tiers, and confusing them is how people lose work:

| Type | Lifetime | Mount | Use for |
|---|---|---|---|
| Container Disk | Destroyed on stop or terminate | `/` | OS, temp files |
| Volume Disk | Survives stop, dies on terminate | `/workspace` | Working code, datasets |
| Network Volume | Independent of any Pod, shareable | configurable | Weights reused across Pods |

Anything you want to keep goes in `/workspace` or a Network Volume. Never leave work on the container disk.

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
**상태: 계획됨.** 구조와 참조 자료는 확정했고 실습 파일은 아직 작성 전입니다. Terraform 트랙에서는 이미 Pod 를 프로비저닝합니다 — [02-pod]({{ '/terraform/' | relative_url }}) 참조.
</div>

Pod 는 직접 빌려서 제어하는 GPU 또는 CPU 컨테이너입니다. Serverless 와 달리 중지할 때까지 떠 있고, 파일시스템이 유지되며, 셸 접속이 가능합니다. 개발, 실험, 파인튜닝이 이루어지는 곳입니다.

### 계획된 실습

| 실습 | 내용 |
|---|---|
| 01-launch-and-connect | GPU 선택, 템플릿으로 기동, SSH / JupyterLab / VS Code 접속, `nvidia-smi` 확인 |
| 02-storage | Container Disk vs Volume vs Network Volume — 중지 시 무엇이 남는가 |
| 03-custom-template | 커스텀 Pod 템플릿 제작, 환경변수, 시크릿 |
| 04-pod-to-serverless | Pod 에서 개발한 결과물을 Serverless 워커로 패키징 |

### 스토리지 — 가장 중요한 개념

세 계층이 있고, 이걸 혼동하면 작업물을 잃습니다.

| 종류 | 수명 | 마운트 위치 | 용도 |
|---|---|---|---|
| Container Disk | 중지·삭제 시 소멸 | `/` | OS, 임시 파일 |
| Volume Disk | 중지해도 유지, 삭제 시 소멸 | `/workspace` | 작업 코드, 데이터셋 |
| Network Volume | Pod 와 독립적, 공유 가능 | 설정 가능 | 여러 Pod 에서 재사용하는 가중치 |

보존할 것은 반드시 `/workspace` 또는 Network Volume 에 둡니다. 컨테이너 디스크에 작업물을 남기지 마세요.

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
