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

A CPU Pod needs an instance id, `<flavor>-<vCPU>-<memory GB>`; the SDK sends `cpu3c-2-4` as `{"id": "cpu3c", "vcpuCount": 2}`. The flavors come from `GET /v2/catalog/cpus`: `cpu3c`/`cpu5c` (2 GB per vCPU), `cpu3g`/`cpu5g` (4 GB), `cpu3m`/`cpu5m` (8 GB), 2–32 vCPU.

### Setup

```bash
cd pod/01-launch-connect
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # runpod~=2.4.0
```

`runpod` 2.x calls REST API v2 for Pods, so the lab key with GraphQL set to None works ([#126](https://github.com/litkhai/runpod-hols/issues/126)). Until 2026-11-24 this lab pinned 1.12, which used GraphQL. Porting meant more than the launch call:

- `get_pods()` returns REST objects: `status`, `image`, `cost`, `gpu`/`cpu`, `ssh.direct`. The 1.x names `desiredStatus`, `imageName`, `costPerHr` and `uptimeSeconds` are gone, and a filter on them matches nothing — `launch.py` would stop refusing a second Pod.
- `create_pod` rejects `volume_mount_path` on a CPU Pod without a network volume, so `launch.py` sends no volume for CPU.
- `runtime.uptime` read 4 seconds for the whole run, so `status.py` counts uptime from `startedAt`.
- `get_gpu(id, count)` reads `/v2/catalog/gpus/{id}` with availability; `launch.py` prints the stock and price before asking.

[What else changed in 2.x](../../sdk/client.md#what-changed-in-2x).

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
| `requirements.txt` | `runpod~=2.4.0` |

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
    image   runpod/pytorch:2.2.0-cu1281-torch291-ubuntu2404
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

### Without SSH — exec and logs

REST v2 runs a command in a Pod and streams its logs over HTTPS, with no SSH key, port or public IP. Run on 2026-11-24 on a `cpu3c` 2-vCPU CPU Pod created without `startSsh` or ports ([#112](https://github.com/litkhai/runpod-hols/issues/112)).

```bash
curl -X POST https://api.runpod.io/v2/pods/$POD_ID/exec -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H 'Content-Type: application/json' -d '{"command": ["sh", "-c", "nproc; df -h / | tail -1"]}'
# Server-Sent Events: the stream stays open, so always bound it with -m
curl -sN -m 15 -H "Authorization: Bearer $RUNPOD_API_KEY" "https://api.runpod.io/v2/pods/$POD_ID/logs?tail=20"
```

| Call | Result |
|---|---|
| exec right after the create | `409 Pod container is starting, retry shortly`; the first 200 came about 25 s after the Pod read `RUNNING` |
| `["sh", "-c", "echo out; echo err >&2; exit 3"]` | 200 with `exitCode` 3, `stdout` and `stderr` — a non-zero exit is a result, not an error |
| `["sleep", "30"]` with `timeoutSeconds` 2 | 200 after 2 s, `timedOut: true`, `exitCode` null |
| `env` and `cwd` | `{"GREETING": "hi"}` in `/tmp` printed `hi from /tmp` |
| `echo marker > /proc/1/fd/1` | The line appeared in the log stream as `source: container` |
| `logs?tail=20` | `system` lines (image pull, container start) and `container` lines (the image's start script); `source=` picks one |

**The key needs GraphQL access.** With the lab key (GraphQL None) exec answered `403 This API key cannot run commands on pods` and logs `403 Access to the requested resource was denied`. A key with REST *All resources* and GraphQL Read only got logs but still not exec; GraphQL Read / Write unlocked both. The spec names only `pods:write` and `pods:read`. Serverless worker logs behave the same way ([#104](https://github.com/litkhai/runpod-hols/issues/104)).

Three CPU Pods of about two minutes each, about USD 0.01 in all.

### Where the volume actually mounts

The SDK and the console disagree:

| | Default mount |
|---|---|
| Console | `/workspace` |
| SDK `create_pod` | `/runpod-volume` |

`launch.py` pins `volume_mount_path="/workspace"` so the path matches the console, the docs and the other labs. If you call `create_pod` yourself and skip that argument, your persistent disk lands somewhere else and nothing warns you.

That applies to GPU Pods. A CPU Pod gets no volume disk: SDK 2.x rejects `volume_mount_path` there, and SDK 1.12 dropped `volume_in_gb`. The Pod came up with `volumeInGb` 0, and `df` showed `/workspace` on the same 10 GB overlay as `/`. Anything written there is gone at terminate, and at stop as well. Persistent storage on CPU Pods is [#16](https://github.com/litkhai/runpod-hols/issues/16).

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

The whole run cost under one cent. Not checked in this run: JupyterLab on 8888, `--stop`, a GPU Pod from this script — all three were checked on 2026-11-26, below ([`terraform/02-pod`](../../terraform/02-pod) launched GPU Pods on 2026-10-16).

**Re-run on `runpod` 2.4.0, 2026-11-24** ([#126](https://github.com/litkhai/runpod-hols/issues/126)), with the lab key (GraphQL None):

| Step | Result |
|---|---|
| `status.py` before | `No Pods.` |
| `launch.py --dry-run`, CPU and `--gpu` | Plan printed; the GPU plan shows stock and price from the catalog |
| `launch.py --gpu "NOT-A-GPU" --dry-run` | Refused before the plan, nothing created |
| `launch.py` | `cpu3c`, 2 vCPU, US-CA-2, $0.06/hr |
| SSH | Connected. `nproc` 2, `/workspace` on the 10 GB overlay, torch 2.9.1+cu128 |
| `launch.py` again | Refused: a Pod is already running |
| `teardown.py --yes` | Terminated |
| `status.py` after | `No Pods.`; `currentSpendPerHr` 0 |

About 8 minutes, under one cent.

**Image `runpod/pytorch:2.2.0-cu1281-torch291-ubuntu2404`, 2026-11-26** ([#143](https://github.com/litkhai/runpod-hols/issues/143)); `DEFAULT_IMAGE` was 1.0.7 before. `launch.py --gpu` on an L4 (A5000, RTX 2000 Ada and A4000 had no stock): SSH after 188 s, `NVIDIA L4` driver 595.112.07, torch 2.9.1+cu128 with `torch.cuda.is_available()` True and a CUDA matmul, Python 3.12.3, Ubuntu 24.04.5. Port 8888 was not listening — `launch.py` does not ask for JupyterLab (`startJupyter` defaults to false). A separate REST v2 Pod with `startJupyter: true` on the same image served JupyterLab's login page on the 8888 proxy 126 s after create. Both Pods terminated.

**`teardown.py --stop`, 2026-11-26** ([#153](https://github.com/litkhai/runpod-hols/issues/153)). `launch.py --gpu` was refused for RTX A4000 (catalog stock `LOW`), A4500, A5000, RTX 2000 Ada and RTX 4000 Ada (*no longer any instances available*) and created an L4 in EUR-IS-1 at $0.69/hr.

| Step | Result |
|---|---|
| `status.py` | `RUNNING`, SSH address after 213 s |
| `teardown.py --stop` | `stopped`; `.pod-id` kept |
| `status.py` 10 s later | Listed under *STOPPED — GPU released, volume storage still billed*: status `EXITED`, `$0.69/hr not running`, volume 10GB at `/workspace` |
| REST v2 `GET /v2/pods/{id}` | `status` `EXITED`; `gpu` still `NVIDIA L4` ×1, `cost` still 0.69 (the rate, not what is billed), `ssh.direct` still listed |
| `teardown.py` | Terminated the stopped Pod and removed `.pod-id` |
| `status.py` after | `No Pods.`; `currentSpendPerHr` 0 |

249 s, about USD 0.05. Starting the stopped Pod again was not tried here; [`02-storage`](../02-storage) covers stop and start.

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

CPU Pod 에는 인스턴스 ID (`<flavor>-<vCPU>-<메모리 GB>`) 가 필요합니다. SDK 는 `cpu3c-2-4` 를 `{"id": "cpu3c", "vcpuCount": 2}` 로 보냅니다. flavor 목록은 `GET /v2/catalog/cpus` 에서 나옵니다. `cpu3c`/`cpu5c` (vCPU 당 2 GB), `cpu3g`/`cpu5g` (4 GB), `cpu3m`/`cpu5m` (8 GB), vCPU 2–32개.

### 준비

```bash
cd pod/01-launch-connect
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt   # runpod~=2.4.0
```

`runpod` 2.x 는 Pod 호출에 REST API v2 를 쓰므로 GraphQL 을 None 으로 둔 실습용 키로 동작합니다 ([#126](https://github.com/litkhai/runpod-hols/issues/126)). 2026-11-24 전까지는 GraphQL 을 쓰는 1.12 로 고정했습니다. 포팅은 기동 호출만의 문제가 아니었습니다.

- `get_pods()` 는 REST 객체 — `status`, `image`, `cost`, `gpu`/`cpu`, `ssh.direct` — 를 돌려줍니다. 1.x 의 `desiredStatus`, `imageName`, `costPerHr`, `uptimeSeconds` 는 없고, 이 이름으로 거르면 아무것도 걸리지 않아 `launch.py` 의 중복 기동 방지가 작동하지 않습니다.
- `create_pod` 은 네트워크 볼륨 없는 CPU Pod 에 `volume_mount_path` 를 주면 거부하므로, `launch.py` 는 CPU 에는 볼륨을 보내지 않습니다.
- `runtime.uptime` 이 실행 내내 4초였으므로 `status.py` 는 `startedAt` 부터 가동 시간을 계산합니다.
- `get_gpu(id, count)` 는 `/v2/catalog/gpus/{id}` 를 재고와 함께 읽습니다. `launch.py` 는 확인을 묻기 전에 재고와 가격을 출력합니다.

[2.x 의 다른 변경점](../../sdk/client.md#2x-에서-바뀐-것).

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
| `requirements.txt` | `runpod~=2.4.0` |

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
    image   runpod/pytorch:2.2.0-cu1281-torch291-ubuntu2404
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

### SSH 없이 — exec 와 로그

REST v2 는 SSH 키·포트·공인 IP 없이 HTTPS 로 Pod 안에서 명령을 실행하고 로그를 스트리밍합니다. 2026-11-24 에 `startSsh` 와 포트 없이 만든 `cpu3c` 2 vCPU CPU Pod 에서 실행했습니다 ([#112](https://github.com/litkhai/runpod-hols/issues/112)).

```bash
curl -X POST https://api.runpod.io/v2/pods/$POD_ID/exec -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H 'Content-Type: application/json' -d '{"command": ["sh", "-c", "nproc; df -h / | tail -1"]}'
# Server-Sent Events: the stream stays open, so always bound it with -m
curl -sN -m 15 -H "Authorization: Bearer $RUNPOD_API_KEY" "https://api.runpod.io/v2/pods/$POD_ID/logs?tail=20"
```

| 호출 | 결과 |
|---|---|
| 생성 직후 exec | `409 Pod container is starting, retry shortly`. Pod 이 `RUNNING` 이 된 지 약 25초 뒤 처음 200 |
| `["sh", "-c", "echo out; echo err >&2; exit 3"]` | `exitCode` 3, `stdout`, `stderr` 를 담은 200 — 0 이 아닌 종료도 오류가 아니라 결과 |
| `timeoutSeconds` 2 로 `["sleep", "30"]` | 2초 뒤 200, `timedOut: true`, `exitCode` null |
| `env` 와 `cwd` | `/tmp` 에서 `{"GREETING": "hi"}` 로 `hi from /tmp` 출력 |
| `echo marker > /proc/1/fd/1` | 그 줄이 로그 스트림에 `source: container` 로 나타남 |
| `logs?tail=20` | `system` 줄 (이미지 pull, 컨테이너 시작) 과 `container` 줄 (이미지 시작 스크립트). `source=` 로 하나만 고를 수 있음 |

**키에 GraphQL 권한이 필요합니다.** 실습용 키 (GraphQL None) 로는 exec 가 `403 This API key cannot run commands on pods`, 로그가 `403 Access to the requested resource was denied` 였습니다. REST *All resources* 에 GraphQL Read only 를 준 키는 로그는 됐지만 exec 는 여전히 안 됐고, GraphQL Read / Write 를 주자 둘 다 됐습니다. 스펙에는 `pods:write` 와 `pods:read` 만 적혀 있습니다. Serverless 워커 로그도 같습니다 ([#104](https://github.com/litkhai/runpod-hols/issues/104)).

약 2분짜리 CPU Pod 세 개, 합계 약 USD 0.01.

### 볼륨이 실제로 마운트되는 위치

SDK 와 콘솔이 다릅니다.

| | 기본 마운트 위치 |
|---|---|
| 콘솔 | `/workspace` |
| SDK `create_pod` | `/runpod-volume` |

`launch.py` 는 `volume_mount_path="/workspace"` 를 명시해 콘솔·문서·다른 실습과 경로를 맞춥니다. `create_pod` 을 직접 호출하면서 이 인자를 빠뜨리면 영구 디스크가 다른 곳에 붙고, 아무 경고도 나오지 않습니다.

이는 GPU Pod 이야기입니다. CPU Pod 에는 볼륨 디스크가 없습니다. SDK 2.x 는 거기에 `volume_mount_path` 를 주면 거부하고, SDK 1.12 는 `volume_in_gb` 를 보내지 않았습니다. Pod 은 `volumeInGb` 0 으로 떴고, `df` 로 보면 `/workspace` 가 `/` 와 같은 10 GB overlay 위에 있었습니다. 여기에 쓴 것은 삭제 때는 물론 중지 때도 사라집니다. CPU Pod 의 영구 스토리지는 [#16](https://github.com/litkhai/runpod-hols/issues/16) 에서 다룹니다.

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

전체 비용은 1센트 미만이었습니다. 이 실행에서 확인하지 않은 것: 8888 의 JupyterLab, `--stop`, 이 스크립트로 GPU Pod 기동. 세 가지 모두 2026-11-26 에 확인했다 (아래) ([`terraform/02-pod`](../../terraform/02-pod) 이 2026-10-16 에 GPU Pod 을 띄움).

**`runpod` 2.4.0 재실행, 2026-11-24** ([#126](https://github.com/litkhai/runpod-hols/issues/126)), 실습용 키 (GraphQL None):

| 단계 | 결과 |
|---|---|
| 시작 전 `status.py` | `No Pods.` |
| `launch.py --dry-run`, CPU 와 `--gpu` | 계획 출력. GPU 계획에는 카탈로그의 재고와 가격이 나옴 |
| `launch.py --gpu "NOT-A-GPU" --dry-run` | 계획 전에 거부, 생성 없음 |
| `launch.py` | `cpu3c`, vCPU 2개, US-CA-2, $0.06/hr |
| SSH | 접속. `nproc` 2, `/workspace` 는 10 GB overlay, torch 2.9.1+cu128 |
| `launch.py` 재실행 | 거부: 이미 실행 중인 Pod 있음 |
| `teardown.py --yes` | 삭제 |
| 종료 후 `status.py` | `No Pods.`, `currentSpendPerHr` 0 |

약 8분, 1센트 미만.

**이미지 `runpod/pytorch:2.2.0-cu1281-torch291-ubuntu2404`, 2026-11-26** ([#143](https://github.com/litkhai/runpod-hols/issues/143)). 그전 `DEFAULT_IMAGE` 는 1.0.7. L4 에서 `launch.py --gpu` (A5000, RTX 2000 Ada, A4000 은 재고 없음): 188초 뒤 SSH, `NVIDIA L4` 드라이버 595.112.07, torch 2.9.1+cu128 에서 `torch.cuda.is_available()` True 와 CUDA 행렬곱, Python 3.12.3, Ubuntu 24.04.5. 8888 포트는 열려 있지 않았다. `launch.py` 가 JupyterLab 을 요청하지 않기 때문이다 (`startJupyter` 기본값 false). 같은 이미지로 `startJupyter: true` 를 준 REST v2 Pod 를 따로 만들었더니 생성 126초 뒤 8888 프록시에서 JupyterLab 로그인 페이지가 나왔다. 두 Pod 모두 삭제했다.

**`teardown.py --stop`, 2026-11-26** ([#153](https://github.com/litkhai/runpod-hols/issues/153)). `launch.py --gpu` 는 RTX A4000 (카탈로그 재고 `LOW`), A4500, A5000, RTX 2000 Ada, RTX 4000 Ada 에서 거부됐고 (*no longer any instances available*), EUR-IS-1 의 L4 를 시간당 $0.69 에 만들었다.

| 단계 | 결과 |
|---|---|
| `status.py` | `RUNNING`, 213초 뒤 SSH 주소 |
| `teardown.py --stop` | `stopped`, `.pod-id` 유지 |
| 10초 뒤 `status.py` | *STOPPED — GPU 반납, 볼륨 스토리지는 계속 과금* 아래에 표시: 상태 `EXITED`, `$0.69/hr not running`, `/workspace` 에 볼륨 10GB |
| REST v2 `GET /v2/pods/{id}` | `status` `EXITED`. `gpu` 는 여전히 `NVIDIA L4` ×1, `cost` 도 0.69 (요율이지 과금액이 아님), `ssh.direct` 도 그대로 |
| `teardown.py` | 중지된 Pod 을 삭제하고 `.pod-id` 제거 |
| 종료 후 `status.py` | `No Pods.`, `currentSpendPerHr` 0 |

249초, 약 USD 0.05. 중지한 Pod 을 다시 시작하는 것은 여기서 해보지 않았다. 중지와 시작은 [`02-storage`](../02-storage) 에서 다룬다.
