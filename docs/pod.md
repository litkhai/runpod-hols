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

<figure class="shot"><a href="{{ '/assets/img/pod/create-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-storage.webp' | relative_url }}" alt="Create storage dialog: Network volume, Global volume (beta) and Volume disk (legacy) with prices" loading="lazy" width="1400" height="998"></a><figcaption>Create storage, from the Pod deploy form, 2026-11-07: Network volume USD 0.07/GB-month in one datacenter; Global volume (beta) USD 0.09/GB-month plus IOPS across datacenters; Volume disk (legacy — the Pod volume) USD 0.10/GB-month running, 0.20 stopped.</figcaption></figure>

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

### Global volume (beta) — what was measured

A third kind of persistent storage, listed first in **Add volume** with a **Global** badge: no datacenter, no size, USD 0.09 per GB-month stored plus IOPS. It is created through `POST https://api.runpod.io/v2/global-volumes` (name only) or the console, but REST v1 cannot attach it: the console's deploy mutation passes `volumeMounts: [{volumeId, volumeType: "OBJECT_STORE_VOLUME", mountPath: "/workspace"}]`. Inside the Pod it is a FUSE mount of an object store.

| 2026-11-07 | Pod A, CA-MTL-1 (RTX A5000) | Pod B, EU-RO-1 (RTX 4090) |
|---|---|---|
| `/workspace` | `fuse.geesefs`, 1.0P | same volume |
| Write 512 MiB | **61 MiB/s** (container disk 273) | |
| First read of that file | 344 MiB/s | **39 MiB/s** across regions |
| Re-read | 275 MiB/s | 985 MiB/s (local cache) |
| 200 small files | 338 ms | 59 ms |

These figures came from `dd` on `/dev/urandom`, which caps near 300 MB/s by itself; the same tiers measured with one fio method are in [Storage]({{ '/readings/storage/#benchmark' | relative_url }}).

<figure class="shot"><a href="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}" alt="Storage page listing the global volume with 537MB stored, 205 objects, location Any" loading="lazy" width="1400" height="998"></a><figcaption>Storage, 2026-11-07: the test volume — location <strong>Any</strong>, 537 MB in 205 objects, USD 0.05/month.</figcaption></figure>

- **One volume, two continents.** A marker and a 512 MiB file written in Canada were readable in Romania with the same sha256; a new file written in Romania appeared in Canada **3 s** later.
- **Concurrent writes diverge.** Both Pods wrote the same file at the same moment; each kept reading its own version — still so 45 s later. The docs say the last write wins and recommend network volumes for shared mutable data; here neither Pod saw the other's write.
- **Billing is per object.** The Storage page showed 537 MB, 205 objects, USD 0.05/month for this test.
- Pod B was deployed with the same GraphQL mutation and `dataCenterId: "EU-RO-1"` — the first choice, RTX A5000, had no capacity there.

Use it for read-mostly data that several regions need — weights, configs, datasets — and keep checkpoints and anything two workers write on a network volume or the container disk.

### Templates and secrets — what Lab 03 found

A template's `env` can hold {% raw %}`{{ RUNPOD_SECRET_<name> }}`{% endraw %}, replaced with the secret's value at boot. Run on 2026-11-05 with a random demo secret ([the lab](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template)):

<figure class="shot"><a href="{{ '/assets/img/pod/create-secret.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-secret.webp' | relative_url }}" alt="Create secret form with the RUNPOD_SECRET reference example" loading="lazy" width="1400" height="998"></a><figcaption>Create secret (Credentials → Secrets): the form states the rule above — a secret reaches a Pod or endpoint only through an env var that references it.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}"><img src="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}" alt="Create template form rejecting a reference to a secret that does not exist" loading="lazy" width="1400" height="998"></a><figcaption>In the console, Create template checks the reference: <code>RUNPOD_SECRET_hf_token</code> does not exist, so the field reads "Secret not found" and the template cannot be created. The form was discarded, not saved.</figcaption></figure>

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

<figure class="shot"><a href="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}"><img src="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}" alt="Billing explorer with daily spend split by Cloud GPU, Cloud CPU, Serverless and Storage" loading="lazy" width="1400" height="998"></a><figcaption>Billing → Billing explorer: daily spend by product, in UTC, and "1 hour behind" — a Pod deleted a moment ago is not there yet. 2026-11-05 below is the day of the Pod labs.</figcaption></figure>

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

<figure class="shot"><a href="{{ '/assets/img/pod/create-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-storage.webp' | relative_url }}" alt="Create storage 화면: Network volume, Global volume (베타), Volume disk (레거시) 와 가격" loading="lazy" width="1400" height="998"></a><figcaption>Pod 배포 화면의 Create storage, 2026-11-07: Network volume 은 데이터센터 하나에 GB·월 USD 0.07, Global volume (베타) 은 데이터센터 간 GB·월 USD 0.09 + IOPS, Volume disk (레거시, 곧 Pod 볼륨) 는 실행 중 GB·월 USD 0.10, 중지 시 0.20.</figcaption></figure>

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

### Global volume (베타) — 측정한 것

세 번째 영구 스토리지로, **Add volume** 목록 맨 앞에 **Global** 배지와 함께 나옵니다. 데이터센터도 크기도 없고, 저장 GB·월 USD 0.09 에 IOPS 요금이 붙습니다. `POST https://api.runpod.io/v2/global-volumes` (이름만) 나 콘솔로 만들지만, REST v1 로는 Pod 에 붙일 수 없습니다. 콘솔의 배포 mutation 은 `volumeMounts: [{volumeId, volumeType: "OBJECT_STORE_VOLUME", mountPath: "/workspace"}]` 를 보냅니다. Pod 안에서는 오브젝트 스토어의 FUSE 마운트입니다.

| 2026-11-07 | Pod A, CA-MTL-1 (RTX A5000) | Pod B, EU-RO-1 (RTX 4090) |
|---|---|---|
| `/workspace` | `fuse.geesefs`, 1.0P | 같은 볼륨 |
| 512 MiB 쓰기 | **61 MiB/s** (컨테이너 디스크 273) | |
| 그 파일 첫 읽기 | 344 MiB/s | 지역 간 **39 MiB/s** |
| 다시 읽기 | 275 MiB/s | 985 MiB/s (로컬 캐시) |
| 작은 파일 200개 | 338 ms | 59 ms |

이 수치는 `/dev/urandom` 으로 `dd` 를 돌려 얻은 것인데, urandom 자체가 300 MB/s 근처에서 막힙니다. 같은 fio 방법으로 모든 층을 다시 잰 결과는 [Storage]({{ '/readings/storage/#benchmark-ko' | relative_url }}) 에 있습니다.

<figure class="shot"><a href="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}" alt="537MB, 객체 205개, 위치 Any 로 표시된 global volume 의 Storage 화면" loading="lazy" width="1400" height="998"></a><figcaption>Storage, 2026-11-07: 테스트 볼륨 — 위치 <strong>Any</strong>, 객체 205개에 537 MB, 월 USD 0.05.</figcaption></figure>

- **볼륨 하나, 두 대륙.** 캐나다에서 쓴 마커와 512 MiB 파일을 루마니아에서 같은 sha256 으로 읽었고, 루마니아에서 쓴 새 파일은 **3초** 뒤 캐나다에 보였습니다.
- **동시 쓰기는 갈라집니다.** 두 Pod 이 같은 순간에 같은 파일을 쓰자 각자 자기 버전을 계속 읽었고, 45초 뒤에도 그대로였습니다. 문서는 마지막 쓰기가 이긴다고 하고 공유 가변 데이터에는 네트워크 볼륨을 권하는데, 여기서는 어느 쪽도 상대의 쓰기를 보지 못했습니다.
- **과금은 객체 단위입니다.** Storage 화면에 이 테스트는 537 MB, 객체 205개, 월 USD 0.05 로 나왔습니다.
- Pod B 는 같은 GraphQL mutation 에 `dataCenterId: "EU-RO-1"` 을 넣어 띄웠습니다. 첫 선택인 RTX A5000 은 그곳에 자리가 없었습니다.

여러 지역이 함께 읽는 데이터 — 가중치, 설정, 데이터셋 — 에 쓰고, 체크포인트처럼 둘 이상이 쓰는 데이터는 네트워크 볼륨이나 컨테이너 디스크에 두세요.

### 템플릿과 시크릿 — Lab 03 이 확인한 것

템플릿의 `env` 에 {% raw %}`{{ RUNPOD_SECRET_<name> }}`{% endraw %} 를 넣으면 부팅 시 시크릿 값으로 바뀝니다. 2026-11-05 임의의 데모 시크릿으로 실행했습니다 ([실습](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template)).

<figure class="shot"><a href="{{ '/assets/img/pod/create-secret.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-secret.webp' | relative_url }}" alt="RUNPOD_SECRET 참조 예시가 있는 Create secret 화면" loading="lazy" width="1400" height="998"></a><figcaption>Create secret (Credentials → Secrets): 화면도 위 규칙을 그대로 적어 둔다. 시크릿은 그것을 참조하는 환경변수를 통해서만 Pod 나 엔드포인트에 들어간다.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}"><img src="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}" alt="존재하지 않는 시크릿 참조를 거부하는 Create template 화면" loading="lazy" width="1400" height="998"></a><figcaption>콘솔의 Create template 은 참조를 검사한다. <code>RUNPOD_SECRET_hf_token</code> 이 없으므로 칸에 "Secret not found" 가 뜨고 템플릿을 만들 수 없다. 이 양식은 저장하지 않고 버렸다.</figcaption></figure>

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

<figure class="shot"><a href="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}"><img src="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}" alt="Cloud GPU, Cloud CPU, Serverless, Storage 별 일일 지출을 보여주는 Billing explorer" loading="lazy" width="1400" height="998"></a><figcaption>Billing → Billing explorer: 제품별 일일 지출, UTC 기준, "1 hour behind". 방금 지운 Pod 는 아직 나오지 않는다. 아래 2026-11-05 는 Pod 실습을 한 날이다.</figcaption></figure>

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

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

<div class="note" markdown="1">
**Lab 01 已端到端跑通**——从 Python 启动、通过 SSH 连接、销毁，默认使用 CPU。2026-11-05 使用 `runpod` 1.12.0 运行：一个 `cpu3c-2-4` CPU Pod，$0.06/hr，启动后约 4 分钟可通过 SSH 连接，总费用不到一美分。[查看实验](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect)。
</div>

Pod 是你租用并自行控制的 GPU 或 CPU 容器。与 Serverless 不同，它会一直运行直到你停止它，保留其文件系统，并提供 shell 访问。开发、实验和微调都在这里进行。

### 实验

| 实验 | 状态 |
|---|---|
| [01-launch-connect](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect) | ✅ 2026-11-05 已运行——从 Python 启动、通过 SSH 连接、销毁。默认使用 CPU |
| [02-storage](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage) | ✅ 2026-11-05 已运行——stop、terminate 以及 CPU Pod 之后各保留了什么 |
| [03-custom-template](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template) | ✅ 2026-11-05 已运行——带普通环境变量和 secret 环境变量的 template |
| [04-pod-to-serverless](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless) | ✅ 2026-11-05 已运行——在 Pod 上开发，通过 network volume 从 Serverless 提供同一个文件 |

### 存储——最重要的概念

共有三层，把它们搞混正是人们丢失工作成果的原因：

| 类型 | 生命周期 | 挂载点 | 用途 |
|---|---|---|---|
| Container Disk | stop 或 terminate 时销毁 | `/` | 操作系统、临时文件 |
| Volume Disk | stop 后保留，terminate 时销毁 | `/workspace` | 工作代码、数据集 |
| Network Volume | 独立于任何 Pod，可共享 | 可配置 | 在多个 Pod 间复用的权重 |

<figure class="shot"><a href="{{ '/assets/img/pod/create-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-storage.webp' | relative_url }}" alt="Create storage 对话框：Network volume、Global volume（测试版）和 Volume disk（旧版）及价格" loading="lazy" width="1400" height="998"></a><figcaption>Pod 部署表单中的 Create storage，2026-11-07：Network volume 单个数据中心，每 GB·月 USD 0.07；Global volume（测试版）跨数据中心，每 GB·月 USD 0.09 加 IOPS；Volume disk（旧版，即 Pod 卷）运行时每 GB·月 USD 0.10，停止时 0.20。</figcaption></figure>

任何想保留的东西都放在 `/workspace` 或 Network Volume 中。绝不要把工作成果留在 container disk 上。

<div class="warn" markdown="1">
**CPU Pod 是例外。** 用 SDK 1.12 以 `volume_in_gb=10` 启动的 CPU Pod，启动后 `volumeInGb` 为 0——SDK 不会为 CPU Pod 发送该字段——而 `/workspace` 与 `/` 位于同一个 10 GB overlay 上。在这种情况下，`/workspace` 就是 container disk。REST API 使用 `volumeInGb: 10` 时结果相同（Lab 02）；network volume 则可以挂载到 CPU Pod 上。
</div>

### Lab 02 的测量结果

2026-11-05 在 EU-RO-1 运行，在每一层都放置了标记文件（[实验](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage)）：

| 操作 | Container disk `/` | Pod volume `/workspace` | Network volume `/workspace` |
|---|---|---|---|
| stop 后再 start | 被清空 | 保留 | — |
| terminate，在同一 volume 上新建 Pod | — | — | 保留，且在不同的主机上 |
| CPU Pod | 存在 | 未创建 | 可挂载并正常工作 |

<div class="warn" markdown="1">
**已停止的 Pod 不一定能立即再次启动。** stop 后 40 秒执行的第一次 `start` 返回了 *"There are not enough free GPUs on the host machine to start this pod."* Pod 始终绑定在它的机器上；同样的调用在八分钟后成功了。在此之前，Pod volume 中的数据无法访问——而 network volume 不绑定于某台机器。
</div>

停止期间，对于一个 10 GB 的 Pod volume，账号的 `currentSpendPerHr` 为 `0.003`，但 Pod 的 `costPerHr` 仍显示运行时的费率 `0.89`。在 EU-RO-1，两种 volume 都是 FUSE 挂载 `mfs#euro.runpod.net:9421`；`df` 显示的是整个 2.3 PB 的文件系统，而写入在达到 10 GB 分配量时以 `Disk quota exceeded` 停止。

### Global volume（测试版）——实测结果

第三种持久存储，在 **Add volume** 列表中排在最前，带 **Global** 标记：没有数据中心，也没有容量，按存储每 GB·月 USD 0.09 加 IOPS 计费。可以用 `POST https://api.runpod.io/v2/global-volumes`（只需名称）或控制台创建，但 REST v1 无法把它挂到 Pod 上：控制台的部署 mutation 传的是 `volumeMounts: [{volumeId, volumeType: "OBJECT_STORE_VOLUME", mountPath: "/workspace"}]`。在 Pod 内它是一个对象存储的 FUSE 挂载。

| 2026-11-07 | Pod A，CA-MTL-1（RTX A5000） | Pod B，EU-RO-1（RTX 4090） |
|---|---|---|
| `/workspace` | `fuse.geesefs`，1.0P | 同一个卷 |
| 写入 512 MiB | **61 MiB/s**（容器盘 273） | |
| 首次读取该文件 | 344 MiB/s | 跨区域 **39 MiB/s** |
| 再次读取 | 275 MiB/s | 985 MiB/s（本地缓存） |
| 200 个小文件 | 338 ms | 59 ms |

这些数字来自对 `/dev/urandom` 运行 `dd`，而 urandom 本身就在 300 MB/s 附近封顶；用同一种 fio 方法重新测量所有层级的结果见 [Storage]({{ '/readings/storage/#benchmark-zh' | relative_url }})。

<figure class="shot"><a href="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}" alt="Storage 页面列出的 global volume：537MB、205 个对象、位置 Any" loading="lazy" width="1400" height="998"></a><figcaption>Storage，2026-11-07：测试卷——位置 <strong>Any</strong>，205 个对象共 537 MB，每月 USD 0.05。</figcaption></figure>

- **一个卷，两个大洲。** 在加拿大写入的标记文件和 512 MiB 文件，在罗马尼亚读取时 sha256 一致；在罗马尼亚写入的新文件 **3 秒** 后出现在加拿大。
- **并发写入会分叉。** 两个 Pod 在同一时刻写同一个文件，各自一直读到自己的版本，45 秒后仍然如此。文档说最后一次写入生效，并建议共享可变数据使用 network volume；而这里两边都没有看到对方的写入。
- **按对象计费。** 这次测试在 Storage 页面显示 537 MB、205 个对象、每月 USD 0.05。
- Pod B 是用同一个 GraphQL mutation 加上 `dataCenterId: "EU-RO-1"` 部署的——首选的 RTX A5000 在那里没有容量。

适合多个区域都要读取、以读为主的数据——权重、配置、数据集；检查点以及会被多个 worker 写入的数据，请放在 network volume 或容器盘上。

### Template 与 secret——Lab 03 的发现

template 的 `env` 中可以写 {% raw %}`{{ RUNPOD_SECRET_<name> }}`{% endraw %}，启动时会被替换为 secret 的值。2026-11-05 使用一个随机的演示 secret 运行（[实验](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template)）：

<figure class="shot"><a href="{{ '/assets/img/pod/create-secret.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-secret.webp' | relative_url }}" alt="带有 RUNPOD_SECRET 引用示例的 Create secret 表单" loading="lazy" width="1400" height="998"></a><figcaption>Create secret（Credentials → Secrets）：表单本身也写明了上面的规则——secret 只有通过引用它的环境变量才会进入 Pod 或端点。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}"><img src="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}" alt="Create template 表单拒绝引用一个不存在的 secret" loading="lazy" width="1400" height="998"></a><figcaption>控制台的 Create template 会检查引用：<code>RUNPOD_SECRET_hf_token</code> 不存在，因此字段显示 "Secret not found"，无法创建模板。该表单已丢弃，未保存。</figcaption></figure>

| 位置 | 其中的内容 |
|---|---|
| `GET /templates`、`GET /pods` | 引用，从不包含值 |
| PID 1 的环境 | 值（哈希一致） |
| `ssh host 'command'` | 两个变量都没有——只有交互式 shell 会 source `/etc/rp_environment` |
| 轮换 secret 之后 | 在 Pod 被 stop 再 start 之前一直是旧值；`restart` 返回 500 且没有任何效果 |

<div class="warn" markdown="1">
**在 Pod 内部，secret 只是一个普通文件。** `/etc/rp_environment`（权限 644）中存有解析后的 secret 以及 Pod 的 `RUNPOD_API_KEY`。secret 让值不出现在 template 和 API 中，但不会让值不出现在容器里。
</div>

### 从 Pod 到 Serverless——Lab 04 的发现

一个 network volume 在 Pod 上挂载到 `/workspace`，在 Serverless worker 上挂载到 `/runpod-volume`，就能让 endpoint 运行你刚在 Pod 上测试过的文件——无需构建镜像。template 设置 `dockerStartCmd: ["python3", "-u", "/runpod-volume/app/handler.py"]`，并将 `PYTHONPATH` 指向安装在 volume 上的包。2026-11-05 在 EU-RO-1 的 RTX 4090 上运行（[实验](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless)）：

| 步骤 | 结果 |
|---|---|
| 用 `pip install --target` 安装到 volume | 9,237 个文件约需 10 分钟 |
| 第一个 job | worker 报告 `loaded_from: /runpod-volume/app/handler.py`；`delayTime` 205 s |
| 在这次冷启动上执行 `runsync` | 90.9 s 后返回 `IN_QUEUE`——请轮询 `/status/{id}` |
| 第二个 job，worker 已经消失 | `delayTime` 47 s |

适合迭代开发；用于生产时，应像 Serverless Lab 01 那样把代码打包进镜像——volume 会把 endpoint 固定在一个数据中心，并使每次冷启动都通过网络 import。

### SDK 中的变化

| | `runpod` 1.12.0 | `runpod` 2.0.0+（2026-10-30） |
|---|---|---|
| Pod 调用 | GraphQL | REST API v2 |
| 不带 instance id 的 CPU Pod | 会发送；API 拒绝：`instanceId` 为必填 | 在 SDK 中被拒绝 |
| 带 `volume_mount_path` 但没有 network volume 的 CPU Pod | 会发送；volume 被丢弃 | 在 SDK 中被拒绝 |

Lab 01 固定使用 `runpod~=1.12.0`。在 2.x 上，它的脚本还会误读 Pod：REST 对象中的字段是 `status` 而不是 `desiredStatus`，所以检查运行中 Pod 的逻辑将什么也找不到。[2.x 中的其他变化]({{ '/sdk/client/' | relative_url }})。instance id 形如 `cpu3c-2-4`——规格类型、vCPU、以 GB 计的内存。

### 计费

按分钟计费，只要 Pod 在运行就计费，无论是否空闲。stop 会释放 GPU，但 volume 存储仍会计费。terminate 会删除一切。

<figure class="shot"><a href="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}"><img src="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}" alt="Billing explorer 按 Cloud GPU、Cloud CPU、Serverless、Storage 显示每日花费" loading="lazy" width="1400" height="998"></a><figcaption>Billing → Billing explorer：按产品显示每日花费，按 UTC 计，且 "1 hour behind"——刚删除的 Pod 还不会出现。下方 2026-11-05 是做 Pod 实验的那天。</figcaption></figure>

<div class="danger" markdown="1">
这是与 Serverless 最大的区别，也是最容易意外产生高额账单的地方。请设置支出上限，并养成实验一结束就立即 terminate 的习惯。
</div>

### 参考资料

Pod 不需要代码仓库——你可以从控制台、CLI 或 SDK 启动——所以与 Serverless 路线不同，这里没有需要 fork 的 template 仓库。

[Pods overview](https://docs.runpod.io/pods/overview) ·
[Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) ·
[Connect](https://docs.runpod.io/pods/connect-to-a-pod) ·
[Storage types](https://docs.runpod.io/pods/storage/types) ·
[Network volumes](https://docs.runpod.io/pods/storage/create-network-volumes) ·
[Templates](https://docs.runpod.io/pods/templates/overview) ·
[Pricing](https://docs.runpod.io/pods/pricing) ·
[runpod/containers](https://github.com/runpod/containers/tree/main/official-templates)

注意 `runpod/containers` 是与 Serverless 路线共用的基础——`runpod/base` 既是 Pod template 的基础，也是 Serverless `worker-template` 构建所基于的镜像。

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

<div class="note" markdown="1">
**Lab 01 はエンドツーエンドで動作します**。Python から起動し、SSH で接続し、削除します。デフォルトは CPU です。2026-11-05 に `runpod` 1.12.0 で実行：`cpu3c-2-4` の CPU Pod で $0.06/hr、起動から約 4 分で SSH 接続可能になり、合計 1 セント未満でした。[ラボを見る](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect)。
</div>

Pod は借りて自分で制御する GPU または CPU コンテナです。Serverless と違い、停止するまで動き続け、ファイルシステムを保持し、シェルアクセスができます。開発、実験、ファインチューニングはここで行います。

### ラボ

| ラボ | 状態 |
|---|---|
| [01-launch-connect](https://github.com/litkhai/runpod-hols/tree/main/pod/01-launch-connect) | ✅ 2026-11-05 実行。Python から起動、SSH で接続、削除。デフォルトは CPU |
| [02-storage](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage) | ✅ 2026-11-05 実行。stop、terminate、CPU Pod の後に何が残るか |
| [03-custom-template](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template) | ✅ 2026-11-05 実行。通常の環境変数と secret の環境変数を持つ template |
| [04-pod-to-serverless](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless) | ✅ 2026-11-05 実行。Pod で開発し、network volume 経由で同じファイルを Serverless から提供 |

### ストレージ：最も重要な概念

3 つの階層があり、これを混同すると作業が失われます。

| 種類 | 寿命 | マウント | 用途 |
|---|---|---|---|
| Container Disk | stop または terminate で破棄 | `/` | OS、一時ファイル |
| Volume Disk | stop では残り、terminate で消える | `/workspace` | 作業中のコード、データセット |
| Network Volume | どの Pod からも独立、共有可能 | 設定可能 | 複数の Pod で使い回す重み |

<figure class="shot"><a href="{{ '/assets/img/pod/create-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-storage.webp' | relative_url }}" alt="Create storage ダイアログ：Network volume、Global volume（ベータ）、Volume disk（レガシー）と価格" loading="lazy" width="1400" height="998"></a><figcaption>Pod デプロイ画面の Create storage、2026-11-07：Network volume は 1 データセンターで GB・月 USD 0.07、Global volume（ベータ）はデータセンター横断で GB・月 USD 0.09 + IOPS、Volume disk（レガシー、つまり Pod ボリューム）は実行中 GB・月 USD 0.10、停止中 0.20。</figcaption></figure>

残しておきたいものは `/workspace` か Network Volume に置いてください。作業を container disk に残してはいけません。

<div class="warn" markdown="1">
**CPU Pod は例外です。** SDK 1.12 から `volume_in_gb=10` で起動した CPU Pod は `volumeInGb` 0 で立ち上がりました。SDK は CPU Pod に対してこのフィールドを送信しません。そして `/workspace` は `/` と同じ 10 GB の overlay 上にありました。この場合、`/workspace` は container disk です。REST API で `volumeInGb: 10` を指定しても同じでした（Lab 02）。network volume は CPU Pod にもアタッチされます。
</div>

### Lab 02 で測定したこと

2026-11-05 に EU-RO-1 で、各階層にマーカーファイルを置いて実行しました（[ラボ](https://github.com/litkhai/runpod-hols/tree/main/pod/02-storage)）。

| 操作 | Container disk `/` | Pod volume `/workspace` | Network volume `/workspace` |
|---|---|---|---|
| stop してから start | 消去 | 保持 | — |
| terminate し、同じ volume で新しい Pod | — | — | 保持、別のホスト上で |
| CPU Pod | 存在 | 作成されない | マウントされて動作 |

<div class="warn" markdown="1">
**停止した Pod はすぐには再起動できないことがあります。** stop の 40 秒後に実行した最初の `start` は *"There are not enough free GPUs on the host machine to start this pod."* を返しました。Pod は自分のマシンに紐づいたままです。同じ呼び出しは 8 分後に成功しました。それまで Pod volume のデータには手が届きません。network volume はマシンに紐づいていません。
</div>

停止中、10 GB の Pod volume に対してアカウントの `currentSpendPerHr` は `0.003` でしたが、Pod の `costPerHr` は稼働時の料金 `0.89` のままでした。EU-RO-1 ではどちらの volume も FUSE マウント `mfs#euro.runpod.net:9421` でした。`df` は 2.3 PB のファイルシステム全体を表示し、書き込みは 10 GB の割り当てで `Disk quota exceeded` となって止まりました。

### Global volume（ベータ）：測定したこと

3 つ目の永続ストレージで、**Add volume** の一覧の先頭に **Global** バッジ付きで表示されます。データセンターも容量もなく、保存 GB・月あたり USD 0.09 に IOPS 料金が加わります。`POST https://api.runpod.io/v2/global-volumes`（名前のみ）かコンソールで作成できますが、REST v1 では Pod にアタッチできません。コンソールのデプロイ mutation は `volumeMounts: [{volumeId, volumeType: "OBJECT_STORE_VOLUME", mountPath: "/workspace"}]` を送っています。Pod の中ではオブジェクトストアの FUSE マウントです。

| 2026-11-07 | Pod A、CA-MTL-1（RTX A5000） | Pod B、EU-RO-1（RTX 4090） |
|---|---|---|
| `/workspace` | `fuse.geesefs`、1.0P | 同じボリューム |
| 512 MiB 書き込み | **61 MiB/s**（コンテナディスク 273） | |
| そのファイルの初回読み込み | 344 MiB/s | リージョン間 **39 MiB/s** |
| 再読み込み | 275 MiB/s | 985 MiB/s（ローカルキャッシュ） |
| 小さなファイル 200 個 | 338 ms | 59 ms |

これらの数値は `/dev/urandom` を使った `dd` によるもので、urandom 自体が 300 MB/s 付近で頭打ちになります。同じ fio の方法ですべての層を測り直した結果は [Storage]({{ '/readings/storage/#benchmark-ja' | relative_url }}) にあります。

<figure class="shot"><a href="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}"><img src="{{ '/assets/img/pod/global-volume-storage.webp' | relative_url }}" alt="537MB、205 オブジェクト、場所 Any と表示された global volume の Storage 画面" loading="lazy" width="1400" height="998"></a><figcaption>Storage、2026-11-07：テスト用ボリューム——場所 <strong>Any</strong>、205 オブジェクトで 537 MB、月 USD 0.05。</figcaption></figure>

- **1 つのボリュームを 2 つの大陸で。** カナダで書いたマーカーと 512 MiB のファイルを、ルーマニアで同じ sha256 のまま読めました。ルーマニアで書いた新しいファイルは **3 秒** 後にカナダで見えました。
- **同時書き込みは分岐します。** 2 つの Pod が同じ瞬間に同じファイルを書くと、それぞれが自分のバージョンを読み続け、45 秒後もそのままでした。ドキュメントは最後の書き込みが勝つとし、共有する可変データには network volume を勧めていますが、ここではどちらも相手の書き込みを見ませんでした。
- **課金はオブジェクト単位です。** Storage 画面ではこのテストが 537 MB、205 オブジェクト、月 USD 0.05 と表示されました。
- Pod B は同じ GraphQL mutation に `dataCenterId: "EU-RO-1"` を加えてデプロイしました。最初に選んだ RTX A5000 はそこに空きがありませんでした。

複数のリージョンが読む、読み取り中心のデータ（重み、設定、データセット）に使い、チェックポイントや複数のワーカーが書くデータは network volume かコンテナディスクに置いてください。

### Template と secret：Lab 03 でわかったこと

template の `env` には {% raw %}`{{ RUNPOD_SECRET_<name> }}`{% endraw %} を書くことができ、起動時に secret の値に置き換えられます。2026-11-05 にランダムなデモ用 secret で実行しました（[ラボ](https://github.com/litkhai/runpod-hols/tree/main/pod/03-custom-template)）。

<figure class="shot"><a href="{{ '/assets/img/pod/create-secret.webp' | relative_url }}"><img src="{{ '/assets/img/pod/create-secret.webp' | relative_url }}" alt="RUNPOD_SECRET 参照の例が載った Create secret フォーム" loading="lazy" width="1400" height="998"></a><figcaption>Create secret（Credentials → Secrets）：フォーム自体が上のルールを書いています。シークレットは、それを参照する環境変数を通してのみ Pod やエンドポイントに届きます。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}"><img src="{{ '/assets/img/pod/template-secret-ref.webp' | relative_url }}" alt="存在しないシークレットへの参照を拒否する Create template フォーム" loading="lazy" width="1400" height="998"></a><figcaption>コンソールの Create template は参照を検査します。<code>RUNPOD_SECRET_hf_token</code> は存在しないので欄に "Secret not found" と出て、テンプレートは作成できません。フォームは保存せずに破棄しました。</figcaption></figure>

| 場所 | 中身 |
|---|---|
| `GET /templates`、`GET /pods` | 参照のみで、値は決して含まれない |
| PID 1 の環境 | 値（ハッシュが一致） |
| `ssh host 'command'` | どちらの変数もなし。`/etc/rp_environment` を source するのは対話シェルだけ |
| secret をローテーションした後 | Pod を stop して start するまで古い値のまま。`restart` は 500 を返し何もしなかった |

<div class="warn" markdown="1">
**Pod の中では secret はただのファイルです。** `/etc/rp_environment`（モード 644）に、解決済みの secret と Pod の `RUNPOD_API_KEY` が入っていました。secret は値を template や API から隠しますが、コンテナからは隠しません。
</div>

### Pod から Serverless へ：Lab 04 でわかったこと

1 つの network volume を Pod では `/workspace` に、Serverless の worker では `/runpod-volume` にマウントすると、Pod でテストしたばかりのファイルを endpoint で実行できます。イメージのビルドは不要です。template で `dockerStartCmd: ["python3", "-u", "/runpod-volume/app/handler.py"]` を設定し、`PYTHONPATH` を volume にインストールしたパッケージに向けます。2026-11-05 に EU-RO-1 の RTX 4090 で実行しました（[ラボ](https://github.com/litkhai/runpod-hols/tree/main/pod/04-pod-to-serverless)）。

| ステップ | 結果 |
|---|---|
| `pip install --target` で volume にインストール | 9,237 ファイルで約 10 分 |
| 最初の job | worker が `loaded_from: /runpod-volume/app/handler.py` を報告。`delayTime` 205 s |
| そのコールドスタートでの `runsync` | 90.9 s 後に `IN_QUEUE` を返した。`/status/{id}` をポーリングすること |
| 2 つ目の job、worker はすでに消えている | `delayTime` 47 s |

反復開発には向いています。本番では Serverless Lab 01 のようにコードをイメージに焼き込んでください。volume は endpoint を 1 つのデータセンターに固定し、コールドスタートのたびにネットワーク越しの import を発生させます。

### SDK で変わったこと

| | `runpod` 1.12.0 | `runpod` 2.0.0+（2026-10-30） |
|---|---|---|
| Pod の呼び出し | GraphQL | REST API v2 |
| instance id なしの CPU Pod | 送信される。API が拒否：`instanceId` は必須 | SDK で拒否 |
| `volume_mount_path` ありで network volume なしの CPU Pod | 送信される。volume は落とされる | SDK で拒否 |

Lab 01 は `runpod~=1.12.0` に固定しています。2.x ではスクリプトが Pod を読み違えることもあります。REST のオブジェクトは `desiredStatus` ではなく `status` なので、稼働中の Pod のチェックが何も見つけられません。[2.x でのその他の変更]({{ '/sdk/client/' | relative_url }})。instance id は `cpu3c-2-4` のような形式で、フレーバー、vCPU、GB 単位のメモリを表します。

### 課金

Pod が稼働している間は、アイドルかどうかに関係なく分単位で課金されます。stop すると GPU は解放されますが、volume のストレージは引き続き課金されます。terminate するとすべて削除されます。

<figure class="shot"><a href="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}"><img src="{{ '/assets/img/pod/billing-explorer.webp' | relative_url }}" alt="Cloud GPU、Cloud CPU、Serverless、Storage 別の日次支出を示す Billing explorer" loading="lazy" width="1400" height="998"></a><figcaption>Billing → Billing explorer：製品別の日次支出、UTC 基準、"1 hour behind"。削除した直後の Pod はまだ出ません。下の 2026-11-05 は Pod のラボを行った日です。</figcaption></figure>

<div class="danger" markdown="1">
これが Serverless との最大の違いであり、うっかり請求額を膨らませる最も簡単な原因です。支出上限を設定し、ラボが終わったらすぐに terminate する習慣をつけてください。
</div>

### 参考資料

Pod にはコードリポジトリが不要です。コンソール、CLI、SDK から起動できます。そのため Serverless トラックと違い、fork する template リポジトリはありません。

[Pods overview](https://docs.runpod.io/pods/overview) ·
[Choose a Pod](https://docs.runpod.io/pods/choose-a-pod) ·
[Connect](https://docs.runpod.io/pods/connect-to-a-pod) ·
[Storage types](https://docs.runpod.io/pods/storage/types) ·
[Network volumes](https://docs.runpod.io/pods/storage/create-network-volumes) ·
[Templates](https://docs.runpod.io/pods/templates/overview) ·
[Pricing](https://docs.runpod.io/pods/pricing) ·
[runpod/containers](https://github.com/runpod/containers/tree/main/official-templates)

なお `runpod/containers` は Serverless トラックと共通の土台です。`runpod/base` は Pod template のベースであると同時に、Serverless の `worker-template` がビルドの基にしているイメージでもあります。

</div>
