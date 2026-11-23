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

Create one at [Console → Credentials → API Keys](https://console.runpod.io/user/credentials?tab=api-keys), then:

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
| Terraform 1.6+ | `terraform/` | `brew install hashicorp/tap/terraform` — the core formula is frozen at 1.5.7, which cannot install the Runpod provider |
| `runpodctl` | `pod/` (optional) | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP server (optional) | `brew install node` |

### 4. Spending Limit

Before the first lab that creates anything, set a spending limit in the console. Pods bill per minute while running; a forgotten one is the most common surprise on a Runpod invoice.

### Checking the account from the API

These REST v2 reads answer "is anything billing, and what is the account allowed to do" without the console or GraphQL. Read on 2026-11-24 with the lab key ([#105](https://github.com/litkhai/runpod-hols/issues/105)).

| Call | Scope | Returns |
|---|---|---|
| `GET /v2/account/limits` | `account:read` | `spendRate: {current, limit}` in USD per hour, and `serverlessWorkers.limit` (here: spend limit 80, worker limit 30). `spendRate.current` is the REST form of GraphQL `currentSpendPerHr` — 0 means nothing is billing |
| `GET /v2/billing/balance` | `billing:read` | `balanceAmount` and `billingMode` (`PREPAID` here) |
| `GET /v2/audit-logs` | `audit:read` | Who did what to which resource, newest first: `actorId`, `email`, `action`, `resourceType`, `resourceId`, `timestamp`, `value`. Filter with `actions`, `actorIds`, `startTime`, `endTime`, `search`; `limit` is at most 200 (1000 is a 422). This account had 349 entries back to 2026-09-28, mostly API key, Pod, endpoint and template create/delete. Creating a key logs its scopes and policy |
| `GET /v2/cost-centers` | `billing:read` | Cost centers (none here) |
| `GET /v2/tags` | `tags:read` | 403 *Resource tagging is not enabled for this user* — gated per account, not by the key |
| `GET /v2/catalog/gpus?include=AVAILABILITY&product=POD` | `catalog:read` | 46 GPU types with community, secure and serverless prices and stock (`NONE`, `LOW`, `MEDIUM`, `HIGH`). `include=AVAILABILITY` without `product` is a 400: stock differs between `POD` and `SERVERLESS` (31 vs 22 types at `NONE`) |
| `GET /v2/catalog/cpus` | `catalog:read` | CPU flavors (`cpu3c`, `cpu5g`, …) with vCPU range, RAM per vCPU and per-vCPU price |
| `GET /v2/catalog/datacenters` | `catalog:read` | 35 data centers with region, compliance, volume tiers and global networking; `include=GPU_AVAILABILITY` adds stock per GPU |
| `GET /v2/catalog/templates?source=` | `catalog:read` | Public templates: `official` (14), `verified` (3), `community` (100 on the first page); `…/{id}/readme` returns the README as text |

Stock is a snapshot, not a promise; the Pod labs record what create calls actually got.

### Ways to Reach Runpod from Code

| Path | Best for | Notes |
|---|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | Scripts, and the worker runtime itself | `pip install runpod`, requires 3.10+. See [`sdk/`](../sdk) — the [worker](../sdk/worker.md) and [client](../sdk/client.md) halves |
| [`runpodctl`](https://github.com/runpod/runpodctl) | Quick CLI operations, file transfer | Go binary, Homebrew tap. Not the same as the `runpod` CLI the SDK installs |
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

[콘솔 → Credentials → API Keys](https://console.runpod.io/user/credentials?tab=api-keys) 에서 생성한 뒤:

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
| Terraform 1.6+ | `terraform/` | `brew install hashicorp/tap/terraform` — core 포뮬러는 1.5.7 에 멈춰 있어 Runpod 프로바이더를 설치할 수 없음 |
| `runpodctl` | `pod/` (선택) | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP 서버 (선택) | `brew install node` |

### 4. 지출 한도 설정

리소스를 생성하는 첫 실습을 시작하기 전에 콘솔에서 지출 한도(spending limit)를 설정하세요. Pod 는 실행 중인 동안 분 단위로 과금되며, 깜빡하고 켜둔 Pod 가 Runpod 청구서에서 가장 흔한 사고입니다.

### API 로 계정 상태 확인하기

"지금 과금되는 것이 있는가, 계정이 무엇을 할 수 있는가" 를 콘솔이나 GraphQL 없이 REST v2 조회로 확인합니다. 2026-11-24 에 실습용 키로 조회했습니다 ([#105](https://github.com/litkhai/runpod-hols/issues/105)).

| 호출 | 범위 | 돌려주는 것 |
|---|---|---|
| `GET /v2/account/limits` | `account:read` | 시간당 USD 기준 `spendRate: {current, limit}` 와 `serverlessWorkers.limit` (여기서는 지출 한도 80, 워커 한도 30). `spendRate.current` 는 GraphQL `currentSpendPerHr` 의 REST 판이며, 0 이면 과금 중인 것이 없음 |
| `GET /v2/billing/balance` | `billing:read` | `balanceAmount` 와 `billingMode` (여기서는 `PREPAID`) |
| `GET /v2/audit-logs` | `audit:read` | 누가 어떤 리소스에 무엇을 했는지, 최신순: `actorId`, `email`, `action`, `resourceType`, `resourceId`, `timestamp`, `value`. `actions`, `actorIds`, `startTime`, `endTime`, `search` 로 거를 수 있고 `limit` 은 최대 200 (1000 은 422). 이 계정은 2026-09-28 부터 349건이었고 대부분 API 키·Pod·엔드포인트·템플릿의 생성·삭제. 키를 만들면 그 범위와 정책이 기록됨 |
| `GET /v2/cost-centers` | `billing:read` | 비용 센터 (여기서는 없음) |
| `GET /v2/tags` | `tags:read` | 403 *Resource tagging is not enabled for this user*. 키가 아니라 계정 단위로 막혀 있음 |
| `GET /v2/catalog/gpus?include=AVAILABILITY&product=POD` | `catalog:read` | GPU 46종의 community·secure·serverless 가격과 재고 (`NONE`, `LOW`, `MEDIUM`, `HIGH`). `product` 없이 `include=AVAILABILITY` 는 400. 재고는 `POD` 와 `SERVERLESS` 가 다름 (`NONE` 이 31 대 22) |
| `GET /v2/catalog/cpus` | `catalog:read` | CPU 종류 (`cpu3c`, `cpu5g`, …) 의 vCPU 범위, vCPU 당 RAM, vCPU 당 가격 |
| `GET /v2/catalog/datacenters` | `catalog:read` | 데이터센터 35곳의 지역, 컴플라이언스, 볼륨 계층, 글로벌 네트워킹. `include=GPU_AVAILABILITY` 를 주면 GPU 별 재고 추가 |
| `GET /v2/catalog/templates?source=` | `catalog:read` | 공개 템플릿: `official` (14), `verified` (3), `community` (첫 페이지 100). `…/{id}/readme` 는 README 를 텍스트로 돌려줌 |

재고는 그 순간의 값이지 보장이 아닙니다. 생성 호출이 실제로 무엇을 받았는지는 Pod 실습에 기록합니다.

### 코드로 Runpod 에 접근하는 경로

| 경로 | 적합한 용도 | 비고 |
|---|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | 스크립트, 그리고 워커 런타임 자체 | `pip install runpod`, 3.10 이상 필요. [`sdk/`](../sdk) 의 [worker](../sdk/worker.md) · [client](../sdk/client.md) 참조 |
| [`runpodctl`](https://github.com/runpod/runpodctl) | 간단한 CLI 작업, 파일 전송 | Go 바이너리, Homebrew tap. SDK 가 설치하는 `runpod` CLI 와 다른 도구 |
| [Terraform provider](https://registry.terraform.io/providers/runpod/runpod) | 재현 가능한 인프라 | [`terraform/`](../terraform) 참조 |
| [MCP 서버](https://github.com/runpod/runpod-mcp) | Claude Code / Cursor 에서 Runpod 조작 | [`mcp.md`](./mcp.md) 참조 |
| [REST / GraphQL API](https://docs.runpod.io/api-reference) | 그 외 전부 | SDK 가 감싸고 있는 대상 |
