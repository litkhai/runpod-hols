# Setup — Prerequisites for Every Track

[English](#english) | [한국어](#한국어)

---

## English

Everything the other tracks assume you have done. Start here.

### Quick Start

```bash
./setup/check-setup.sh          # 1. are the tools present?
./setup/init-env.sh             # 2. enter your secrets, writes .env (0600)
python setup/verify-auth.py     # 3. does the key actually work?
```

### Files

| File | Role |
|---|---|
| `check-setup.sh` | Checks python / docker / uv / terraform / runpodctl / node, `.env`, and warns about Apple Silicon |
| `init-env.sh` | Prompts for secrets and writes `.env`. Input is hidden, so the key never reaches your screen or shell history |
| `verify-auth.py` | Read-only API calls proving the key works: `get_user`, `get_gpus`, `get_pods`. Creates nothing, costs nothing |
| `mcp.md` | Connecting Runpod to Claude Code and other agents via the official MCP server |

### 1. API Key

Create one at [Console → Settings → API Keys](https://console.runpod.io/user/settings), then:

```bash
./setup/init-env.sh
```

The script reads the key with terminal echo disabled, writes `.env` with `0600` permissions, and prints only a masked confirmation (`••••••••1234`). Re-running it is safe — existing values are offered as defaults and the previous file is backed up to `.env.bak`.

If you would rather do it by hand, `cp .env.example .env` and edit. Either way `.env` is gitignored — never commit it.

> **Runpod shows the key once and does not store it.** Copy it into a password manager at creation time. If you lose it you cannot recover it — you can only create a new one.

Keys carry a permission level, set at creation:

| Level | Meaning |
|---|---|
| **All** | Full access |
| **Restricted** | Per-API access you configure — `None`, `Restricted`, `Read/Write`, or `Read Only` |
| **Read Only** | Read access, no writes |

What each track needs:

| Task | Level |
|---|---|
| `verify-auth.py`, browsing GPU types and existing resources | **Read Only** |
| Deploying Lab 01 through the console | No key needed |
| Calling a deployed endpoint | Access to that endpoint |
| `terraform/01-endpoint` — creating a template and endpoint | Write access |
| `terraform/02-pod` — creating a Pod and volume | **All** |

That last row is deliberately blunt: the documented `Restricted` mode customises access *per Serverless endpoint*, and does not clearly describe Pod or Network Volume scope. `All` is the reliable choice there.

You can **edit a key's permissions later** with the pencil icon on the Settings page — no need to issue a second key. So starting Read Only and raising it when you reach the Terraform labs works fine.

> **Rotate a key the moment it lands anywhere public** — a commit, a screenshot, a paste in chat. Deleting the commit is not enough; the key must be revoked in the console.

> Keys created before **11 November 2024** are legacy: they have Read/Write or Read Only on GraphQL, but **full access to the AI API** regardless. Replace them with a `Restricted` key scoped to what you actually need.

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
./setup/init-env.sh             # 2. 비밀값 입력 → .env 생성 (0600)
python setup/verify-auth.py     # 3. 키가 실제로 동작하는가
```

### 파일 구성

| 파일 | 역할 |
|---|---|
| `check-setup.sh` | python / docker / uv / terraform / runpodctl / node 와 `.env` 를 검사하고 Apple Silicon 주의사항을 안내 |
| `init-env.sh` | 비밀값을 입력받아 `.env` 를 생성. 입력이 화면에 표시되지 않아 키가 화면에도 셸 히스토리에도 남지 않음 |
| `verify-auth.py` | 키 동작을 확인하는 읽기 전용 호출: `get_user`, `get_gpus`, `get_pods`. 생성하는 것이 없어 과금되지 않음 |
| `mcp.md` | 공식 MCP 서버로 Runpod 을 Claude Code 등 에이전트에 연결하는 방법 |

### 1. API 키

[콘솔 → Settings → API Keys](https://console.runpod.io/user/settings) 에서 생성한 뒤:

```bash
./setup/init-env.sh
```

이 스크립트는 터미널 에코를 끈 채로 키를 입력받고, `.env` 를 `0600` 권한으로 작성하며, 확인용으로 마스킹된 값(`••••••••1234`)만 출력합니다. 여러 번 실행해도 안전합니다. 기존 값을 기본값으로 제시하고 이전 파일은 `.env.bak` 으로 백업합니다.

직접 작성하고 싶다면 `cp .env.example .env` 후 편집해도 됩니다. 어느 쪽이든 `.env` 는 gitignore 돼 있으니 절대 커밋하지 마세요.

> **Runpod 은 키를 한 번만 보여주고 저장하지 않습니다.** 생성 시점에 비밀번호 관리자에 복사해 두세요. 분실하면 복구할 수 없고 새로 만드는 수밖에 없습니다.

키에는 생성 시 지정하는 권한 등급이 있습니다.

| 등급 | 내용 |
|---|---|
| **All** | 전체 접근 |
| **Restricted** | API 별로 직접 설정 — `None`, `Restricted`, `Read/Write`, `Read Only` |
| **Read Only** | 읽기만, 쓰기 불가 |

트랙별로 필요한 수준입니다.

| 작업 | 등급 |
|---|---|
| `verify-auth.py`, GPU 타입·기존 리소스 조회 | **Read Only** |
| 콘솔에서 Lab 01 배포 | 키 불필요 |
| 배포한 엔드포인트 호출 | 해당 엔드포인트 접근 권한 |
| `terraform/01-endpoint` — 템플릿·엔드포인트 생성 | 쓰기 권한 |
| `terraform/02-pod` — Pod·볼륨 생성 | **All** |

마지막 행은 일부러 단정적으로 적었습니다. 문서화된 `Restricted` 모드는 *Serverless 엔드포인트 단위*로 접근을 설정하며, Pod 나 Network Volume 범위에 대해서는 명확히 기술하지 않습니다. 이 경우 `All` 이 확실한 선택입니다.

**권한은 나중에 수정할 수 있습니다.** Settings 페이지의 연필 아이콘으로 편집하면 되고 두 번째 키를 발급할 필요가 없습니다. Read Only 로 시작해 Terraform 실습에 도달했을 때 올리는 방식이 잘 동작합니다.

> **키가 공개된 곳에 노출되는 즉시 폐기하세요** — 커밋, 스크린샷, 채팅 붙여넣기 모두 해당됩니다. 커밋을 지우는 것만으로는 부족하고 콘솔에서 revoke 해야 합니다.

> **2024년 11월 11일 이전**에 만든 키는 레거시입니다. GraphQL 에는 Read/Write 또는 Read Only 가 적용되지만 **AI API 에는 무조건 전체 접근** 권한을 가집니다. 실제로 필요한 범위로 좁힌 `Restricted` 키로 교체하세요.

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
