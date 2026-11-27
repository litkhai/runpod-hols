# Pod Lab 03 — A Custom Template with Environment Variables and a Secret

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** make a Pod template that sets a plain environment variable and one read from a Runpod secret, launch a Pod from it, and see where each value ends up — inside the container and in the API.

**Time:** ~15 minutes · **Cost:** a CPU Pod for a few minutes ($0.06/hr on 2026-11-05)

### What a template holds

A template is the reusable half of a Pod: image, disks, ports, environment. The Pod adds compute and location. Here the template is created over REST v2 (`POST /v2/templates`; field names changed from v1, [#101](https://github.com/litkhai/runpod-hols/issues/101) — the run below used v1):

```json
{
  "name": "hol-pod-03",
  "image": "runpod/base:1.0.2-ubuntu2404",
  "category": "CPU",
  "serverless": false,
  "disk": 10,
  "ports": ["22/tcp"],
  "startSsh": true,
  "startJupyter": false,
  "env": {
    "GREETING": "hello from the template",
    "DEMO_SECRET": "{{ RUNPOD_SECRET_hol_pod_03_demo }}"
  }
}
```

`{{ RUNPOD_SECRET_<name> }}` is replaced with the secret's value when the Pod boots ([Manage secrets](https://docs.runpod.io/pods/templates/secrets)). Secrets have an API in REST v2 only: `POST https://api.runpod.io/v2/account/secrets` takes `name` and `value`; the value is write-only.

### Files

| File | Role |
|---|---|
| `lab.py` | Secret create/rotate/delete (REST v2), template and Pod create/show/delete (REST v1); ids in `.template.json` |
| `inspect.sh` | Runs inside the Pod; prints plain values in full, secrets as a SHA-256 prefix or a length — never the value |
| `common.py` | `.env` loading and REST calls, standard library only |

The demo secret is a random string `lab.py` generates; it prints only the first 16 hex digits of its SHA-256, so you can match it inside the Pod.

### Step 1 — Secret, template, Pod

```bash
cd pod/03-custom-template
python3 lab.py secret create     # secret value sha256[:16] = 4958d4cc3a4f7138
python3 lab.py template create
python3 lab.py pod create        # CPU Pod, cpu3c, 2 vCPU
python3 lab.py pod show
```

The API never shows the value — not in the template, not in the Pod:

```
env (GET /pods) {"DEMO_SECRET": "{{ RUNPOD_SECRET_hol_pod_03_demo }}", "GREETING": "hello from the template", "PUBLIC_KEY": "ssh-ed25519 …"}
```

### Step 2 — Look inside

```bash
ssh root@<ip> -p <port> 'bash -s' < inspect.sh
```

```
GREETING        this shell: <unset>
GREETING        PID 1:      hello from the template
DEMO_SECRET     this shell: <unset>
DEMO_SECRET     PID 1:      sha256[:16] 4958d4cc3a4f7138
RUNPOD_* names, PID 1: RUNPOD_API_KEY RUNPOD_CPU_COUNT RUNPOD_CPU_POD_PODVERSION RUNPOD_DC_ID RUNPOD_GPU_COUNT RUNPOD_MEM_GB RUNPOD_POD_HOSTNAME RUNPOD_POD_ID RUNPOD_PUBLIC_IP RUNPOD_TCP_PORT_22
RUNPOD_API_KEY  PID 1:      present, 50 chars
/etc/rp_environment: 31 lines, mentions GREETING: 1
```

The secret arrived — the hash matches. Two things are worth knowing:

**`ssh host 'command'` does not see the template's variables.** They are in PID 1's environment. The image's start script copies them into `/etc/rp_environment`, and `/root/.bashrc` sources that file (line 102), so an interactive shell has them and a non-interactive command does not. Scripts run over SSH should `source /etc/rp_environment` first, or read `/proc/1/environ`.

<div class="warn" markdown="1">
**`/etc/rp_environment` holds the resolved secret and the Pod's API key in plain text.** The file is mode `644` on the container disk and contains `export DEMO_SECRET=…` (same hash) and `export RUNPOD_API_KEY=…`. A secret keeps the value out of the template and the API; inside the Pod it is an ordinary file. Treat anything a Pod can read as exposed to whatever runs in that Pod, and rotate when a Pod's host is in doubt.
</div>

### Step 3 — Rotate the secret

```bash
python3 lab.py secret rotate     # secret value sha256[:16] = 5c36d64c0c3f2f37
```

| After the rotation | `DEMO_SECRET` in PID 1 |
|---|---|
| Running Pod, no restart | `4958d4cc3a4f7138` — the old value |
| `POST /pods/{id}/restart` | Failed: `500 … hapi.runpod.net/v1/internal/pod/…/restart: context deadline exceeded`; `lastStartedAt` unchanged |
| `stop`, then `start` | `5c36d64c0c3f2f37` — the new value |

A rotated secret reaches a Pod only at its next boot, as the [v2 reference](https://docs.runpod.io/api-reference-v2/account/update-a-secret) says.

### Step 4 — Clean up

```bash
python3 lab.py pod delete
python3 lab.py template delete
python3 lab.py secret delete
python3 lab.py status            # secrets [], templates [], pods []
```

The Pod template deleted at once. A Serverless template did not, in [Serverless Lab 03](../../serverless/03-vllm-endpoint): it stayed held by its deleted endpoint for up to about 90 minutes.

### Re-run on REST v2 (2026-11-24)

The same steps through REST v2 ([#123](https://github.com/litkhai/runpod-hols/issues/123)), CPU Pod `cpu3c` in US-CA-2, about eight minutes:

| Step | Result |
|---|---|
| Secret, template, Pod | As before; the Pod read back `template: null` although it was created from the template |
| Inside the Pod | PID 1 has the resolved secret (hash matches); a non-interactive SSH shell has neither variable; `/etc/rp_environment` is still mode 644 with the secret and `RUNPOD_API_KEY`; new: `RUNPOD_PROXY_BASE` |
| Rotate, no restart | Old value |
| `POST /pods/{id}/action` `restart` | `400 There are not enough free vcpu on the host machine to start this pod` — and the Pod was left `EXITED` |
| `start` | The same 400 twice, accepted on the third try a minute later; the new value |
| Clean up | Pod, template and secret deleted at once |

### GPU Pod and container start command (2026-11-27)

A one-off run through REST v2 ([#167](https://github.com/litkhai/runpod-hols/issues/167)); `lab.py` still makes a CPU Pod. RTX 2000 Ada in EU-RO-1 (USD 0.24/hr), `runpod/base:1.0.2-ubuntu2404`, about three minutes of Pod time. The template had `category: NVIDIA` and `cmd: ["bash", "-c", "echo template-cmd … >> /hol-start.txt; exec /start.sh"]`. REST v2 calls the console's *Container start command* (`dockerStartCmd` in v1) `cmd` and `entrypoint`, stored together as `args`. A `cmd` replaces the image's `CMD` — `/start.sh` here, which sets up SSH — so this one ends by running it.

| Step | Result |
|---|---|
| Template, read back | `cmd` as sent; `args` holds it as `{"cmd":[…]}`; `entrypoint` null |
| Pod from the template | Create response and `GET` carry the template's `cmd`; `template` reads back `null`, as on CPU Pods |
| Inside the Pod, SSH after 30 s | `/hol-start.txt` written; PID 1 is `docker-init -- bash -c …`; `sshd` running; `nvidia-smi -L` lists the GPU; secret hash matches; `/etc/rp_environment` still holds it and `RUNPOD_API_KEY`; new names `RUNPOD_GPU_NAME` and `RUNPOD_PROXY_BASE` |
| Rotate, then `restart` | `200`; SSH answered again within 25 s; the new secret value in PID 1; `/hol-start.txt` held only the new start's line — the container was recreated, so files outside volumes were gone |
| Second Pod from the template, with its own `cmd` | The Pod's `cmd` ran, not the template's |
| Clean up | Pods, template and secret deleted at once; USD 0.01 |

`restart` worked on this GPU host. On CPU Pods it had returned 500 (v1) and 400 (v2).

### What was run

2026-11-05, Secure Cloud CPU Pod (`cpu3c`, 2 vCPU), `runpod/base:1.0.2-ubuntu2404`, REST v1 for templates and Pods, REST v2 for secrets.

| Step | Result |
|---|---|
| Secret create (v2) | Created; the response carries id, name, description, createdAt — no value |
| Template create (v1) | `env` holds the reference, not the value |
| Pod from template | `GET /pods` shows the reference, not the value |
| Inside the Pod | PID 1 has the resolved value (hash matches); a non-interactive SSH shell has neither variable |
| `/etc/rp_environment` | Mode 644, resolved secret and `RUNPOD_API_KEY` in plain text |
| Rotate, no restart | Old value |
| `restart` | 500, Pod not restarted |
| `stop` + `start` | New value |
| Clean up | Pod, template and secret deleted at once; `currentSpendPerHr` 0 |

Not run: building a custom image (the template reuses `runpod/base`), a template marked public, a secret used by a Serverless endpoint. A GPU Pod and a start command ran on 2026-11-27, above.

---

## 한국어

**목표:** 일반 환경변수 하나와 Runpod 시크릿에서 읽는 환경변수 하나를 설정하는 Pod 템플릿을 만들고, 그 템플릿으로 Pod 을 띄운 뒤 각 값이 컨테이너 안과 API 에서 어디에 나타나는지 봅니다.

**소요 시간:** 약 15분 · **비용:** CPU Pod 몇 분 (2026-11-05 기준 시간당 $0.06)

### 템플릿에 담기는 것

템플릿은 Pod 의 재사용 가능한 절반입니다. 이미지, 디스크, 포트, 환경변수. Pod 은 여기에 컴퓨트와 위치를 더합니다. 여기서는 REST v2 (`POST /v2/templates`) 로 템플릿을 만듭니다. 필드 이름이 v1 에서 바뀌었고 ([#101](https://github.com/litkhai/runpod-hols/issues/101)), 아래 실행은 v1 로 했습니다.

```json
{
  "name": "hol-pod-03",
  "image": "runpod/base:1.0.2-ubuntu2404",
  "category": "CPU",
  "serverless": false,
  "disk": 10,
  "ports": ["22/tcp"],
  "startSsh": true,
  "startJupyter": false,
  "env": {
    "GREETING": "hello from the template",
    "DEMO_SECRET": "{{ RUNPOD_SECRET_hol_pod_03_demo }}"
  }
}
```

`{{ RUNPOD_SECRET_<name> }}` 은 Pod 이 부팅할 때 시크릿 값으로 바뀝니다 ([Manage secrets](https://docs.runpod.io/pods/templates/secrets)). 시크릿 API 는 REST v2 에만 있습니다. `POST https://api.runpod.io/v2/account/secrets` 가 `name` 과 `value` 를 받고, 값은 쓰기 전용입니다.

### 파일 구성

| 파일 | 역할 |
|---|---|
| `lab.py` | 시크릿 생성·교체·삭제 (REST v2), 템플릿과 Pod 생성·조회·삭제 (REST v1). id 는 `.template.json` 에 기록 |
| `inspect.sh` | Pod 안에서 실행. 일반 값은 그대로, 시크릿은 SHA-256 앞부분이나 길이로만 출력하며 값은 절대 출력하지 않음 |
| `common.py` | `.env` 로딩과 REST 호출. 표준 라이브러리만 사용 |

데모 시크릿은 `lab.py` 가 만드는 임의 문자열입니다. SHA-256 앞 16자리만 출력하므로 Pod 안에서 대조할 수 있습니다.

### 1단계 — 시크릿, 템플릿, Pod

```bash
cd pod/03-custom-template
python3 lab.py secret create     # secret value sha256[:16] = 4958d4cc3a4f7138
python3 lab.py template create
python3 lab.py pod create        # CPU Pod, cpu3c, vCPU 2개
python3 lab.py pod show
```

API 는 값을 보여주지 않습니다. 템플릿에서도, Pod 에서도.

```
env (GET /pods) {"DEMO_SECRET": "{{ RUNPOD_SECRET_hol_pod_03_demo }}", "GREETING": "hello from the template", "PUBLIC_KEY": "ssh-ed25519 …"}
```

### 2단계 — 안을 들여다보기

```bash
ssh root@<ip> -p <port> 'bash -s' < inspect.sh
```

```
GREETING        this shell: <unset>
GREETING        PID 1:      hello from the template
DEMO_SECRET     this shell: <unset>
DEMO_SECRET     PID 1:      sha256[:16] 4958d4cc3a4f7138
RUNPOD_* names, PID 1: RUNPOD_API_KEY RUNPOD_CPU_COUNT RUNPOD_CPU_POD_PODVERSION RUNPOD_DC_ID RUNPOD_GPU_COUNT RUNPOD_MEM_GB RUNPOD_POD_HOSTNAME RUNPOD_POD_ID RUNPOD_PUBLIC_IP RUNPOD_TCP_PORT_22
RUNPOD_API_KEY  PID 1:      present, 50 chars
/etc/rp_environment: 31 lines, mentions GREETING: 1
```

시크릿은 도착했습니다. 해시가 일치합니다. 알아둘 것이 두 가지 있습니다.

**`ssh host 'command'` 는 템플릿 변수를 보지 못합니다.** 변수는 PID 1 의 환경에 있습니다. 이미지의 시작 스크립트가 이를 `/etc/rp_environment` 로 복사하고 `/root/.bashrc` 가 그 파일을 읽으므로 (102번째 줄), 대화형 셸에는 있고 비대화형 명령에는 없습니다. SSH 로 실행하는 스크립트는 먼저 `source /etc/rp_environment` 를 하거나 `/proc/1/environ` 을 읽어야 합니다.

<div class="warn" markdown="1">
**`/etc/rp_environment` 에 치환된 시크릿과 Pod 의 API 키가 평문으로 들어 있습니다.** 이 파일은 컨테이너 디스크 위의 `644` 권한 파일이고, `export DEMO_SECRET=…` (같은 해시) 와 `export RUNPOD_API_KEY=…` 를 담고 있습니다. 시크릿은 값이 템플릿과 API 에 드러나지 않게 해 주지만, Pod 안에서는 평범한 파일입니다. Pod 이 읽을 수 있는 것은 그 Pod 에서 도는 모든 것에 노출된 것으로 보고, Pod 의 호스트가 의심스러우면 교체하세요.
</div>

### 3단계 — 시크릿 교체

```bash
python3 lab.py secret rotate     # secret value sha256[:16] = 5c36d64c0c3f2f37
```

| 교체 후 | PID 1 의 `DEMO_SECRET` |
|---|---|
| 실행 중인 Pod, 재시작 없음 | `4958d4cc3a4f7138` — 이전 값 |
| `POST /pods/{id}/restart` | 실패: `500 … hapi.runpod.net/v1/internal/pod/…/restart: context deadline exceeded`. `lastStartedAt` 변화 없음 |
| `stop` 후 `start` | `5c36d64c0c3f2f37` — 새 값 |

[v2 레퍼런스](https://docs.runpod.io/api-reference-v2/account/update-a-secret) 에 적힌 대로, 교체된 시크릿은 Pod 이 다음에 부팅할 때 반영됩니다.

### 4단계 — 정리

```bash
python3 lab.py pod delete
python3 lab.py template delete
python3 lab.py secret delete
python3 lab.py status            # secrets [], templates [], pods []
```

Pod 템플릿은 바로 지워졌습니다. [Serverless Lab 03](../../serverless/03-vllm-endpoint) 의 Serverless 템플릿은 그렇지 않았습니다. 삭제된 엔드포인트가 최대 약 90분 동안 잡고 있었습니다.

### REST v2 로 재실행 (2026-11-24)

같은 단계를 REST v2 로 ([#123](https://github.com/litkhai/runpod-hols/issues/123)), US-CA-2 의 CPU Pod `cpu3c` 로 약 8분 동안 실행했습니다.

| 단계 | 결과 |
|---|---|
| 시크릿, 템플릿, Pod | 이전과 같음. 템플릿으로 만들었는데도 Pod 을 읽으면 `template: null` |
| Pod 안 | PID 1 에 해석된 시크릿 (해시 일치), 비대화형 SSH 셸에는 두 변수 모두 없음. `/etc/rp_environment` 는 여전히 644 이고 시크릿과 `RUNPOD_API_KEY` 포함. 새로 `RUNPOD_PROXY_BASE` |
| 교체, 재시작 없음 | 이전 값 |
| `POST /pods/{id}/action` `restart` | `400 There are not enough free vcpu on the host machine to start this pod` — 그리고 Pod 이 `EXITED` 로 남음 |
| `start` | 같은 400 두 번, 1분 뒤 세 번째에 성공. 새 값 |
| 정리 | Pod, 템플릿, 시크릿 바로 삭제 |

### GPU Pod 과 컨테이너 시작 명령 (2026-11-27)

REST v2 로 한 번 따로 실행했습니다 ([#167](https://github.com/litkhai/runpod-hols/issues/167)). `lab.py` 는 여전히 CPU Pod 을 만듭니다. EU-RO-1 의 RTX 2000 Ada (시간당 USD 0.24), `runpod/base:1.0.2-ubuntu2404`, Pod 시간 약 3분. 템플릿은 `category: NVIDIA` 에 `cmd: ["bash", "-c", "echo template-cmd … >> /hol-start.txt; exec /start.sh"]` 였습니다. 콘솔의 *Container start command* (v1 의 `dockerStartCmd`) 를 REST v2 는 `cmd` 와 `entrypoint` 로 받고, 둘을 합쳐 `args` 에 저장합니다. `cmd` 는 이미지의 `CMD` 를 대체합니다. 이 이미지의 `CMD` 는 SSH 를 띄우는 `/start.sh` 라서, 명령 끝에서 그것을 실행했습니다.

| 단계 | 결과 |
|---|---|
| 템플릿, 다시 읽기 | `cmd` 는 보낸 그대로. `args` 에 `{"cmd":[…]}` 로 저장. `entrypoint` 는 null |
| 템플릿으로 만든 Pod | 생성 응답과 `GET` 에 템플릿의 `cmd` 가 있음. CPU Pod 때처럼 `template` 은 `null` 로 읽힘 |
| Pod 안, SSH 30초 후 | `/hol-start.txt` 생성. PID 1 은 `docker-init -- bash -c …`. `sshd` 실행 중. `nvidia-smi -L` 에 GPU 가 보임. 시크릿 해시 일치. `/etc/rp_environment` 에 시크릿과 `RUNPOD_API_KEY` 가 여전히 있음. 새 이름 `RUNPOD_GPU_NAME`, `RUNPOD_PROXY_BASE` |
| 교체 후 `restart` | `200`. 25초 안에 SSH 가 다시 응답. PID 1 에 새 시크릿 값. `/hol-start.txt` 에는 새 시작의 줄만 남음 — 컨테이너가 새로 만들어져 볼륨 밖의 파일은 사라짐 |
| 같은 템플릿으로 `cmd` 를 따로 준 두 번째 Pod | 템플릿이 아니라 Pod 의 `cmd` 가 실행됨 |
| 정리 | Pod, 템플릿, 시크릿 즉시 삭제. USD 0.01 |

이 GPU 호스트에서는 `restart` 가 동작했습니다. CPU Pod 에서는 500 (v1) 과 400 (v2) 이었습니다.

### 실행 내역

2026-11-05, Secure Cloud CPU Pod (`cpu3c`, vCPU 2개), `runpod/base:1.0.2-ubuntu2404`, 템플릿과 Pod 은 REST v1, 시크릿은 REST v2.

| 단계 | 결과 |
|---|---|
| 시크릿 생성 (v2) | 생성됨. 응답에는 id, name, description, createdAt 만 있고 값은 없음 |
| 템플릿 생성 (v1) | `env` 에 값이 아닌 참조 |
| 템플릿으로 Pod 생성 | `GET /pods` 에 값이 아닌 참조 |
| Pod 안 | PID 1 에 치환된 값 (해시 일치). 비대화형 SSH 셸에는 두 변수 모두 없음 |
| `/etc/rp_environment` | 권한 644, 치환된 시크릿과 `RUNPOD_API_KEY` 가 평문 |
| 교체, 재시작 없음 | 이전 값 |
| `restart` | 500, Pod 재시작되지 않음 |
| `stop` + `start` | 새 값 |
| 정리 | Pod, 템플릿, 시크릿 모두 바로 삭제. `currentSpendPerHr` 0 |

실행하지 않은 것: 커스텀 이미지 빌드 (템플릿은 `runpod/base` 를 재사용), 공개 템플릿, Serverless 엔드포인트에서의 시크릿 사용. GPU Pod 과 시작 명령은 2026-11-27 에 실행했습니다 (위).
