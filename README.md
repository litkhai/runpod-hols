# Runpod Hands-On Labs (HOLs)

**📖 [litkhai.github.io/runpod-hols](https://litkhai.github.io/runpod-hols)**

[English](#english) | [한국어](#한국어)

---

## English

A collection of practical, hands-on laboratory exercises for learning [Runpod](https://runpod.io) — the GPU cloud platform for AI/ML workloads.

Everything here was verified by actually running it. The outputs, image sizes and error messages in these docs are real, not transcribed from vendor documentation.

### 🎯 Purpose

These labs cover Runpod's three compute products, plus the two things you need around them:

- **Setup** — API keys, tooling, auth verification, MCP
- **Serverless** — autoscaling inference endpoints, billed per execution
- **Pods** — GPU containers you rent and control, billed per minute
- **Terraform** — the same resources as infrastructure as code
- **Instant Clusters** — multi-node distributed training (TBD)

### 📁 Repository Structure

```
runpod-hols/
├── setup/               # ← Start here: keys, tools, auth check, MCP
├── serverless/          # Autoscaling inference endpoints
│   └── 01-hello-worker/ # handler → local test → container → deploy
├── terraform/           # Infrastructure as code
│   ├── 01-endpoint/     # runpod_template + runpod_endpoint
│   └── 02-pod/          # runpod_pod + optional network volume
├── pod/                 # GPU containers (SSH / Jupyter)
├── cluster/             # Multi-node distributed training — TBD
└── docs/                # GitHub Pages source
```

| Track | Status | Contents |
|---|---|---|
| [`setup/`](./setup) | ✅ Ready | API key, tool checks, auth smoke test, MCP server |
| [`serverless/`](./serverless) | ✅ Lab 01 ready | Write handler → test locally → containerize → deploy endpoint |
| [`terraform/`](./terraform) | ✅ 2 labs ready | Provision endpoint and Pod declaratively |
| [`pod/`](./pod) | 📋 Planned | Launch Pod → connect → storage → custom template |
| [`cluster/`](./cluster) | 🚧 TBD | Multi-node PyTorch / Slurm / Axolotl |

### Comparing the Three Products

| | Serverless | Pod | Instant Cluster |
|---|---|---|---|
| Form | Autoscaling worker endpoint | A single GPU container | 2–8 nodes (16–64 GPUs) |
| Requires | `handler.py` + image | Nothing (launch from console) | Distributed training script |
| Access | HTTP API | SSH / Jupyter / VS Code | SSH (per node) |
| Billing | Only while executing | Continuously while running | Cluster lease time |
| State | None (reset per request) | Persistent (`/workspace`) | Persistent |
| Use for | Inference serving | Development · fine-tuning | Large-scale distributed training |

The key difference is **state persistence**. A Pod keeps `/workspace` across stop/start, so you can reuse models and datasets. Serverless gives you a fresh container per request, so anything heavy must be baked into the image or attached via a Network Volume.

### Prerequisites

| Item | Required | Check |
|---|---|---|
| Python | **3.10+** | `python3 --version` |
| Docker | latest | `docker --version` |
| uv (recommended) | latest | `uv --version` |
| Runpod account | — | https://console.runpod.io |

> **macOS caution — system Python:** the built-in `python3` on macOS is 3.9, and the Runpod SDK 1.11 declares `requires-python >=3.10`, so it will not install. Use `uv venv --python 3.11`, which downloads 3.11 automatically. Do not use the system Python directly.

> **Apple Silicon caution — image architecture:** Runpod workers run on `linux/amd64`. When building on an arm64 Mac you must pass `--platform linux/amd64`, otherwise the endpoint fails to start.

#### API key

```bash
./setup/init-env.sh
```

Create a key at [Console → Settings → API Keys](https://console.runpod.io/user/settings), then run the script above. It reads the key with terminal echo disabled and writes `.env` with `0600` permissions, so the key never reaches your screen or shell history. (`cp .env.example .env` and editing by hand works too.)

You can complete the console-only parts of the labs without a key, but calling endpoints from the SDK or CLI requires one. Runpod shows the key only once — save it in a password manager. See [`setup/README.md`](./setup) for permission levels.

### 💸 Cost Warning

- **A Pod is billed the entire time it is running, even when idle.** Always **Stop** or **Terminate** when you finish. Stopping still incurs volume storage charges, so Terminate any Pod you will not reuse.
- **Serverless costs nothing when there are no requests.** But setting Active Workers above 0 bills continuously — keep it at 0 for these labs.
- Check current rates at [Pods pricing](https://docs.runpod.io/pods/pricing) and [Serverless pricing](https://docs.runpod.io/serverless/pricing).

### Referenced Official Runpod Resources

Each track README contains a detailed review of the sources it draws on.

| Resource | Used for |
|---|---|
| [runpod-workers/worker-template](https://github.com/runpod-workers/worker-template) | Serverless worker scaffold (the basis for Lab 01) |
| [runpod/runpod-python](https://github.com/runpod/runpod-python) | Python SDK — worker runtime + API client |
| [runpod/containers](https://github.com/runpod/containers) | Official base images (`runpod/base`, `pytorch`, …) |
| [runpod/docs](https://github.com/runpod/docs) | Documentation source → https://docs.runpod.io |
| [runpod/runpodctl](https://github.com/runpod/runpodctl) | CLI |
| [runpod-workers/*](https://github.com/orgs/runpod-workers/repositories) | Production worker examples (vLLM, ComfyUI, Whisper, …) |

### Getting Started

```bash
cd serverless/01-hello-worker
```

Follow [serverless/01-hello-worker/README.md](./serverless/01-hello-worker/README.md).

### 🙏 Acknowledgements

These labs grew out of an opportunity provided by **Kenny Lee** ([kenny.lee@runpod.io](mailto:kenny.lee@runpod.io)) and a technical introduction from **Hailong Yang**, both at Runpod. Special thanks to them.

---

## 한국어

[Runpod](https://runpod.io) — AI/ML 워크로드를 위한 GPU 클라우드 플랫폼 — 학습을 위한 실무 중심 실습(Hands-On Labs) 모음입니다.

여기 있는 내용은 전부 실제로 실행해서 확인한 것입니다. 문서에 나오는 출력, 이미지 크기, 오류 메시지는 벤더 문서를 옮긴 것이 아니라 직접 얻은 결과입니다.

### 🎯 목적

Runpod 의 세 가지 컴퓨트 제품과, 그 주변에 필요한 두 가지를 다룹니다.

- **Setup** — API 키, 도구, 인증 확인, MCP
- **Serverless** — 오토스케일 추론 엔드포인트, 실행된 시간만큼 과금
- **Pods** — 직접 빌려서 제어하는 GPU 컨테이너, 분 단위 과금
- **Terraform** — 같은 리소스를 코드형 인프라로
- **Instant Clusters** — 다중 노드 분산 학습 (TBD)

### 📁 저장소 구조

```
runpod-hols/
├── setup/               # ← 여기서 시작: 키, 도구, 인증 확인, MCP
├── serverless/          # 오토스케일 추론 엔드포인트
│   └── 01-hello-worker/ # handler 작성 → 로컬 테스트 → 컨테이너화 → 배포
├── terraform/           # 코드형 인프라
│   ├── 01-endpoint/     # runpod_template + runpod_endpoint
│   └── 02-pod/          # runpod_pod + 선택적 network volume
├── pod/                 # GPU 컨테이너 (SSH / Jupyter)
├── cluster/             # 다중 노드 분산 학습 — TBD
└── docs/                # GitHub Pages 소스
```

| 트랙 | 상태 | 내용 |
|---|---|---|
| [`setup/`](./setup) | ✅ 준비됨 | API 키, 도구 검사, 인증 스모크 테스트, MCP 서버 |
| [`serverless/`](./serverless) | ✅ Lab 01 준비됨 | handler 작성 → 로컬 테스트 → 컨테이너화 → 엔드포인트 배포 |
| [`terraform/`](./terraform) | ✅ 2개 준비됨 | 엔드포인트와 Pod 를 선언적으로 프로비저닝 |
| [`pod/`](./pod) | 📋 계획됨 | Pod 기동 → 접속 → 스토리지 → 커스텀 템플릿 |
| [`cluster/`](./cluster) | 🚧 TBD | 다중 노드 PyTorch / Slurm / Axolotl |

### 세 제품의 차이

| | Serverless | Pod | Instant Cluster |
|---|---|---|---|
| 형태 | 오토스케일 워커 엔드포인트 | GPU 컨테이너 1대 | 2~8 노드 (16~64 GPU) |
| 필요한 것 | `handler.py` + 이미지 | 없음 (콘솔에서 기동) | 분산 학습 스크립트 |
| 접속 | HTTP API | SSH / Jupyter / VS Code | SSH (노드별) |
| 과금 | 실행된 시간만 | 켜져 있는 동안 계속 | 클러스터 임대 시간 |
| 상태 유지 | 없음 (요청마다 초기화) | 있음 (`/workspace`) | 있음 |
| 쓰는 때 | 추론 서빙 | 개발 · 파인튜닝 | 대규모 분산 학습 |

가장 중요한 차이는 **상태 유지**입니다. Pod 는 껐다 켜도 `/workspace` 가 남아서 모델과 데이터셋을 재사용할 수 있지만, Serverless 는 요청마다 새 컨테이너이므로 무거운 것은 이미지에 미리 굽거나 Network Volume 에 붙여야 합니다.

### 사전 준비

| 항목 | 필요 버전 | 확인 방법 |
|---|---|---|
| Python | **3.10 이상** | `python3 --version` |
| Docker | 최신 | `docker --version` |
| uv (권장) | 최신 | `uv --version` |
| Runpod 계정 | — | https://console.runpod.io |

> **macOS 주의 — 시스템 Python:** macOS 기본 `python3` 는 3.9 이고 Runpod SDK 1.11 은 `requires-python >=3.10` 이라 설치되지 않습니다. `uv venv --python 3.11` 을 쓰면 uv 가 3.11 을 자동으로 받아옵니다. 시스템 python 을 직접 쓰지 마세요.

> **Apple Silicon 주의 — 이미지 아키텍처:** Runpod 워커는 `linux/amd64` 에서 동작합니다. arm64 Mac 에서 빌드할 때는 반드시 `--platform linux/amd64` 를 붙여야 하며, 빠뜨리면 엔드포인트가 기동에 실패합니다.

#### API 키

```bash
./setup/init-env.sh
```

[콘솔 → Settings → API Keys](https://console.runpod.io/user/settings) 에서 키를 생성한 뒤 위 스크립트를 실행하세요. 터미널 에코를 끈 채 키를 입력받아 `.env` 를 `0600` 권한으로 작성하므로, 키가 화면에도 셸 히스토리에도 남지 않습니다. (`cp .env.example .env` 후 직접 편집해도 됩니다.)

콘솔 UI 로만 진행하는 부분은 키 없이도 되지만, SDK 나 CLI 로 엔드포인트를 호출하려면 필요합니다. Runpod 은 키를 한 번만 보여주므로 비밀번호 관리자에 저장해 두세요. 권한 등급은 [`setup/README.md`](./setup) 를 참조하세요.

### 💸 비용 주의

- **Pod 는 idle 상태여도 켜져 있는 내내 과금됩니다.** 실습이 끝나면 반드시 **Stop** 또는 **Terminate** 하세요. Stop 만 하면 Volume 스토리지 요금은 계속 나가므로, 다시 쓰지 않을 Pod 는 Terminate 가 맞습니다.
- **Serverless 는 요청이 없으면 비용이 발생하지 않습니다.** 다만 Active Worker 를 1 이상으로 두면 상시 과금되므로 실습에서는 0 으로 둡니다.
- 실제 단가는 [Pods pricing](https://docs.runpod.io/pods/pricing) 과 [Serverless pricing](https://docs.runpod.io/serverless/pricing) 에서 확인하세요.

### 참조한 Runpod 공식 리소스

각 트랙 README 에 상세 검토 내용이 있습니다.

| 리소스 | 용도 |
|---|---|
| [runpod-workers/worker-template](https://github.com/runpod-workers/worker-template) | Serverless 워커 스캐폴드 (Lab 01 의 원본) |
| [runpod/runpod-python](https://github.com/runpod/runpod-python) | Python SDK — 워커 런타임 + API 클라이언트 |
| [runpod/containers](https://github.com/runpod/containers) | 공식 베이스 이미지 (`runpod/base`, `pytorch` 등) |
| [runpod/docs](https://github.com/runpod/docs) | 문서 원본 → https://docs.runpod.io |
| [runpod/runpodctl](https://github.com/runpod/runpodctl) | CLI |
| [runpod-workers/*](https://github.com/orgs/runpod-workers/repositories) | 실전 워커 예제 (vLLM, ComfyUI, Whisper 등) |

### 시작하기

```bash
cd serverless/01-hello-worker
```

[serverless/01-hello-worker/README.md](./serverless/01-hello-worker/README.md) 를 따라가세요.

### 🙏 감사의 말

이 실습 자료는 Runpod 의 **Kenny Lee** ([kenny.lee@runpod.io](mailto:kenny.lee@runpod.io)) 님의 기회 제공과 **Hailong Yang** 님의 기술 소개를 기반으로 만들어졌습니다. 두 분께 감사드립니다.
