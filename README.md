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
│   ├── 01-hello-worker/ # handler → local test → container → deploy
│   └── 02-llm-chat/     # LLM from GitHub + Runpod cached model
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
| [`serverless/`](./serverless) | ✅ 2 labs ready | Write handler → test locally → containerize → deploy endpoint |
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

### How This Repository Works

Four conventions, each with a reason behind it.

**Everything is verified by running it.** Command output, image sizes, latency figures and error messages in these docs were produced on a real account, not copied from vendor documentation. Where something has *not* been run — `terraform apply`, the Pod track — the page says so explicitly. That distinction is the point: this repo is worth more than the official docs only where it contradicts or completes them, and it can only do that honestly if you can tell verified from assumed.

Several corrections came out of that discipline. Runpod's own `worker-template` README describes a `src/` directory it does not have; the console's Build context field is undocumented; `{"input": {}}` never returns; the SDK's cached-model path disagrees with the docs. None of these are visible from reading alone.

**Labs are self-contained.** Each lab directory holds a `Dockerfile` with bare `COPY` paths, so the folder builds on its own and can be lifted out of this repo unchanged. This mirrors how Runpod structures its own code — `runpod-workers/*` is one repo per worker, and the `runpod/containers` monorepo sets a per-target `context` rather than reaching across directories. The cost is that deploying from a subdirectory needs the console's **Build context** field set; that trade is documented in [`serverless/README.md`](./serverless).

**Docs are bilingual, English first.** Every README and site page carries a full English section and a full Korean one, in the format used by [`clickhouse-hols`](https://github.com/litkhai/clickhouse-hols). Interface text — nav, footer — stays English only; the language toggle governs content, not chrome.

**The top level is flat.** `setup / serverless / pod / cluster / terraform` sit side by side rather than under a `labs/` wrapper, because the repository name already says these are labs.

### The Documentation Site

[`docs/`](./docs) builds to [litkhai.github.io/runpod-hols](https://litkhai.github.io/runpod-hols) through [`.github/workflows/pages.yml`](./.github/workflows/pages.yml) on every push that touches it.

| Choice | Why |
|---|---|
| Jekyll with a hand-written layout, no remote theme | No upstream gem to break, and full control over the bilingual toggle |
| Palette taken from Runpod's own assets | `docs.json` and the logo SVGs, not invented colours |
| Dark by default, light opt-in | A `<head>` guard applies the saved theme before first paint |
| Sidebar contents built in the browser | Each page holds both languages; a server-rendered list would duplicate every heading and half the anchors would point into a hidden block |

To preview locally without installing Ruby:

```bash
docker run --rm -v "$PWD/docs":/site -w /site -p 4000:4000 ruby:3.3   bash -c "gem install jekyll -N && jekyll serve --host 0.0.0.0"
```

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

### 📄 License

[MIT](./LICENSE). Take anything here and use it.

`serverless/01-hello-worker` derives from [`runpod-workers/worker-template`](https://github.com/runpod-workers/worker-template), which is MIT licensed. Its copyright notice travels with this repo in [NOTICE](./NOTICE), as MIT requires — kept out of LICENSE so GitHub still detects the licence as MIT rather than "Other". The Python SDK, container images and Terraform provider this repo builds on are MIT as well.

Not affiliated with, reviewed by, or endorsed by Runpod.

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
│   ├── 01-hello-worker/ # handler 작성 → 로컬 테스트 → 컨테이너화 → 배포
│   └── 02-llm-chat/     # GitHub 연동 LLM + Runpod 모델 캐시
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
| [`serverless/`](./serverless) | ✅ 2개 준비됨 | handler 작성 → 로컬 테스트 → 컨테이너화 → 엔드포인트 배포 |
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

### 이 저장소의 작동 방식

네 가지 관례가 있고, 각각 이유가 있습니다.

**모든 것은 실행해서 검증합니다.** 이 문서들의 명령 출력, 이미지 크기, 지연시간 수치, 오류 메시지는 실제 계정에서 얻은 것이지 벤더 문서를 옮긴 것이 아닙니다. 아직 실행하지 *않은* 것 — `terraform apply`, Pod 트랙 — 은 그렇다고 명시합니다. 이 구분이 핵심입니다. 이 저장소가 공식 문서보다 가치 있는 지점은 공식 문서와 어긋나거나 그것을 보완하는 부분뿐이고, 검증된 것과 가정한 것을 구별할 수 있어야 그 주장이 정직해집니다.

이 원칙에서 여러 수정이 나왔습니다. Runpod 의 `worker-template` README 는 존재하지 않는 `src/` 디렉토리를 설명하고, 콘솔의 Build context 필드는 문서화돼 있지 않으며, `{"input": {}}` 은 응답이 오지 않고, SDK 의 모델 캐시 경로는 문서와 다릅니다. 읽기만 해서는 어느 것도 알 수 없습니다.

**실습은 자체 완결적입니다.** 각 실습 디렉토리는 접두사 없는 `COPY` 경로를 쓰는 `Dockerfile` 을 갖고 있어, 폴더 단독으로 빌드되고 이 저장소 밖으로 그대로 옮겨도 동작합니다. Runpod 이 자기 코드를 구성하는 방식과 같습니다 — `runpod-workers/*` 는 워커마다 저장소를 따로 두고, `runpod/containers` 모노레포는 디렉토리를 가로지르는 대신 타겟마다 `context` 를 지정합니다. 대신 하위 디렉토리에서 배포할 때 콘솔의 **Build context** 필드를 설정해야 하는데, 그 맞바꿈은 [`serverless/README.md`](./serverless) 에 정리돼 있습니다.

**문서는 영문 우선 이중 언어입니다.** 모든 README 와 사이트 페이지가 완전한 영문 절과 완전한 한글 절을 함께 담으며, [`clickhouse-hols`](https://github.com/litkhai/clickhouse-hols) 의 형식을 따릅니다. 인터페이스 텍스트(네비게이션, 푸터)는 영문만 사용합니다. 언어 토글이 관장하는 것은 본문이지 UI 가 아닙니다.

**최상위는 평평합니다.** `setup / serverless / pod / cluster / terraform` 이 `labs/` 같은 상위 폴더 없이 나란히 놓입니다. 저장소 이름이 이미 이것들이 실습임을 말하고 있기 때문입니다.

### 문서 사이트

[`docs/`](./docs) 는 [`.github/workflows/pages.yml`](./.github/workflows/pages.yml) 을 통해 [litkhai.github.io/runpod-hols](https://litkhai.github.io/runpod-hols) 로 빌드되며, 해당 디렉토리를 건드리는 푸시마다 배포됩니다.

| 선택 | 이유 |
|---|---|
| 원격 테마 없이 직접 작성한 Jekyll 레이아웃 | 깨질 외부 gem 이 없고 이중 언어 토글을 완전히 제어 |
| Runpod 공식 자산에서 가져온 색상 | 임의로 고른 색이 아니라 `docs.json` 과 로고 SVG 기준 |
| 기본 다크, 라이트는 선택 | `<head>` 가드가 첫 페인트 전에 저장된 테마를 적용 |
| 사이드바 목차를 브라우저에서 생성 | 각 페이지가 두 언어를 담고 있어, 서버에서 만들면 제목이 두 배가 되고 앵커 절반이 숨겨진 블록을 가리킴 |

Ruby 를 설치하지 않고 로컬에서 미리 보려면:

```bash
docker run --rm -v "$PWD/docs":/site -w /site -p 4000:4000 ruby:3.3 \
  bash -c "gem install jekyll -N && jekyll serve --host 0.0.0.0"
```

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

### 📄 라이선스

[MIT](./LICENSE). 여기 있는 것은 무엇이든 가져다 쓰셔도 됩니다.

`serverless/01-hello-worker` 는 MIT 라이선스인 [`runpod-workers/worker-template`](https://github.com/runpod-workers/worker-template) 에서 파생됐습니다. MIT 가 요구하는 원본 저작권 표시는 [NOTICE](./NOTICE) 에 함께 담았습니다. LICENSE 에 덧붙이지 않은 이유는, 그러면 GitHub 이 라이선스를 MIT 가 아니라 "Other" 로 인식하기 때문입니다. 이 저장소가 기반으로 삼는 Python SDK, 컨테이너 이미지, Terraform 프로바이더도 모두 MIT 입니다.

Runpod 과 제휴 관계가 없으며, Runpod 의 검토나 승인을 받지 않았습니다.

### 🙏 감사의 말

이 실습 자료는 Runpod 의 **Kenny Lee** ([kenny.lee@runpod.io](mailto:kenny.lee@runpod.io)) 님의 기회 제공과 **Hailong Yang** 님의 기술 소개를 기반으로 만들어졌습니다. 두 분께 감사드립니다.
