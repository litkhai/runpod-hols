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
| [02-storage](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage) | ✅ Run 2026-11-05 — what survives a stop, a terminate, and a CPU Pod |
| [03-custom-template](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template) | ✅ Run 2026-11-05 — a template with plain and secret environment variables |
| [04-pod-to-serverless](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless) | ✅ Run 2026-11-05 — develop on a Pod, serve the same file from Serverless via a network volume |

### Storage — the concept that matters most

Three tiers, and confusing them is how people lose work:

| Type | Lifetime | Mount | Use for |
|---|---|---|---|
| Container Disk | Destroyed on stop or terminate | `/` | OS, temp files |
| Volume Disk | Survives stop, dies on terminate | `/workspace` | Working code, datasets |
| Network Volume | Independent of any Pod, shareable | configurable | Weights reused across Pods |

Anything you want to keep goes in `/workspace` or a Network Volume. Never leave work on the container disk.

<div class="warn" markdown="1">
**CPU Pods are the exception.** Launched from SDK 1.12 with `volume_in_gb=10`, a CPU Pod came up with `volumeInGb` 0 — the SDK does not send the field for CPU Pods — and `/workspace` sat on the same 10 GB overlay as `/`. There, `/workspace` is container disk. The REST API did the same with `volumeInGb: 10` (Lab 02); a network volume does attach to a CPU Pod.
</div>

### What Lab 02 measured

Run on 2026-11-05 in EU-RO-1 with marker files on each tier ([the lab](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage)):

| Action | Container disk `/` | Pod volume `/workspace` | Network volume `/workspace` |
|---|---|---|---|
| Stop, then start | Wiped | Kept | — |
| Terminate, new Pod on the same volume | — | — | Kept, on a different host |
| CPU Pod | Present | Not created | Mounts and works |

<div class="warn" markdown="1">
**A stopped Pod may not start again right away.** The first `start` 40 seconds after a stop returned *"There are not enough free GPUs on the host machine to start this pod."* The Pod stays tied to its machine; the same call worked eight minutes later. Until then the Pod volume's data is out of reach — a network volume is not tied to a machine.
</div>

While stopped, the account's `currentSpendPerHr` was `0.003` for a 10 GB Pod volume, but the Pod's `costPerHr` still showed the running rate, `0.89`. In EU-RO-1 both kinds of volume were a FUSE mount, `mfs#euro.runpod.net:9421`; `df` showed the whole 2.3 PB filesystem, and writes stopped at the 10 GB allocation with `Disk quota exceeded`.

### Templates and secrets — what Lab 03 found

A template's `env` can hold {% raw %}`{{ RUNPOD_SECRET_<name> }}`{% endraw %}, replaced with the secret's value at boot. Run on 2026-11-05 with a random demo secret ([the lab](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template)):

| Where | What it held |
|---|---|
| `GET /templates`, `GET /pods` | The reference, never the value |
| PID 1's environment | The value (hash matched) |
| `ssh host 'command'` | Neither variable — only interactive shells source `/etc/rp_environment` |
| After rotating the secret | Old value until the Pod was stopped and started; `restart` returned 500 and did nothing |

<div class="warn" markdown="1">
**Inside the Pod a secret is a plain file.** `/etc/rp_environment`, mode 644, held the resolved secret and the Pod's `RUNPOD_API_KEY`. Secrets keep values out of templates and the API, not out of the container.
</div>

### From a Pod to Serverless — what Lab 04 found

One network volume, mounted at `/workspace` on a Pod and at `/runpod-volume` on Serverless workers, lets an endpoint run the file you just tested on the Pod — no image build. The template sets `dockerStartCmd: ["python3", "-u", "/runpod-volume/app/handler.py"]` and `PYTHONPATH` to packages installed on the volume. Run on 2026-11-05 on RTX 4090 in EU-RO-1 ([the lab](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless)):

| Step | Result |
|---|---|
| `pip install --target` onto the volume | About 10 minutes for 9,237 files |
| First job | Worker reported `loaded_from: /runpod-volume/app/handler.py`; `delayTime` 205 s |
| `runsync` on that cold start | Returned `IN_QUEUE` after 90.9 s — poll `/status/{id}` |
| Second job, worker already gone | `delayTime` 47 s |

Good for iterating; for production, bake the code into an image as Serverless Lab 01 does — the volume pins the endpoint to one data center and makes every cold start import over the network.

### What changed in the SDK

| | `runpod` 1.12.0 | `runpod` 2.0.0+ (2026-10-30) |
|---|---|---|
| Pod calls | GraphQL | REST API v2 |
| CPU Pod without an instance id | Sent; the API rejects it: `instanceId` is required | Rejected in the SDK |
| CPU Pod with `volume_mount_path` and no network volume | Sent; the volume is dropped | Rejected in the SDK |

Lab 01 pins `runpod~=1.12.0`. On 2.x its scripts would also misread Pods: the REST objects say `status`, not `desiredStatus`, so the running-Pod check would find nothing. [What else changed in 2.x]({{ '/sdk/client/' | relative_url }}). Instance ids look like `cpu3c-2-4` — flavor, vCPU, memory in GB.

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
| [02-storage](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage) | ✅ 2026-11-05 실행 — 중지, 삭제, CPU Pod 에서 무엇이 남는가 |
| [03-custom-template](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template) | ✅ 2026-11-05 실행 — 일반 환경변수와 시크릿 환경변수를 쓰는 템플릿 |
| [04-pod-to-serverless](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless) | ✅ 2026-11-05 실행 — Pod 에서 개발하고, 네트워크 볼륨으로 같은 파일을 Serverless 에서 서빙 |

### 스토리지 — 가장 중요한 개념

세 계층이 있고, 이걸 혼동하면 작업물을 잃습니다.

| 종류 | 수명 | 마운트 위치 | 용도 |
|---|---|---|---|
| Container Disk | 중지·삭제 시 소멸 | `/` | OS, 임시 파일 |
| Volume Disk | 중지해도 유지, 삭제 시 소멸 | `/workspace` | 작업 코드, 데이터셋 |
| Network Volume | Pod 와 독립적, 공유 가능 | 설정 가능 | 여러 Pod 에서 재사용하는 가중치 |

보존할 것은 반드시 `/workspace` 또는 Network Volume 에 둡니다. 컨테이너 디스크에 작업물을 남기지 마세요.

<div class="warn" markdown="1">
**CPU Pod 은 예외입니다.** SDK 1.12 에서 `volume_in_gb=10` 으로 띄운 CPU Pod 이 `volumeInGb` 0 으로 떴습니다. SDK 가 CPU Pod 에는 이 필드를 보내지 않기 때문입니다. `/workspace` 는 `/` 와 같은 10 GB overlay 위에 있었습니다. 즉 여기서 `/workspace` 는 컨테이너 디스크입니다. REST API 에 `volumeInGb: 10` 을 줘도 같았고 (Lab 02), 네트워크 볼륨은 CPU Pod 에도 붙습니다.
</div>

### Lab 02 가 측정한 것

2026-11-05 EU-RO-1 에서 계층마다 표식 파일을 두고 실행했습니다 ([실습](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage)).

| 동작 | 컨테이너 디스크 `/` | Pod 볼륨 `/workspace` | 네트워크 볼륨 `/workspace` |
|---|---|---|---|
| 중지 후 시작 | 초기화 | 유지 | — |
| 삭제 후 같은 볼륨으로 새 Pod | — | — | 유지, 다른 호스트에서 |
| CPU Pod | 있음 | 만들어지지 않음 | 마운트되고 동작 |

<div class="warn" markdown="1">
**중지한 Pod 이 바로 다시 시작되지 않을 수 있습니다.** 중지 40초 뒤 첫 `start` 가 *"There are not enough free GPUs on the host machine to start this pod."* 를 돌려줬습니다. Pod 은 원래 머신에 묶여 있고, 같은 호출이 8분 뒤에 성공했습니다. 그 전까지 Pod 볼륨의 데이터에는 손이 닿지 않습니다. 네트워크 볼륨은 머신에 묶이지 않습니다.
</div>

중지 중 계정의 `currentSpendPerHr` 는 10 GB Pod 볼륨에 대해 `0.003` 이었지만, Pod 의 `costPerHr` 는 실행 중 요금 `0.89` 를 그대로 보여줬습니다. EU-RO-1 에서는 두 종류의 볼륨 모두 FUSE 마운트 `mfs#euro.runpod.net:9421` 이었고, `df` 는 2.3 PB 파일시스템 전체를 보여줬으며, 쓰기는 10 GB 할당에서 `Disk quota exceeded` 로 멈췄습니다.

### 템플릿과 시크릿 — Lab 03 이 확인한 것

템플릿의 `env` 에 {% raw %}`{{ RUNPOD_SECRET_<name> }}`{% endraw %} 를 넣으면 부팅 시 시크릿 값으로 바뀝니다. 2026-11-05 임의의 데모 시크릿으로 실행했습니다 ([실습](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template)).

| 위치 | 담긴 것 |
|---|---|
| `GET /templates`, `GET /pods` | 참조. 값은 절대 아님 |
| PID 1 의 환경 | 값 (해시 일치) |
| `ssh host 'command'` | 두 변수 모두 없음 — 대화형 셸만 `/etc/rp_environment` 를 읽음 |
| 시크릿 교체 후 | Pod 을 중지·시작할 때까지 이전 값. `restart` 는 500 을 돌려주고 아무것도 하지 않음 |

<div class="warn" markdown="1">
**Pod 안에서 시크릿은 평범한 파일입니다.** 권한 644 인 `/etc/rp_environment` 에 치환된 시크릿과 Pod 의 `RUNPOD_API_KEY` 가 들어 있었습니다. 시크릿은 값을 템플릿과 API 에서 감춰 주지만, 컨테이너 안에서까지 감추지는 않습니다.
</div>

### Pod 에서 Serverless 로 — Lab 04 가 확인한 것

네트워크 볼륨 하나를 Pod 에는 `/workspace`, Serverless 워커에는 `/runpod-volume` 으로 붙이면, 이미지 빌드 없이 Pod 에서 방금 테스트한 파일을 엔드포인트가 실행합니다. 템플릿에 `dockerStartCmd: ["python3", "-u", "/runpod-volume/app/handler.py"]` 와 볼륨에 설치한 패키지를 가리키는 `PYTHONPATH` 를 둡니다. 2026-11-05 EU-RO-1 의 RTX 4090 에서 실행했습니다 ([실습](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless)).

| 단계 | 결과 |
|---|---|
| 볼륨에 `pip install --target` | 파일 9,237개에 약 10분 |
| 첫 작업 | 워커가 `loaded_from: /runpod-volume/app/handler.py` 보고. `delayTime` 205초 |
| 그 콜드 스타트에서 `runsync` | 90.9초 뒤 `IN_QUEUE` 반환 — `/status/{id}` 를 폴링 |
| 두 번째 작업, 워커는 이미 종료 | `delayTime` 47초 |

반복 개발에는 좋습니다. 프로덕션은 Serverless Lab 01 처럼 코드를 이미지에 구우세요. 볼륨은 엔드포인트를 한 데이터센터에 묶고, 콜드 스타트마다 네트워크 너머로 import 하게 만듭니다.

### SDK 에서 바뀐 것

| | `runpod` 1.12.0 | `runpod` 2.0.0+ (2026-10-30) |
|---|---|---|
| Pod 호출 | GraphQL | REST API v2 |
| 인스턴스 ID 없는 CPU Pod | 전송됨. API 가 거부: `instanceId` 필수 | SDK 에서 거부 |
| 네트워크 볼륨 없이 `volume_mount_path` 를 준 CPU Pod | 전송됨. 볼륨은 빠짐 | SDK 에서 거부 |

Lab 01 은 `runpod~=1.12.0` 으로 고정합니다. 2.x 에서는 스크립트가 Pod 도 잘못 읽습니다. REST 객체에는 `desiredStatus` 가 아니라 `status` 가 있어 실행 중 Pod 확인이 아무것도 찾지 못합니다. [2.x 의 다른 변경점]({{ '/sdk/client/' | relative_url }}). 인스턴스 ID 는 `cpu3c-2-4` 처럼 flavor, vCPU, 메모리(GB) 순입니다.

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
