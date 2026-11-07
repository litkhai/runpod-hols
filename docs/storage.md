---
layout: default
title: Storage
permalink: /readings/storage/
description: Every Runpod storage tier through one benchmark, two writers on one volume, and where model weights should live — measured.
---

# Storage

<div class="lang" data-lang="en" markdown="1">

## English

Every Runpod product sits on the same handful of storage tiers, and they are not what their names suggest: the "Pod volume" is a network filesystem, the "high-performance" volume is a different storage system in a different datacenter, and the global volume is an object store behind FUSE. This note puts all of them through one benchmark, checks what happens when two writers share a volume, and measures where model weights should live for a Serverless cold start.

Everything here was run on 2026-11-07 ([#64](https://github.com/litkhai/runpod-hols/issues/64), [#69](https://github.com/litkhai/runpod-hols/issues/69)). Scripts and raw results are in [`storage/`](https://github.com/litkhai/runpod-hols/tree/main/storage).

## The tiers
{: #tiers }

| Tier | What it actually is (2026-11-07) | Lives | Price | Attach |
|---|---|---|---|---|
| Container disk | `overlay` on the host's local NVMe | Until the Pod stops | In the Pod price | Always there |
| Pod volume ("Volume disk", legacy) | MooseFS over FUSE (`mfs#euro-3.runpod.net`) in EU-RO-1 | Until the Pod is deleted | USD 0.10/GB-month running, 0.20 stopped | `volumeInGb` |
| Network volume, standard | The same MooseFS | Until you delete it | USD 0.07/GB-month (0.05 beyond 1 TB) | `networkVolumeId`, one datacenter |
| Network volume, high-performance | A VAST NFS server (`us-ca-2-vast.runpod.net:/runpodfs`) | Until you delete it | USD 0.14/GB-month | GraphQL only (`isNextGenStorage: true`) |
| Global volume (beta) | An object store over FUSE (`fuse.geesefs`, 1.0P) | Until you delete it | USD 0.09/GB-month + IOPS | GraphQL only (`volumeMounts`, `OBJECT_STORE_VOLUME`) |

<figure class="shot"><a href="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}"><img src="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}" alt="Create new volume page with the High-performance filter: AP-IN-1, AP-IN-2, CA-MTL-1, CA-MTL-4, EU-FR-1, EUR-NO-2, US-CA-2" loading="lazy" width="1400" height="998"></a><figcaption>Create new volume, High-performance filter: seven datacenters, only US-CA-2 also S3-compatible. Picking one switches the volume to high-performance at USD 0.14/GB-month — twice standard. The filter's tooltip promises "up to 2x faster"; the docs say "up to 3x throughput and 4x IOPS".</figcaption></figure>

Three API surfaces are involved, and none covers everything. REST v1 creates standard network volumes and attaches them to Pods; GraphQL (what the console uses) is the only way to create a high-performance volume or attach a global volume; global volumes themselves are created through `POST https://api.runpod.io/v2/global-volumes`.

<div class="warn" markdown="1">
**Passing both kinds to one GraphQL deploy drops the network volume.** `podFindAndDeployOnDemand` with `networkVolumeId` *and* a global volume in `volumeMounts` started a Pod with only the global volume; `/workspace` was the container disk, and nothing reported an error. Check `df -T /workspace` after every deploy.
</div>

## One benchmark for every tier
{: #benchmark }

`storage/bench.sh` runs the same fio jobs on each mount: 2 GiB sequential write and read with 1 MiB blocks, 30 s of 4 KiB random read and write at queue depth 16 (direct I/O wherever the filesystem accepts it), and 1,000 4 KiB files created and synced.

| Tier | Client | Seq write | Seq read | 4K rand read | 4K rand write | Small files |
|---|---|---|---|---|---|---|
| Container disk | GPU Pod, EU-RO-1 | 4.3–4.5 GB/s | 4.6 GB/s | ~190–204k IOPS | ~165–188k IOPS | ~1,250/s |
| Pod volume | GPU Pod, EU-RO-1 | 1.6 GB/s | 1.2 GB/s | 9.9k IOPS | 51k IOPS | 67/s |
| Network volume, standard | GPU and CPU Pods, EU-RO-1 | 2.0–2.3 GB/s | 1.45–1.5 GB/s | 7.5–8.1k IOPS | 48k IOPS | 66–74/s |
| Network volume, high-performance | CPU Pod, US-CA-2 | 0.18 GB/s | 0.65 GB/s | 16k IOPS | 5.1k IOPS | 113/s |
| Global volume | GPU Pod, EU-RO-1 | 0.19 GB/s | (cache, see below) | 64k IOPS | 17k IOPS | 1,100/s |

What the table says:

- **The local disk wins everything, by an order of magnitude on random reads.** ~190k IOPS against under 10k on the network volume. Anything that reads small pieces at random — a dataloader over many files, a database — belongs on the container disk.
- **The Pod volume and the standard network volume are the same system.** Same MooseFS cluster, same profile; the Pod volume is not a local disk in EU-RO-1.
- **"High-performance" was not faster in a straight line.** In US-CA-2 it doubled random reads (16k vs 8k IOPS) and was 1.6× faster on small files, but wrote sequentially at a tenth of the standard volume's speed. Datacenter and storage system change together, so this is not a pure tier comparison — but it is what you get for twice the price there.
- **The global volume caches aggressively.** Reading the 2 GiB right after writing it ran at 6.6 GB/s from local cache; a cold read of a 512 MiB file from another continent ran at 39 MiB/s ([#64](https://github.com/litkhai/runpod-hols/issues/64)).
- **CPU Pods have slow container disks.** On a `cpu3c` Pod the container disk wrote at 0.23 GB/s and read at 0.13 GB/s — slower than the network volume it was attached to.

<div class="note" markdown="1">
**This replaces the mixed numbers from earlier labs.** Pod lab 02 used `dd oflag=direct` (1.6 GB/s), and the first global-volume test wrote from `/dev/urandom`, which caps near 300 MB/s on its own — so its "273 MB/s container disk" was the random generator, not the disk.
</div>

## Two writers, one volume
{: #sharing }

| | Standard network volume (EU-RO-1) | Global volume (CA-MTL-1 + EU-RO-1) |
|---|---|---|
| New file written on one side seen on the other | < 4 s | 3 s |
| Both write one file at the same moment | Both read the same final content | **Each keeps its own version**, still 45 s later |
| 200 appends from each side | All 400 lines present | Not tested |

The network volume behaves like one shared filesystem. The global volume does not: concurrent writers diverge, and nothing reports a conflict. Runpod's docs say the last write wins and recommend network volumes for shared mutable data; the measurement agrees with the recommendation, not with "last write wins". The docs also warn that writing to one network volume from several Serverless workers at once "may cause data corruption" — appends survived here, but treat it as one writer at a time.

## Where model weights should live
{: #model-weights }

Same vLLM worker (`worker-v1-vllm` v2.28.0, Qwen2.5-7B-Instruct, 14.29 GiB), RTX 4090, FlashBoot off read back, cold starts 180 s apart:

| Weights | Cold start `delayTime` | What happened to the weights |
|---|---|---|
| Downloaded every time | 96.8–123.4 s | Download 12.1–28.4 s, then load in seconds |
| Endpoint **Model** field (host cache) | **85.7–129.9 s** | No download; shards from the host in 5–46 s |
| Network volume (`/runpod-volume`) | 137.9–195.2 s | No download after the first; load 27.8–31.1 s at ~0.5 GB/s |

The network volume saved the download and then spent as long reading from MooseFS, and the cold starts came out slower overall. For a model of this size, set the endpoint's Model field ([Serverless]({{ '/serverless/' | relative_url }})) and leave the network volume for data that must persist and be shared — outputs, checkpoints, datasets that several Pods read. The global volume was not tried for weights: its measured cold read across regions (39 MiB/s) rules it out.

## Getting data in without a Pod — the S3 API
{: #s3 }

Network volumes in S3-capable datacenters (EU-RO-1 here) also answer at `https://s3api-<dc>.runpod.io`, with the volume id as the bucket. It needs an S3 API key from **Credentials → S3 API Keys**, separate from the Runpod API key and with read and write access to every S3-capable volume. Measured on 2026-11-07 with `aws s3 cp`, 1 GiB:

| Client | Upload | Download |
|---|---|---|
| This repo's build server, outside Runpod | 20 MiB/s | 66 MiB/s |
| A CPU Pod in the same datacenter | 30 MiB/s | 210 MiB/s |
| The same file through the Pod's mount | | 1.27 GB/s |

- **The two views are one filesystem.** A file uploaded through S3 appeared on the Pod's `/workspace` with the same sha256, and a file written in the Pod was listed by S3 straight away.
- **Uploads are slow from anywhere.** 20–30 MiB/s is about 35–50 s per GiB; 100 small files went at 20 per second. Fine for configs and adapters, slow for a 15 GB model — compare the Model field.
- **Uploaded files are `root`, mode 600** (directories 750). A container that runs as another user cannot read them until you `chmod`.
- The key is shown once and grants every S3-capable volume; delete it when done. This test's key was revoked afterwards.

## Choosing
{: #choosing }

| You need | Use |
|---|---|
| Scratch space, datasets read at random, compilation caches | Container disk |
| Model weights for a Serverless endpoint | The endpoint's Model field |
| Files that outlive the Pod in one datacenter, shared by Pods and endpoints there | Standard network volume |
| Random-read heavy work in a high-performance datacenter | High-performance volume — measure first; sequential writes were slow |
| Read-mostly files that several regions need | Global volume — one writer, expect seconds of delay |
| Data that must survive Pod deletion but needs no sharing | Pod volume is the same system as a network volume, at a higher price |

Not covered yet: Instant Cluster volumes.

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

Runpod 의 모든 제품은 같은 몇 가지 스토리지 계층 위에 놓여 있고, 그 실체는 이름과 다릅니다. "Pod 볼륨"은 네트워크 파일시스템이고, "고성능" 볼륨은 다른 데이터센터에 있는 다른 스토리지 시스템이며, 글로벌 볼륨은 FUSE 뒤에 있는 오브젝트 스토어입니다. 이 노트는 모든 계층을 하나의 벤치마크로 측정하고, 두 작성자가 한 볼륨을 공유할 때 어떤 일이 생기는지 확인하며, Serverless 콜드 스타트를 위해 모델 가중치를 어디에 둬야 하는지 측정합니다.

모든 항목은 2026-11-07 에 실행했습니다([#64](https://github.com/litkhai/runpod-hols/issues/64), [#69](https://github.com/litkhai/runpod-hols/issues/69)). 스크립트와 원시 결과는 [`storage/`](https://github.com/litkhai/runpod-hols/tree/main/storage) 에 있습니다.

## 스토리지 계층
{: #tiers-ko }

| 계층 | 실제 정체 (2026-11-07) | 수명 | 가격 | 연결 방식 |
|---|---|---|---|---|
| 컨테이너 디스크 | 호스트 로컬 NVMe 위의 `overlay` | Pod 가 중지될 때까지 | Pod 가격에 포함 | 항상 존재 |
| Pod 볼륨 ("Volume disk", 레거시) | EU-RO-1 의 FUSE 기반 MooseFS (`mfs#euro-3.runpod.net`) | Pod 가 삭제될 때까지 | 실행 중 USD 0.10/GB-월, 중지 시 0.20 | `volumeInGb` |
| 네트워크 볼륨, 표준 | 같은 MooseFS | 직접 삭제할 때까지 | USD 0.07/GB-월 (1 TB 초과분 0.05) | `networkVolumeId`, 데이터센터 하나 |
| 네트워크 볼륨, 고성능 | VAST NFS 서버 (`us-ca-2-vast.runpod.net:/runpodfs`) | 직접 삭제할 때까지 | USD 0.14/GB-월 | GraphQL 전용 (`isNextGenStorage: true`) |
| 글로벌 볼륨 (베타) | FUSE 기반 오브젝트 스토어 (`fuse.geesefs`, 1.0P) | 직접 삭제할 때까지 | USD 0.09/GB-월 + IOPS | GraphQL 전용 (`volumeMounts`, `OBJECT_STORE_VOLUME`) |

<figure class="shot"><a href="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}"><img src="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}" alt="High-performance 필터를 적용한 볼륨 생성 페이지: AP-IN-1, AP-IN-2, CA-MTL-1, CA-MTL-4, EU-FR-1, EUR-NO-2, US-CA-2" loading="lazy" width="1400" height="998"></a><figcaption>볼륨 생성, High-performance 필터: 데이터센터 일곱 곳이며, S3 호환까지 되는 곳은 US-CA-2 뿐입니다. 이 중 하나를 고르면 볼륨이 USD 0.14/GB-월의 고성능으로 바뀝니다 — 표준의 두 배입니다. 필터의 툴팁은 "최대 2배 빠름"을, 문서는 "최대 3배 처리량, 4배 IOPS"를 약속합니다.</figcaption></figure>

관련된 API 는 세 가지이고, 어느 것도 전부를 다루지 못합니다. REST v1 은 표준 네트워크 볼륨을 만들고 Pod 에 연결합니다. GraphQL(콘솔이 쓰는 API)은 고성능 볼륨을 만들거나 글로벌 볼륨을 연결하는 유일한 방법입니다. 글로벌 볼륨 자체는 `POST https://api.runpod.io/v2/global-volumes` 로 생성합니다.

<div class="warn" markdown="1">
**두 종류를 한 번의 GraphQL 배포에 함께 넘기면 네트워크 볼륨이 빠집니다.** `networkVolumeId` *와* `volumeMounts` 의 글로벌 볼륨을 함께 넘긴 `podFindAndDeployOnDemand` 는 글로벌 볼륨만 붙은 Pod 를 띄웠습니다. `/workspace` 는 컨테이너 디스크였고, 어떤 오류도 보고되지 않았습니다. 배포할 때마다 `df -T /workspace` 로 확인하세요.
</div>

## 모든 계층에 같은 벤치마크
{: #benchmark-ko }

`storage/bench.sh` 는 각 마운트에서 같은 fio 작업을 실행합니다. 1 MiB 블록으로 2 GiB 순차 쓰기와 읽기, 큐 깊이 16 의 4 KiB 랜덤 읽기와 쓰기 30 s(파일시스템이 허용하는 곳에서는 direct I/O), 그리고 4 KiB 파일 1,000 개 생성 후 sync 입니다.

| 계층 | 클라이언트 | 순차 쓰기 | 순차 읽기 | 4K 랜덤 읽기 | 4K 랜덤 쓰기 | 작은 파일 |
|---|---|---|---|---|---|---|
| 컨테이너 디스크 | GPU Pod, EU-RO-1 | 4.3–4.5 GB/s | 4.6 GB/s | ~190–204k IOPS | ~165–188k IOPS | ~1,250/s |
| Pod 볼륨 | GPU Pod, EU-RO-1 | 1.6 GB/s | 1.2 GB/s | 9.9k IOPS | 51k IOPS | 67/s |
| 네트워크 볼륨, 표준 | GPU 및 CPU Pod, EU-RO-1 | 2.0–2.3 GB/s | 1.45–1.5 GB/s | 7.5–8.1k IOPS | 48k IOPS | 66–74/s |
| 네트워크 볼륨, 고성능 | CPU Pod, US-CA-2 | 0.18 GB/s | 0.65 GB/s | 16k IOPS | 5.1k IOPS | 113/s |
| 글로벌 볼륨 | GPU Pod, EU-RO-1 | 0.19 GB/s | (캐시, 아래 참조) | 64k IOPS | 17k IOPS | 1,100/s |

표가 말해주는 것:

- **로컬 디스크가 모든 항목에서 이기며, 랜덤 읽기에서는 한 자릿수 차이로 앞섭니다.** 약 190k IOPS 대 네트워크 볼륨의 10k 미만입니다. 작은 조각을 무작위로 읽는 작업 — 많은 파일을 읽는 데이터로더, 데이터베이스 — 은 컨테이너 디스크에 두어야 합니다.
- **Pod 볼륨과 표준 네트워크 볼륨은 같은 시스템입니다.** 같은 MooseFS 클러스터, 같은 성능 특성이며, EU-RO-1 의 Pod 볼륨은 로컬 디스크가 아닙니다.
- **"고성능"이 일관되게 빠르지는 않았습니다.** US-CA-2 에서 랜덤 읽기는 두 배(16k 대 8k IOPS), 작은 파일은 1.6배 빨랐지만, 순차 쓰기는 표준 볼륨 속도의 10분의 1 이었습니다. 데이터센터와 스토리지 시스템이 함께 바뀌므로 순수한 계층 비교는 아니지만, 그곳에서 두 배 가격으로 얻는 것은 이것입니다.
- **글로벌 볼륨은 공격적으로 캐시합니다.** 2 GiB 를 쓴 직후 읽으면 로컬 캐시에서 6.6 GB/s 가 나왔고, 다른 대륙에서 512 MiB 파일을 콜드 리드하면 39 MiB/s 였습니다([#64](https://github.com/litkhai/runpod-hols/issues/64)).
- **CPU Pod 는 컨테이너 디스크가 느립니다.** `cpu3c` Pod 에서 컨테이너 디스크는 쓰기 0.23 GB/s, 읽기 0.13 GB/s 로, 연결된 네트워크 볼륨보다 느렸습니다.

<div class="note" markdown="1">
**이전 실습의 뒤섞인 수치를 이것으로 대체합니다.** Pod 실습 02 는 `dd oflag=direct`(1.6 GB/s)를 썼고, 첫 글로벌 볼륨 테스트는 `/dev/urandom` 에서 읽어 썼는데 이것만으로 약 300 MB/s 에서 막힙니다 — 그래서 "컨테이너 디스크 273 MB/s"는 디스크가 아니라 난수 생성기의 속도였습니다.
</div>

## 두 작성자, 하나의 볼륨
{: #sharing-ko }

| | 표준 네트워크 볼륨 (EU-RO-1) | 글로벌 볼륨 (CA-MTL-1 + EU-RO-1) |
|---|---|---|
| 한쪽에서 쓴 새 파일이 다른 쪽에 보이기까지 | < 4 s | 3 s |
| 양쪽이 같은 순간 한 파일에 쓰기 | 양쪽 모두 같은 최종 내용을 읽음 | **각자 자기 버전을 유지**, 45 s 후에도 |
| 양쪽에서 각각 200 회 append | 400 줄 모두 존재 | 미검증 |

네트워크 볼륨은 하나의 공유 파일시스템처럼 동작합니다. 글로벌 볼륨은 그렇지 않습니다. 동시에 쓰면 내용이 갈라지고, 충돌을 알려주는 것도 없습니다. Runpod 문서는 마지막 쓰기가 이긴다고 하며 공유되는 가변 데이터에는 네트워크 볼륨을 권장합니다. 측정 결과는 "마지막 쓰기가 이긴다"가 아니라 그 권장 사항과 일치합니다. 문서는 또한 여러 Serverless 워커가 한 네트워크 볼륨에 동시에 쓰면 "데이터 손상이 생길 수 있다"고 경고합니다 — 여기서는 append 가 살아남았지만, 한 번에 한 작성자만 쓰는 것으로 취급하세요.

## 모델 가중치는 어디에 둘까
{: #model-weights-ko }

같은 vLLM 워커(`worker-v1-vllm` v2.28.0, Qwen2.5-7B-Instruct, 14.29 GiB), RTX 4090, FlashBoot 꺼짐을 다시 읽어 확인, 콜드 스타트 간격 180 s:

| 가중치 위치 | 콜드 스타트 `delayTime` | 가중치에 일어난 일 |
|---|---|---|
| 매번 다운로드 | 96.8–123.4 s | 다운로드 12.1–28.4 s, 이후 수 초 만에 로드 |
| 엔드포인트 **Model** 필드 (호스트 캐시) | **85.7–129.9 s** | 다운로드 없음, 호스트에서 샤드 로드 5–46 s |
| 네트워크 볼륨 (`/runpod-volume`) | 137.9–195.2 s | 첫 회 이후 다운로드 없음, ~0.5 GB/s 로 27.8–31.1 s 로드 |

네트워크 볼륨은 다운로드를 아꼈지만 그만큼을 MooseFS 에서 읽는 데 썼고, 콜드 스타트는 전체적으로 더 느렸습니다. 이 크기의 모델이라면 엔드포인트의 Model 필드를 설정하고([Serverless]({{ '/serverless/' | relative_url }})), 네트워크 볼륨은 유지·공유되어야 하는 데이터 — 출력물, 체크포인트, 여러 Pod 가 읽는 데이터셋 — 에 남겨두세요. 글로벌 볼륨은 가중치용으로 시험하지 않았습니다. 측정된 리전 간 콜드 리드(39 MiB/s)만으로 제외됩니다.

## Pod 없이 데이터 넣기 — S3 API
{: #s3-ko }

S3 를 지원하는 데이터센터(여기서는 EU-RO-1)의 네트워크 볼륨은 `https://s3api-<dc>.runpod.io` 로도 응답하며, 볼륨 id 가 버킷 이름입니다. **Credentials → S3 API Keys** 에서 만드는 S3 API 키가 필요합니다. Runpod API 키와 별개이고, S3 를 지원하는 모든 볼륨에 읽기·쓰기 권한을 가집니다. 2026-11-07 `aws s3 cp` 로 1 GiB 를 잰 결과:

| 클라이언트 | 업로드 | 다운로드 |
|---|---|---|
| 이 저장소의 빌드 서버, Runpod 외부 | 20 MiB/s | 66 MiB/s |
| 같은 데이터센터의 CPU Pod | 30 MiB/s | 210 MiB/s |
| 같은 파일을 Pod 의 마운트로 | | 1.27 GB/s |

- **두 경로는 같은 파일시스템입니다.** S3 로 올린 파일이 Pod 의 `/workspace` 에 같은 sha256 으로 보였고, Pod 에서 쓴 파일은 S3 목록에 곧바로 나왔습니다.
- **업로드는 어디서나 느립니다.** 20–30 MiB/s 는 GiB 당 35–50 초입니다. 작은 파일 100개는 초당 20개였습니다. 설정 파일이나 어댑터에는 괜찮지만 15 GB 모델에는 느립니다 — Model 칸과 비교하세요.
- **올린 파일은 `root`, 권한 600 입니다** (디렉터리 750). 다른 사용자로 도는 컨테이너는 `chmod` 하기 전까지 읽지 못합니다.
- 키는 한 번만 보여 주고 S3 를 지원하는 모든 볼륨에 권한이 있으니, 다 쓰면 지우세요. 이 테스트의 키도 끝난 뒤 폐기했습니다.

## 선택 가이드
{: #choosing-ko }

| 필요한 것 | 사용할 것 |
|---|---|
| 스크래치 공간, 무작위로 읽는 데이터셋, 컴파일 캐시 | 컨테이너 디스크 |
| Serverless 엔드포인트의 모델 가중치 | 엔드포인트의 Model 필드 |
| 한 데이터센터에서 Pod 보다 오래 남고, 그곳의 Pod 와 엔드포인트가 공유하는 파일 | 표준 네트워크 볼륨 |
| 고성능 데이터센터에서 랜덤 읽기가 많은 작업 | 고성능 볼륨 — 먼저 측정하세요. 순차 쓰기가 느렸습니다 |
| 여러 리전이 필요로 하는, 주로 읽기만 하는 파일 | 글로벌 볼륨 — 작성자는 하나, 수 초의 지연을 예상하세요 |
| Pod 삭제 후에도 남아야 하지만 공유는 필요 없는 데이터 | Pod 볼륨은 네트워크 볼륨과 같은 시스템이며, 가격만 더 높습니다 |

아직 다루지 않은 것: Instant Cluster 볼륨.

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

Runpod 的每个产品都建立在同样几种存储层级之上，而它们并不像名字所暗示的那样：“Pod volume”其实是网络文件系统，“high-performance” volume 是另一个数据中心里的另一套存储系统，而 global volume 是挂在 FUSE 后面的对象存储。本文用同一套基准测试把它们逐一跑过，检查两个写入方共享一个 volume 时会发生什么，并测量 Serverless 冷启动时模型权重应该放在哪里。

本文所有内容均于 2026-11-07 实测（[#64](https://github.com/litkhai/runpod-hols/issues/64)、[#69](https://github.com/litkhai/runpod-hols/issues/69)）。脚本和原始结果见 [`storage/`](https://github.com/litkhai/runpod-hols/tree/main/storage)。

## 存储层级
{: #tiers-zh }

| 层级 | 实际是什么（2026-11-07） | 生命周期 | 价格 | 挂载方式 |
|---|---|---|---|---|
| 容器盘 | 主机本地 NVMe 上的 `overlay` | 直到 Pod 停止 | 含在 Pod 价格中 | 始终存在 |
| Pod volume（“Volume disk”，旧版） | EU-RO-1 中经 FUSE 挂载的 MooseFS（`mfs#euro-3.runpod.net`） | 直到 Pod 被删除 | 运行时 USD 0.10/GB-月，停止时 0.20 | `volumeInGb` |
| Network volume，标准 | 同一套 MooseFS | 直到你删除它 | USD 0.07/GB-月（超过 1 TB 部分 0.05） | `networkVolumeId`，限一个数据中心 |
| Network volume，high-performance | 一台 VAST NFS 服务器（`us-ca-2-vast.runpod.net:/runpodfs`） | 直到你删除它 | USD 0.14/GB-月 | 仅 GraphQL（`isNextGenStorage: true`） |
| Global volume（beta） | 经 FUSE 挂载的对象存储（`fuse.geesefs`，1.0P） | 直到你删除它 | USD 0.09/GB-月 + IOPS | 仅 GraphQL（`volumeMounts`、`OBJECT_STORE_VOLUME`） |

<figure class="shot"><a href="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}"><img src="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}" alt="选中 High-performance 筛选条件的 Create new volume 页面：AP-IN-1、AP-IN-2、CA-MTL-1、CA-MTL-4、EU-FR-1、EUR-NO-2、US-CA-2" loading="lazy" width="1400" height="998"></a><figcaption>Create new volume 页面的 High-performance 筛选：七个数据中心，其中只有 US-CA-2 同时兼容 S3。选中其中之一，volume 就会切换为 high-performance，价格为 USD 0.14/GB-月——标准版的两倍。筛选条件的提示框承诺“up to 2x faster”；文档则写着“up to 3x throughput and 4x IOPS”。</figcaption></figure>

这里涉及三套 API，没有一套能覆盖全部。REST v1 可以创建标准 network volume 并把它挂到 Pod 上；GraphQL（控制台使用的接口）是创建 high-performance volume 或挂载 global volume 的唯一途径；global volume 本身则通过 `POST https://api.runpod.io/v2/global-volumes` 创建。

<div class="warn" markdown="1">
**在一次 GraphQL 部署中同时传入两种 volume，network volume 会被丢掉。** 用 `podFindAndDeployOnDemand` 同时传入 `networkVolumeId` *和* `volumeMounts` 中的 global volume，启动的 Pod 只挂上了 global volume；`/workspace` 是容器盘，而且没有任何报错。每次部署后都要用 `df -T /workspace` 检查。
</div>

## 一套基准测试跑遍所有层级
{: #benchmark-zh }

`storage/bench.sh` 在每个挂载点上运行相同的 fio 作业：1 MiB 块的 2 GiB 顺序写和顺序读，队列深度 16 下各 30 s 的 4 KiB 随机读和随机写（只要文件系统支持就使用 direct I/O），以及创建并同步 1,000 个 4 KiB 文件。

| 层级 | 客户端 | 顺序写 | 顺序读 | 4K 随机读 | 4K 随机写 | 小文件 |
|---|---|---|---|---|---|---|
| 容器盘 | GPU Pod，EU-RO-1 | 4.3–4.5 GB/s | 4.6 GB/s | ~190–204k IOPS | ~165–188k IOPS | ~1,250/s |
| Pod volume | GPU Pod，EU-RO-1 | 1.6 GB/s | 1.2 GB/s | 9.9k IOPS | 51k IOPS | 67/s |
| Network volume，标准 | GPU 和 CPU Pod，EU-RO-1 | 2.0–2.3 GB/s | 1.45–1.5 GB/s | 7.5–8.1k IOPS | 48k IOPS | 66–74/s |
| Network volume，high-performance | CPU Pod，US-CA-2 | 0.18 GB/s | 0.65 GB/s | 16k IOPS | 5.1k IOPS | 113/s |
| Global volume | GPU Pod，EU-RO-1 | 0.19 GB/s | （缓存，见下文） | 64k IOPS | 17k IOPS | 1,100/s |

表格说明了什么：

- **本地盘全面领先，随机读更是高出一个数量级。** 约 190k IOPS，而 network volume 不到 10k。凡是随机读取小块数据的负载——遍历大量文件的 dataloader、数据库——都应该放在容器盘上。
- **Pod volume 和标准 network volume 是同一套系统。** 同一个 MooseFS 集群，同样的性能特征；在 EU-RO-1，Pod volume 并不是本地盘。
- **“High-performance”在顺序吞吐上并没有更快。** 在 US-CA-2，它的随机读翻了一倍（16k 对 8k IOPS），小文件快 1.6×，但顺序写只有标准 volume 的十分之一。数据中心和存储系统是同时变化的，所以这并不是纯粹的层级对比——但这就是你在那里花两倍价格得到的东西。
- **Global volume 缓存非常激进。** 写入 2 GiB 后立即读回，从本地缓存读出的速度为 6.6 GB/s；从另一个大洲冷读一个 512 MiB 文件，速度为 39 MiB/s（[#64](https://github.com/litkhai/runpod-hols/issues/64)）。
- **CPU Pod 的容器盘很慢。** 在一台 `cpu3c` Pod 上，容器盘写入 0.23 GB/s、读取 0.13 GB/s——比挂在它上面的 network volume 还慢。

<div class="note" markdown="1">
**本节取代早期实验中口径不一的数字。** Pod lab 02 用的是 `dd oflag=direct`（1.6 GB/s），而第一次 global volume 测试是从 `/dev/urandom` 写入的，它本身就限制在 300 MB/s 左右——所以那次的“273 MB/s 容器盘”测的是随机数生成器，而不是磁盘。
</div>

## 两个写入方，一个 volume
{: #sharing-zh }

| | 标准 network volume（EU-RO-1） | Global volume（CA-MTL-1 + EU-RO-1） |
|---|---|---|
| 一侧新写入的文件在另一侧可见 | < 4 s | 3 s |
| 两侧同时写同一个文件 | 两侧读到相同的最终内容 | **各自保留自己的版本**，45 s 后依然如此 |
| 两侧各追加 200 行 | 400 行全部存在 | 未测试 |

Network volume 表现得像一个共享文件系统。Global volume 则不然：并发写入方的数据会分叉，而且没有任何冲突提示。Runpod 文档称以最后一次写入为准，并建议共享的可变数据使用 network volume；实测结果与这条建议一致，而不是“最后写入为准”。文档还警告，多个 Serverless worker 同时写入同一个 network volume“may cause data corruption”——本次追加测试没有丢数据，但仍应按同一时间只有一个写入方来对待。

## 模型权重应该放在哪里
{: #model-weights-zh }

同一个 vLLM worker（`worker-v1-vllm` v2.28.0，Qwen2.5-7B-Instruct，14.29 GiB），RTX 4090，回读确认 FlashBoot 关闭，每次冷启动间隔 180 s：

| 权重 | 冷启动 `delayTime` | 权重经历了什么 |
|---|---|---|
| 每次都下载 | 96.8–123.4 s | 下载 12.1–28.4 s，随后数秒内加载完成 |
| Endpoint 的 **Model** 字段（主机缓存） | **85.7–129.9 s** | 无需下载；从主机加载分片耗时 5–46 s |
| Network volume（`/runpod-volume`） | 137.9–195.2 s | 首次之后无需下载；以约 0.5 GB/s 加载 27.8–31.1 s |

Network volume 省掉了下载，却又花了同样长的时间从 MooseFS 读取，冷启动总体反而更慢。对于这个规模的模型，请设置 endpoint 的 Model 字段（[Serverless]({{ '/serverless/' | relative_url }})），把 network volume 留给需要持久保存并共享的数据——输出、checkpoint、多个 Pod 共同读取的数据集。Global volume 没有用来测试权重：实测的跨区域冷读速度（39 MiB/s）已经将其排除。

## 不用 Pod 也能放入数据——S3 API
{: #s3-zh }

在支持 S3 的数据中心（这里是 EU-RO-1），network volume 还可以通过 `https://s3api-<dc>.runpod.io` 访问，卷 id 就是 bucket 名。需要在 **Credentials → S3 API Keys** 创建 S3 API 密钥；它独立于 Runpod API 密钥，并对所有支持 S3 的卷拥有读写权限。2026-11-07 用 `aws s3 cp` 测量 1 GiB：

| 客户端 | 上传 | 下载 |
|---|---|---|
| 本仓库的构建服务器，在 Runpod 之外 | 20 MiB/s | 66 MiB/s |
| 同一数据中心的 CPU Pod | 30 MiB/s | 210 MiB/s |
| 同一文件经 Pod 的挂载读取 | | 1.27 GB/s |

- **两种访问方式是同一个文件系统。** 通过 S3 上传的文件出现在 Pod 的 `/workspace` 上，sha256 一致；在 Pod 中写入的文件会立即出现在 S3 列表里。
- **从哪里上传都慢。** 20–30 MiB/s 意味着每 GiB 约 35–50 秒；100 个小文件每秒 20 个。放配置文件和 adapter 没问题，放 15 GB 的模型就慢了——请与 Model 字段比较。
- **上传的文件属于 `root`，权限 600**（目录 750）。以其他用户运行的容器在 `chmod` 之前读不到它们。
- 密钥只显示一次，并对所有支持 S3 的卷有效；用完请删除。本次测试的密钥在测试后已撤销。

## 如何选择
{: #choosing-zh }

| 你需要 | 使用 |
|---|---|
| 临时空间、随机读取的数据集、编译缓存 | 容器盘 |
| Serverless endpoint 的模型权重 | Endpoint 的 Model 字段 |
| 在同一数据中心内比 Pod 活得更久、由那里的 Pod 和 endpoint 共享的文件 | 标准 network volume |
| 在 high-performance 数据中心中以随机读为主的负载 | High-performance volume——先实测；顺序写很慢 |
| 多个区域都需要、以读为主的文件 | Global volume——单一写入方，预期有数秒延迟 |
| 必须在 Pod 删除后保留、但无需共享的数据 | Pod volume 与 network volume 是同一套系统，价格却更高 |

尚未覆盖：Instant Cluster 的卷。

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

Runpod のすべての製品は同じ少数のストレージ階層の上に載っており、それらは名前から想像されるものとは違います。「Pod ボリューム」はネットワークファイルシステムで、「high-performance」ボリュームは別のデータセンターにある別のストレージシステムで、グローバルボリュームは FUSE の背後にあるオブジェクトストアです。このノートでは、すべての階層に同じベンチマークをかけ、2 つの書き込み元が 1 つのボリュームを共有したときに何が起きるかを確かめ、Serverless のコールドスタートに向けてモデルの重みをどこに置くべきかを測定します。

ここでの内容はすべて 2026-11-07 に実行しました（[#64](https://github.com/litkhai/runpod-hols/issues/64)、[#69](https://github.com/litkhai/runpod-hols/issues/69)）。スクリプトと生の結果は [`storage/`](https://github.com/litkhai/runpod-hols/tree/main/storage) にあります。

## ストレージ階層
{: #tiers-ja }

| 階層 | 実際の正体（2026-11-07） | 存続期間 | 料金 | アタッチ方法 |
|---|---|---|---|---|
| コンテナディスク | ホストのローカル NVMe 上の `overlay` | Pod が停止するまで | Pod の料金に含まれる | 常にある |
| Pod ボリューム（「Volume disk」、レガシー） | EU-RO-1 の FUSE 経由の MooseFS（`mfs#euro-3.runpod.net`） | Pod が削除されるまで | 実行中 USD 0.10/GB-月、停止中 0.20 | `volumeInGb` |
| network volume、標準 | 同じ MooseFS | 自分で削除するまで | USD 0.07/GB-月（1 TB 超は 0.05） | `networkVolumeId`、1 つのデータセンター |
| network volume、high-performance | VAST の NFS サーバー（`us-ca-2-vast.runpod.net:/runpodfs`） | 自分で削除するまで | USD 0.14/GB-月 | GraphQL のみ（`isNextGenStorage: true`） |
| グローバルボリューム（ベータ） | FUSE 経由のオブジェクトストア（`fuse.geesefs`、1.0P） | 自分で削除するまで | USD 0.09/GB-月 + IOPS | GraphQL のみ（`volumeMounts`、`OBJECT_STORE_VOLUME`） |

<figure class="shot"><a href="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}"><img src="{{ '/assets/img/storage/create-network-volume-hp.webp' | relative_url }}" alt="High-performance フィルターを選んだ Create new volume ページ：AP-IN-1、AP-IN-2、CA-MTL-1、CA-MTL-4、EU-FR-1、EUR-NO-2、US-CA-2" loading="lazy" width="1400" height="998"></a><figcaption>Create new volume の High-performance フィルター：データセンターは 7 つで、S3 互換も兼ねるのは US-CA-2 だけです。どれかを選ぶとボリュームは USD 0.14/GB-月の high-performance に切り替わり、標準の 2 倍になります。フィルターのツールチップは「up to 2x faster」とうたい、ドキュメントは「up to 3x throughput and 4x IOPS」としています。</figcaption></figure>

関係する API は 3 つあり、どれもすべてをカバーしてはいません。REST v1 は標準の network volume を作成して Pod にアタッチします。GraphQL（コンソールが使うもの）は、high-performance ボリュームを作成したりグローバルボリュームをアタッチしたりする唯一の手段です。グローバルボリューム自体は `POST https://api.runpod.io/v2/global-volumes` で作成します。

<div class="warn" markdown="1">
**1 回の GraphQL デプロイに両方の種類を渡すと、network volume が落とされます。** `podFindAndDeployOnDemand` に `networkVolumeId` *と* `volumeMounts` のグローバルボリュームを渡したところ、Pod はグローバルボリュームだけで起動しました。`/workspace` はコンテナディスクで、エラーは何も報告されませんでした。デプロイのたびに `df -T /workspace` を確認してください。
</div>

## すべての階層に同じベンチマーク
{: #benchmark-ja }

`storage/bench.sh` は各マウントで同じ fio ジョブを実行します。1 MiB ブロックで 2 GiB のシーケンシャル書き込みと読み込み、キュー深度 16 で 4 KiB のランダム読み込みと書き込みを各 30 s（ファイルシステムが受け付ける場合はダイレクト I/O）、そして 4 KiB のファイル 1,000 個の作成と sync です。

| 階層 | クライアント | シーケンシャル書き込み | シーケンシャル読み込み | 4K ランダム読み込み | 4K ランダム書き込み | 小さいファイル |
|---|---|---|---|---|---|---|
| コンテナディスク | GPU Pod、EU-RO-1 | 4.3–4.5 GB/s | 4.6 GB/s | ~190–204k IOPS | ~165–188k IOPS | ~1,250/s |
| Pod ボリューム | GPU Pod、EU-RO-1 | 1.6 GB/s | 1.2 GB/s | 9.9k IOPS | 51k IOPS | 67/s |
| network volume、標準 | GPU Pod と CPU Pod、EU-RO-1 | 2.0–2.3 GB/s | 1.45–1.5 GB/s | 7.5–8.1k IOPS | 48k IOPS | 66–74/s |
| network volume、high-performance | CPU Pod、US-CA-2 | 0.18 GB/s | 0.65 GB/s | 16k IOPS | 5.1k IOPS | 113/s |
| グローバルボリューム | GPU Pod、EU-RO-1 | 0.19 GB/s | （キャッシュ、下記参照） | 64k IOPS | 17k IOPS | 1,100/s |

表からわかること：

- **ローカルディスクがすべてで勝ち、ランダム読み込みでは桁違いです。** ~190k IOPS に対し、network volume は 10k 未満です。小さな断片をランダムに読むもの、たとえば多数のファイルを読むデータローダーやデータベースは、コンテナディスクに置くべきです。
- **Pod ボリュームと標準の network volume は同じシステムです。** 同じ MooseFS クラスタで、プロファイルも同じです。EU-RO-1 の Pod ボリュームはローカルディスクではありません。
- **「High-performance」は単純には速くありませんでした。** US-CA-2 ではランダム読み込みが 2 倍（16k 対 8k IOPS）、小さいファイルで 1.6× 速かったものの、シーケンシャル書き込みは標準ボリュームの 10 分の 1 の速度でした。データセンターとストレージシステムが同時に変わるので純粋な階層比較ではありませんが、そこで 2 倍の料金を払って得られるのはこれです。
- **グローバルボリュームは積極的にキャッシュします。** 書き込んだ直後の 2 GiB の読み込みはローカルキャッシュから 6.6 GB/s で返りました。別の大陸から 512 MiB のファイルをコールドで読むと 39 MiB/s でした（[#64](https://github.com/litkhai/runpod-hols/issues/64)）。
- **CPU Pod のコンテナディスクは遅いです。** `cpu3c` の Pod では、コンテナディスクの書き込みが 0.23 GB/s、読み込みが 0.13 GB/s で、アタッチしていた network volume よりも遅い結果でした。

<div class="note" markdown="1">
**これは以前のラボのまちまちな数値を置き換えるものです。** Pod ラボ 02 は `dd oflag=direct`（1.6 GB/s）を使い、最初のグローバルボリュームのテストは `/dev/urandom` から書き込んでいました。これはそれ自体で 300 MB/s 付近が上限なので、「コンテナディスク 273 MB/s」は乱数生成器の速度であってディスクの速度ではありませんでした。
</div>

## 2 つの書き込み元、1 つのボリューム
{: #sharing-ja }

| | 標準の network volume（EU-RO-1） | グローバルボリューム（CA-MTL-1 + EU-RO-1） |
|---|---|---|
| 一方で書いた新しいファイルが他方から見えるまで | < 4 s | 3 s |
| 両方が同じ瞬間に 1 つのファイルへ書き込む | 両方とも同じ最終内容を読む | **それぞれが自分のバージョンを保持**、45 s 後も同じ |
| 各側から 200 回の追記 | 400 行すべてが存在 | 未テスト |

network volume は 1 つの共有ファイルシステムとして振る舞います。グローバルボリュームはそうではありません。同時に書き込むと内容が分岐し、競合は何も報告されません。Runpod のドキュメントは「最後の書き込みが勝つ」とし、共有される可変データには network volume を推奨しています。測定結果は推奨のほうとは一致しますが、「最後の書き込みが勝つ」とは一致しません。ドキュメントはまた、複数の Serverless ワーカーから同時に 1 つの network volume に書き込むと「may cause data corruption」と警告しています。ここでは追記は無事でしたが、書き込み元は一度に 1 つと考えてください。

## モデルの重みをどこに置くか
{: #model-weights-ja }

同じ vLLM ワーカー（`worker-v1-vllm` v2.28.0、Qwen2.5-7B-Instruct、14.29 GiB）、RTX 4090、読み返した FlashBoot はオフ、コールドスタートは 180 s 間隔：

| 重み | コールドスタートの `delayTime` | 重みに起きたこと |
|---|---|---|
| 毎回ダウンロード | 96.8–123.4 s | ダウンロード 12.1–28.4 s、その後数秒でロード |
| エンドポイントの **Model** フィールド（ホストキャッシュ） | **85.7–129.9 s** | ダウンロードなし。シャードはホストから 5–46 s |
| network volume（`/runpod-volume`） | 137.9–195.2 s | 初回以降ダウンロードなし。ロードは ~0.5 GB/s で 27.8–31.1 s |

network volume はダウンロードを省きましたが、その分だけ MooseFS からの読み込みに時間がかかり、コールドスタートは全体として遅くなりました。このサイズのモデルなら、エンドポイントの Model フィールド（[Serverless]({{ '/serverless/' | relative_url }})）を設定し、network volume は永続化と共有が必要なデータ、つまり出力、チェックポイント、複数の Pod が読むデータセットのために残しておいてください。グローバルボリュームは重みには試していません。測定したリージョン間のコールド読み込み（39 MiB/s）で候補から外れます。

## Pod なしでデータを入れる — S3 API
{: #s3-ja }

S3 対応のデータセンター（ここでは EU-RO-1）にある network volume は `https://s3api-<dc>.runpod.io` でも応答し、ボリューム id がバケット名になります。**Credentials → S3 API Keys** で作る S3 API キーが必要です。Runpod の API キーとは別物で、S3 対応のすべてのボリュームに読み書き権限を持ちます。2026-11-07 に `aws s3 cp` で 1 GiB を測った結果：

| クライアント | アップロード | ダウンロード |
|---|---|---|
| このリポジトリのビルドサーバー（Runpod の外） | 20 MiB/s | 66 MiB/s |
| 同じデータセンターの CPU Pod | 30 MiB/s | 210 MiB/s |
| 同じファイルを Pod のマウント経由で | | 1.27 GB/s |

- **2 つの経路は同じファイルシステムです。** S3 でアップロードしたファイルは Pod の `/workspace` に同じ sha256 で現れ、Pod で書いたファイルはすぐに S3 の一覧に出ました。
- **アップロードはどこからでも遅いです。** 20〜30 MiB/s は 1 GiB あたり 35〜50 秒です。小さなファイル 100 個は毎秒 20 個でした。設定ファイルやアダプターには十分ですが、15 GB のモデルには遅いです——Model 欄と比べてください。
- **アップロードしたファイルは `root`、パーミッション 600 です**（ディレクトリは 750）。別ユーザーで動くコンテナは `chmod` するまで読めません。
- キーは一度しか表示されず、S3 対応のすべてのボリュームに効きます。使い終わったら削除してください。このテストのキーも終了後に失効させました。

## 選び方
{: #choosing-ja }

| 必要なもの | 使うもの |
|---|---|
| スクラッチ領域、ランダムに読むデータセット、コンパイルキャッシュ | コンテナディスク |
| Serverless エンドポイント用のモデルの重み | エンドポイントの Model フィールド |
| 1 つのデータセンター内で Pod より長く残り、そこの Pod とエンドポイントで共有するファイル | 標準の network volume |
| high-performance のデータセンターでランダム読み込みの多い処理 | high-performance ボリューム。まず測定してください。シーケンシャル書き込みは遅い結果でした |
| 複数のリージョンが必要とする、主に読むだけのファイル | グローバルボリューム。書き込み元は 1 つにし、数秒の遅延を見込んでください |
| Pod の削除後も残す必要があるが共有は不要なデータ | Pod ボリュームは network volume と同じシステムで、料金はより高いです |

まだ扱っていないもの：Instant Cluster のボリューム。

</div>

