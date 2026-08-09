# Setup — Prerequisites for Every Track

[English](#english) | [한국어](#한국어)

---

## English

Everything the other tracks assume you have done. Start here.

### Quick Start

```bash
./setup/check-setup.sh          # 1. are the tools present?
cp .env.example .env            # 2. create the env file
#    …fill in RUNPOD_API_KEY…
python setup/verify-auth.py     # 3. does the key actually work?
```

### Files

| File | Role |
|---|---|
| `check-setup.sh` | Checks python / docker / uv / terraform / runpodctl / node, `.env`, and warns about Apple Silicon |
| `verify-auth.py` | Read-only API calls proving the key works: `get_user`, `get_gpus`, `get_pods`. Creates nothing, costs nothing |
| `mcp.md` | Connecting Runpod to Claude Code and other agents via the official MCP server |

### 1. API Key

Issue one at [Console → Settings → API Keys](https://console.runpod.io/user/settings), then:

```bash
cp .env.example .env
```

Fill in `RUNPOD_API_KEY`. `.env` is gitignored — never commit it.

Runpod keys carry a permission level. A **read-only** key is enough to browse GPU types and inspect existing resources; creating endpoints, Pods or volumes needs **read/write**. Start read-only if you are only exploring, and issue a separate read/write key when you reach a lab that provisions something.

> **Rotate a key the moment it lands anywhere public** — a commit, a screenshot, a paste in chat. Deleting the commit is not enough; the key must be revoked in the console.

### 2. Verify

```bash
python setup/verify-auth.py
```

Expected output: your account identity, a count of visible GPU types with a sample, and a list of any Pods you already have running. That last section matters — a Pod left running from an earlier session is billing you right now.

The script needs the `runpod` SDK. If you have not created a virtualenv yet:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python runpod
.venv/bin/python setup/verify-auth.py
```

### 3. Tooling by Track

| Tool | Needed for | Install |
|---|---|---|
| Python 3.10+ | all | `uv venv --python 3.11` (macOS system Python is 3.9 — too old) |
| Docker | `serverless/` | https://docs.docker.com/get-docker/ |
| Terraform | `terraform/` | `brew install terraform` |
| `runpodctl` | `pod/` (optional) | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP server (optional) | `brew install node` |

### 4. Spending Limit

Before the first lab that creates anything, set a spending limit in the console. Pods bill per minute while running; a forgotten one is the most common surprise on a Runpod invoice.

### Ways to Reach Runpod from Code

| Path | Best for | Notes |
|---|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | Scripts, the worker runtime itself | `pip install runpod`, requires 3.10+ |
| [`runpodctl`](https://github.com/runpod/runpodctl) | Quick CLI operations, file transfer | Go binary, Homebrew tap |
| [Terraform provider](https://registry.terraform.io/providers/runpod/runpod) | Reproducible infrastructure | See [`terraform/`](../terraform) |
| [MCP server](https://github.com/runpod/runpod-mcp) | Driving Runpod from Claude Code / Cursor | See [`mcp.md`](./mcp.md) |
| [REST / GraphQL API](https://docs.runpod.io/api-reference) | Anything else | What the SDK wraps |

---

## 한국어

다른 트랙들이 "이미 했다"고 가정하는 것들입니다. 여기서 시작하세요.

### 빠른 시작

```bash
./setup/check-setup.sh          # 1. 도구가 갖춰졌는가
cp .env.example .env            # 2. 환경변수 파일 생성
#    …RUNPOD_API_KEY 채우기…
python setup/verify-auth.py     # 3. 키가 실제로 동작하는가
```

### 파일 구성

| 파일 | 역할 |
|---|---|
| `check-setup.sh` | python / docker / uv / terraform / runpodctl / node 와 `.env` 를 검사하고 Apple Silicon 주의사항을 안내 |
| `verify-auth.py` | 키 동작을 확인하는 읽기 전용 호출: `get_user`, `get_gpus`, `get_pods`. 생성하는 것이 없어 과금되지 않음 |
| `mcp.md` | 공식 MCP 서버로 Runpod 을 Claude Code 등 에이전트에 연결하는 방법 |

### 1. API 키

[콘솔 → Settings → API Keys](https://console.runpod.io/user/settings) 에서 발급한 뒤:

```bash
cp .env.example .env
```

`RUNPOD_API_KEY` 를 채웁니다. `.env` 는 gitignore 돼 있으니 절대 커밋하지 마세요.

Runpod 키에는 권한 등급이 있습니다. GPU 타입 조회나 기존 리소스 확인은 **읽기 전용** 키로 충분하고, 엔드포인트·Pod·볼륨을 생성하려면 **읽기/쓰기** 키가 필요합니다. 둘러보기만 할 때는 읽기 전용으로 시작하고, 리소스를 만드는 실습에 도달했을 때 별도의 읽기/쓰기 키를 발급하는 편이 안전합니다.

> **키가 공개된 곳에 노출되는 즉시 폐기하세요** — 커밋, 스크린샷, 채팅 붙여넣기 모두 해당됩니다. 커밋을 지우는 것만으로는 부족하고 콘솔에서 revoke 해야 합니다.

### 2. 확인

```bash
python setup/verify-auth.py
```

계정 정보, 조회 가능한 GPU 타입 개수와 샘플, 그리고 **현재 실행 중인 Pod 목록**이 출력됩니다. 마지막 항목이 중요합니다. 이전 세션에서 끄지 않고 남겨둔 Pod 가 있다면 지금도 과금되고 있습니다.

이 스크립트는 `runpod` SDK 를 필요로 합니다. 가상환경을 아직 만들지 않았다면:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python runpod
.venv/bin/python setup/verify-auth.py
```

### 3. 트랙별 필요 도구

| 도구 | 필요한 트랙 | 설치 |
|---|---|---|
| Python 3.10+ | 전체 | `uv venv --python 3.11` (macOS 기본 Python 은 3.9 라 부족) |
| Docker | `serverless/` | https://docs.docker.com/get-docker/ |
| Terraform | `terraform/` | `brew install terraform` |
| `runpodctl` | `pod/` (선택) | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP 서버 (선택) | `brew install node` |

### 4. 지출 한도 설정

리소스를 생성하는 첫 실습을 시작하기 전에 콘솔에서 지출 한도(spending limit)를 설정하세요. Pod 는 실행 중인 동안 분 단위로 과금되며, 깜빡하고 켜둔 Pod 가 Runpod 청구서에서 가장 흔한 사고입니다.

### 코드로 Runpod 에 접근하는 경로

| 경로 | 적합한 용도 | 비고 |
|---|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | 스크립트, 워커 런타임 자체 | `pip install runpod`, 3.10 이상 필요 |
| [`runpodctl`](https://github.com/runpod/runpodctl) | 간단한 CLI 작업, 파일 전송 | Go 바이너리, Homebrew tap |
| [Terraform provider](https://registry.terraform.io/providers/runpod/runpod) | 재현 가능한 인프라 | [`terraform/`](../terraform) 참조 |
| [MCP 서버](https://github.com/runpod/runpod-mcp) | Claude Code / Cursor 에서 Runpod 조작 | [`mcp.md`](./mcp.md) 참조 |
| [REST / GraphQL API](https://docs.runpod.io/api-reference) | 그 외 전부 | SDK 가 감싸고 있는 대상 |
