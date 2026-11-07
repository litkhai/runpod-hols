# Pod Lab 01 — Launch, Connect, Tear Down

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** launch a Pod from Python, connect to it, and destroy it — without leaving anything billing.

**Time:** ~15 minutes · **Cost:** a CPU Pod for a few minutes

### Why CPU by default

Launching, connecting and tearing down needs no GPU. `create_pod` treats `gpu_type_id=None` as a CPU-only Pod, which is the cheapest way to learn the mechanics — `cpu3c-2-4` was $0.06/hr on 2026-11-05. Add `--gpu` when you have something to run.

```bash
python launch.py                            # CPU-only, cpu3c-2-4
python launch.py --cpu cpu3g-4-16           # a bigger CPU Pod
python launch.py --gpu "NVIDIA RTX A4000"   # with a GPU
```

A CPU Pod needs an instance id, `<flavor>-<vCPU>-<memory GB>`. Without one the API answers `Field "deployCpuPodInput.instanceId" of required type "String!" was not provided`. The flavors come from the `cpuFlavors` GraphQL query: `cpu3c`/`cpu5c` (2 GB per vCPU), `cpu3g`/`cpu5g` (4 GB), `cpu3m`/`cpu5m` (8 GB), 2–32 vCPU.

### Setup — pin the SDK

```bash
cd pod/01-launch-connect
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # runpod~=1.12.0
```

The scripts are written against the 1.x client. `runpod` 2.0.0 (2026-10-30) moved Pod calls to REST API v2 and rejects this lab's CPU launch before sending anything: `REST API v2 does not support: volume_mount_path on CPU pods without network_volume_id`. An unpinned `pip install runpod` gets 2.x.

Porting is more than the launch call. In 2.x `get_pods()` returns REST objects — `status`, `image`, `cost`, `runtime.uptime` — where these scripts read `desiredStatus`, `imageName`, `costPerHr` and `uptimeSeconds`. On 2.x the running-Pod filter would match nothing, so `launch.py` would no longer refuse to stack Pods. The pin stays until the scripts are ported and run again ([SDK 2.x changes](../../sdk/client.md#what-changed-in-2x)).

### The one thing that costs money

A Pod bills from boot until you terminate it, whether you are using it or not. Everything in this lab is arranged around that:

| Guard | What it does |
|---|---|
| `--dry-run` | Prints the plan, creates nothing |
| Typed confirmation | `yes`, not `y` — a y/N prompt is too easy to fly through |
| Refuses to stack | `launch.py` stops if a Pod is already running |
| GPU id validated first | A typo fails before you are asked to approve spending |
| `status.py` | Rate per hour; uptime and spend so far when the API reports uptime |
| `teardown.py` | Terminates the Pod `launch.py` recorded, no arguments needed |

### Files

| File | Role |
|---|---|
| `launch.py` | Creates the Pod, records its id in `.pod-id` |
| `status.py` | Read-only. Every Pod, its cost, and its SSH details |
| `teardown.py` | Terminates (or `--stop`s) the Pod |
| `common.py` | Credential loading, formatting, the confirmation prompt |
| `requirements.txt` | `runpod~=1.12.0` |

### Step 1 — See what you have

```bash
cd pod/01-launch-connect
python status.py
```

```
No Pods. Nothing is costing you anything.
```

Worth running before and after every lab.

### Step 2 — Rehearse

```bash
python launch.py --dry-run
```

```
About to create a Pod:
    name    hol-pod-01
    image   runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404
    compute CPU only (cpu3c-2-4)
    disks   container 10GB; no volume disk on a CPU Pod — /workspace is on the container disk

Billing starts when it boots and continues until you terminate it,
whether or not you are using it.

--dry-run: nothing created.
```

A wrong GPU id fails here rather than after you have approved the spend:

```
$ python launch.py --gpu "NVIDIA NOT-A-REAL-GPU"
Unknown GPU type 'NVIDIA NOT-A-REAL-GPU': No GPU found with the specified ID…
```

### Step 3 — Launch

```bash
python launch.py
```

It prints the plan, asks you to type `yes`, then creates the Pod and writes its id to `.pod-id`.

### Step 4 — Connect

```bash
python status.py
```

Once the Pod has booted, `status.py` prints the SSH command with the public IP and port filled in:

```
hol-pod-01  (uuv9df4dtk59gd)
    status   RUNNING   CPU only
    cost     $0.06/hr   uptime not reported — check the console
    volume   0GB at /workspace
ssh      ssh root@157.157.221.29 -p 37495 -i ~/.ssh/id_ed25519
```

Ports take a moment to appear after boot — rerun if the line says it is not ready. On 2026-11-05 the SSH line appeared about 4 minutes after `create_pod` returned, and SSH connected on the first try. The API reported `uptimeSeconds` 0 the whole time, so `status.py` cannot estimate spend; the console's billing page can. SSH needs your public key registered under [Credentials → SSH Public Keys](https://console.runpod.io/user/credentials?tab=ssh-key); `runpod ssh add-key` does it for you. JupyterLab is exposed on 8888 and reachable from the Pod's page in the console.

### Step 5 — Tear down

```bash
python teardown.py
```

```bash
python teardown.py --stop   # release the GPU, keep the volume (and its bill)
python teardown.py --all    # every Pod on the account
```

Then confirm with `python status.py`.

### Where the volume actually mounts

The SDK and the console disagree:

| | Default mount |
|---|---|
| Console | `/workspace` |
| SDK `create_pod` | `/runpod-volume` |

`launch.py` pins `volume_mount_path="/workspace"` so the path matches the console, the docs and the other labs. If you call `create_pod` yourself and skip that argument, your persistent disk lands somewhere else and nothing warns you.

That applies to GPU Pods. On a CPU Pod, SDK 1.12 never sends `volume_in_gb`: the Pod came up with `volumeInGb` 0, and `df` showed `/workspace` on the same 10 GB overlay as `/`. Anything written there is gone at terminate, and at stop as well. Persistent storage on CPU Pods is [#16](https://github.com/litkhai/runpod-hols/issues/16).

### Verified

Run end to end on 2026-11-05 with `runpod` 1.12.0, CPU Pod `cpu3c-2-4`, from the lab venv:

| Step | Result |
|---|---|
| `status.py` before | `No Pods.` |
| `launch.py --dry-run` | Prints the plan, creates nothing |
| `launch.py` without `--cpu` (first run) | Rejected by the API: `instanceId` is required. Nothing created. Fixed with the `--cpu` default |
| `launch.py` | Pod created, id written to `.pod-id` |
| `status.py` until SSH appears | About 4 minutes; `$0.06/hr`, `volume 0GB`, `uptimeSeconds` 0 |
| SSH | Connected first try. Ubuntu 24.04.4, 2 vCPU, torch 2.9.1+cu128, `/` and `/workspace` both on a 10 GB overlay |
| `teardown.py` | Terminated, `.pod-id` removed |
| `status.py` after | `No Pods.` |

The whole run cost under one cent. Not checked: JupyterLab on 8888, `--stop`, a GPU Pod from this script ([`terraform/02-pod`](../../terraform/02-pod) launched GPU Pods on 2026-10-16).

---

## 한국어

**목표:** Python 으로 Pod 을 기동하고 접속한 뒤 삭제합니다. 과금되는 것을 남기지 않고요.

**소요 시간:** 약 15분 · **비용:** CPU Pod 몇 분

### 왜 기본값이 CPU 인가

기동·접속·정리에는 GPU 가 필요 없습니다. `create_pod` 은 `gpu_type_id=None` 을 CPU 전용 Pod 으로 취급하는데, 동작 방식을 익히는 데 가장 저렴한 방법입니다. 2026-11-05 기준 `cpu3c-2-4` 가 시간당 $0.06 이었습니다. 실제로 돌릴 것이 생기면 `--gpu` 를 붙이면 됩니다.

```bash
python launch.py                            # CPU 전용, cpu3c-2-4
python launch.py --cpu cpu3g-4-16           # 더 큰 CPU Pod
python launch.py --gpu "NVIDIA RTX A4000"   # GPU 부착
```

CPU Pod 에는 인스턴스 ID (`<flavor>-<vCPU>-<메모리 GB>`) 가 필요합니다. 없으면 API 가 `Field "deployCpuPodInput.instanceId" of required type "String!" was not provided` 로 거부합니다. flavor 목록은 GraphQL `cpuFlavors` 쿼리에서 나옵니다. `cpu3c`/`cpu5c` (vCPU 당 2 GB), `cpu3g`/`cpu5g` (4 GB), `cpu3m`/`cpu5m` (8 GB), vCPU 2–32개.

### 준비 — SDK 버전 고정

```bash
cd pod/01-launch-connect
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # runpod~=1.12.0
```

스크립트는 1.x 클라이언트 기준입니다. `runpod` 2.0.0 (2026-10-30) 은 Pod 호출을 REST API v2 로 옮겼고, 이 실습의 CPU 기동을 요청을 보내기도 전에 거부합니다. `REST API v2 does not support: volume_mount_path on CPU pods without network_volume_id`. 버전을 고정하지 않은 `pip install runpod` 는 2.x 를 설치합니다.

포팅은 기동 호출만의 문제가 아닙니다. 2.x 의 `get_pods()` 는 REST 객체 — `status`, `image`, `cost`, `runtime.uptime` — 를 돌려주는데, 이 스크립트는 `desiredStatus`, `imageName`, `costPerHr`, `uptimeSeconds` 를 읽습니다. 2.x 에서는 실행 중 Pod 필터가 아무것도 찾지 못해 `launch.py` 의 중복 기동 방지가 작동하지 않습니다. 스크립트를 포팅하고 다시 실행할 때까지 고정을 유지합니다 ([SDK 2.x 변경점](../../sdk/client.md#2x-에서-바뀐-것)).

### 돈이 나가는 지점은 하나입니다

Pod 은 기동부터 삭제까지, 사용 여부와 무관하게 과금됩니다. 이 실습의 구성은 전부 그 사실을 중심으로 짜여 있습니다.

| 안전장치 | 하는 일 |
|---|---|
| `--dry-run` | 계획만 출력, 생성하지 않음 |
| 타이핑 확인 | `y` 가 아니라 `yes`. y/N 프롬프트는 너무 쉽게 지나쳐짐 |
| 중복 방지 | 이미 실행 중인 Pod 이 있으면 `launch.py` 가 중단 |
| GPU ID 선검증 | 오타라면 지출 승인 전에 실패 |
| `status.py` | 시간당 요율. API 가 가동 시간을 주면 가동 시간과 현재까지의 지출 |
| `teardown.py` | `launch.py` 가 기록한 Pod 을 인자 없이 삭제 |

### 파일 구성

| 파일 | 역할 |
|---|---|
| `launch.py` | Pod 생성, id 를 `.pod-id` 에 기록 |
| `status.py` | 읽기 전용. 모든 Pod 과 비용, SSH 정보 |
| `teardown.py` | Pod 삭제 (또는 `--stop` 으로 중지) |
| `common.py` | 자격 증명 로딩, 출력 형식, 확인 프롬프트 |
| `requirements.txt` | `runpod~=1.12.0` |

### 1단계 — 현재 상태 확인

```bash
cd pod/01-launch-connect
python status.py
```

```
No Pods. Nothing is costing you anything.
```

모든 실습의 시작과 끝에 실행할 가치가 있습니다.

### 2단계 — 예행연습

```bash
python launch.py --dry-run
```

```
About to create a Pod:
    name    hol-pod-01
    image   runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404
    compute CPU only (cpu3c-2-4)
    disks   container 10GB; no volume disk on a CPU Pod — /workspace is on the container disk

Billing starts when it boots and continues until you terminate it,
whether or not you are using it.

--dry-run: nothing created.
```

잘못된 GPU ID 는 지출을 승인한 뒤가 아니라 이 지점에서 실패합니다.

```
$ python launch.py --gpu "NVIDIA NOT-A-REAL-GPU"
Unknown GPU type 'NVIDIA NOT-A-REAL-GPU': No GPU found with the specified ID…
```

### 3단계 — 기동

```bash
python launch.py
```

계획을 출력하고 `yes` 입력을 요구한 뒤, Pod 을 생성하고 id 를 `.pod-id` 에 씁니다.

### 4단계 — 접속

```bash
python status.py
```

Pod 이 기동되면 `status.py` 가 공개 IP 와 포트를 채운 SSH 명령을 출력합니다.

```
hol-pod-01  (uuv9df4dtk59gd)
    status   RUNNING   CPU only
    cost     $0.06/hr   uptime not reported — check the console
    volume   0GB at /workspace
ssh      ssh root@157.157.221.29 -p 37495 -i ~/.ssh/id_ed25519
```

기동 직후에는 포트가 뜨기까지 잠깐 걸립니다. 준비되지 않았다고 나오면 다시 실행하세요. 2026-11-05 에는 `create_pod` 반환 후 약 4분 뒤에 SSH 줄이 나왔고, 첫 시도에 접속됐습니다. 그동안 API 의 `uptimeSeconds` 는 계속 0 이어서 `status.py` 로는 지출을 추정할 수 없습니다. 콘솔의 결제 화면에서 확인하세요. SSH 를 쓰려면 [Credentials → SSH Public Keys](https://console.runpod.io/user/credentials?tab=ssh-key) 에 공개키가 등록돼 있어야 하며, `runpod ssh add-key` 가 대신 처리해 줍니다. JupyterLab 은 8888 로 노출되고 콘솔의 Pod 페이지에서 접근할 수 있습니다.

### 5단계 — 정리

```bash
python teardown.py
```

```bash
python teardown.py --stop   # GPU 반납, 볼륨 유지 (비용도 유지)
python teardown.py --all    # 계정의 모든 Pod
```

이후 `python status.py` 로 확인합니다.

### 볼륨이 실제로 마운트되는 위치

SDK 와 콘솔이 다릅니다.

| | 기본 마운트 위치 |
|---|---|
| 콘솔 | `/workspace` |
| SDK `create_pod` | `/runpod-volume` |

`launch.py` 는 `volume_mount_path="/workspace"` 를 명시해 콘솔·문서·다른 실습과 경로를 맞춥니다. `create_pod` 을 직접 호출하면서 이 인자를 빠뜨리면 영구 디스크가 다른 곳에 붙고, 아무 경고도 나오지 않습니다.

이는 GPU Pod 이야기입니다. CPU Pod 에서는 SDK 1.12 가 `volume_in_gb` 를 아예 보내지 않습니다. Pod 은 `volumeInGb` 0 으로 떴고, `df` 로 보면 `/workspace` 가 `/` 와 같은 10 GB overlay 위에 있었습니다. 여기에 쓴 것은 삭제 때는 물론 중지 때도 사라집니다. CPU Pod 의 영구 스토리지는 [#16](https://github.com/litkhai/runpod-hols/issues/16) 에서 다룹니다.

### 검증 내역

2026-11-05, `runpod` 1.12.0, CPU Pod `cpu3c-2-4`, 실습 venv 에서 처음부터 끝까지 실행했습니다.

| 단계 | 결과 |
|---|---|
| 시작 전 `status.py` | `No Pods.` |
| `launch.py --dry-run` | 계획 출력, 생성 없음 |
| `--cpu` 없는 `launch.py` (첫 실행) | API 가 거부: `instanceId` 필수. 생성된 것 없음. `--cpu` 기본값으로 수정 |
| `launch.py` | Pod 생성, id 를 `.pod-id` 에 기록 |
| SSH 가 뜰 때까지 `status.py` | 약 4분. `$0.06/hr`, `volume 0GB`, `uptimeSeconds` 0 |
| SSH | 첫 시도에 접속. Ubuntu 24.04.4, vCPU 2개, torch 2.9.1+cu128, `/` 와 `/workspace` 모두 10 GB overlay |
| `teardown.py` | 삭제, `.pod-id` 제거 |
| 종료 후 `status.py` | `No Pods.` |

전체 비용은 1센트 미만이었습니다. 확인하지 않은 것: 8888 의 JupyterLab, `--stop`, 이 스크립트로 GPU Pod 기동 ([`terraform/02-pod`](../../terraform/02-pod) 이 2026-10-16 에 GPU Pod 을 띄움).
