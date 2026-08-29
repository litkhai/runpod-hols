# Pod Lab 01 — Launch, Connect, Tear Down

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** launch a Pod from Python, connect to it, and destroy it — without leaving anything billing.

**Time:** ~15 minutes · **Cost:** a CPU Pod for a few minutes

### Why CPU by default

Launching, connecting and tearing down needs no GPU. `create_pod` treats `gpu_type_id=None` as a CPU-only Pod, which is the cheapest way to learn the mechanics. Add `--gpu` when you have something to run.

```bash
python launch.py                            # CPU-only
python launch.py --gpu "NVIDIA RTX A4000"   # with a GPU
```

### The one thing that costs money

A Pod bills from boot until you terminate it, whether you are using it or not. Everything in this lab is arranged around that:

| Guard | What it does |
|---|---|
| `--dry-run` | Prints the plan, creates nothing |
| Typed confirmation | `yes`, not `y` — a y/N prompt is too easy to fly through |
| Refuses to stack | `launch.py` stops if a Pod is already running |
| GPU id validated first | A typo fails before you are asked to approve spending |
| `status.py` | Rate per hour, uptime, and spend so far |
| `teardown.py` | Terminates the Pod `launch.py` recorded, no arguments needed |

### Files

| File | Role |
|---|---|
| `launch.py` | Creates the Pod, records its id in `.pod-id` |
| `status.py` | Read-only. Every Pod, its cost, and its SSH details |
| `teardown.py` | Terminates (or `--stop`s) the Pod |
| `common.py` | Credential loading, formatting, the confirmation prompt |

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
    compute CPU only
    disks   container 10GB, volume 10GB at /workspace

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
ssh      ssh root@<ip> -p <port> -i ~/.ssh/id_ed25519
```

Ports take a moment to appear after boot — rerun if the line says it is not ready. SSH needs your public key registered under [Settings → SSH Keys](https://console.runpod.io/user/settings); `runpod ssh add-key` does it for you. JupyterLab is exposed on 8888 and reachable from the Pod's page in the console.

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

### Verified

Against a real account, read-only, nothing created:

| Check | Result |
|---|---|
| All four scripts compile | Pass |
| `status.py` with no Pods | `No Pods. Nothing is costing you anything.` |
| `launch.py --dry-run` | Prints the plan, creates nothing |
| `launch.py --gpu <bogus>` | Rejected before the confirmation prompt |
| `teardown.py` with no `.pod-id` | Clean message, no traceback |

**Not verified:** an actual Pod launch, SSH connection, and teardown. Those bill.

---

## 한국어

**목표:** Python 으로 Pod 을 기동하고 접속한 뒤 삭제합니다. 과금되는 것을 남기지 않고요.

**소요 시간:** 약 15분 · **비용:** CPU Pod 몇 분

### 왜 기본값이 CPU 인가

기동·접속·정리에는 GPU 가 필요 없습니다. `create_pod` 은 `gpu_type_id=None` 을 CPU 전용 Pod 으로 취급하는데, 동작 방식을 익히는 데 가장 저렴한 방법입니다. 실제로 돌릴 것이 생기면 `--gpu` 를 붙이면 됩니다.

```bash
python launch.py                            # CPU 전용
python launch.py --gpu "NVIDIA RTX A4000"   # GPU 부착
```

### 돈이 나가는 지점은 하나입니다

Pod 은 기동부터 삭제까지, 사용 여부와 무관하게 과금됩니다. 이 실습의 구성은 전부 그 사실을 중심으로 짜여 있습니다.

| 안전장치 | 하는 일 |
|---|---|
| `--dry-run` | 계획만 출력, 생성하지 않음 |
| 타이핑 확인 | `y` 가 아니라 `yes`. y/N 프롬프트는 너무 쉽게 지나쳐짐 |
| 중복 방지 | 이미 실행 중인 Pod 이 있으면 `launch.py` 가 중단 |
| GPU ID 선검증 | 오타라면 지출 승인 전에 실패 |
| `status.py` | 시간당 요율, 가동 시간, 현재까지의 지출 |
| `teardown.py` | `launch.py` 가 기록한 Pod 을 인자 없이 삭제 |

### 파일 구성

| 파일 | 역할 |
|---|---|
| `launch.py` | Pod 생성, id 를 `.pod-id` 에 기록 |
| `status.py` | 읽기 전용. 모든 Pod 과 비용, SSH 정보 |
| `teardown.py` | Pod 삭제 (또는 `--stop` 으로 중지) |
| `common.py` | 자격 증명 로딩, 출력 형식, 확인 프롬프트 |

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
    compute CPU only
    disks   container 10GB, volume 10GB at /workspace

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
ssh      ssh root@<ip> -p <port> -i ~/.ssh/id_ed25519
```

기동 직후에는 포트가 뜨기까지 잠깐 걸립니다. 준비되지 않았다고 나오면 다시 실행하세요. SSH 를 쓰려면 [Settings → SSH Keys](https://console.runpod.io/user/settings) 에 공개키가 등록돼 있어야 하며, `runpod ssh add-key` 가 대신 처리해 줍니다. JupyterLab 은 8888 로 노출되고 콘솔의 Pod 페이지에서 접근할 수 있습니다.

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

### 검증 내역

실제 계정에 대해 읽기 전용으로, 생성한 것 없이 확인했습니다.

| 확인 항목 | 결과 |
|---|---|
| 스크립트 4개 컴파일 | 통과 |
| Pod 없을 때 `status.py` | `No Pods. Nothing is costing you anything.` |
| `launch.py --dry-run` | 계획 출력, 생성 없음 |
| `launch.py --gpu <잘못된값>` | 확인 프롬프트 전에 거부 |
| `.pod-id` 없을 때 `teardown.py` | 깔끔한 안내, 트레이스백 없음 |

**미검증:** 실제 Pod 기동, SSH 접속, 삭제. 과금되는 동작입니다.
