---
layout: default
title: Setup
permalink: /setup/
---

# Setup

<div class="lang" data-lang="en" markdown="1">

## English

Everything the other tracks assume you have already done.

### Quick start

```bash
./setup/check-setup.sh          # 1. are the tools present?
./setup/init-env.sh             # 2. enter your secrets, writes .env (0600)
python setup/verify-auth.py     # 3. does the key actually work?
```

### API key

Create one at [Console → Settings → API Keys](https://console.runpod.io/user/settings), then run `./setup/init-env.sh`. It reads the key with terminal echo disabled, writes `.env` with `0600` permissions, and prints only a masked confirmation — so the key never reaches your screen or shell history. Re-running is safe: existing values become defaults and the old file is backed up.

<div class="warn" markdown="1">
**Runpod shows the key once and does not store it.** Copy it into a password manager at creation time. If you lose it you cannot recover it — only create a new one.
</div>

Keys carry a permission level, set at creation:

| Level | Meaning |
|---|---|
| **All** | Full access |
| **Restricted** | Per-API access you configure — `None`, `Restricted`, `Read/Write`, `Read Only` |
| **Read Only** | Read access, no writes |

| Task | Level |
|---|---|
| `verify-auth.py`, browsing GPU types and resources | **Read Only** |
| Deploying Lab 01 through the console | No key needed |
| Calling a deployed endpoint | Access to that endpoint |
| `terraform/01-endpoint` | Write access |
| `terraform/02-pod` | **All** |

The documented `Restricted` mode customises access *per Serverless endpoint* and does not clearly cover Pod or Network Volume scope, so `All` is the reliable choice for the Pod lab.

Permissions can be **edited later** from the Settings page — no need to issue a second key. Start Read Only and raise it when you reach the Terraform labs.

<div class="warn" markdown="1">
Rotate a key the moment it lands anywhere public — a commit, a screenshot, a paste in chat. Deleting the commit is not enough; the key must be revoked in the console.

Keys created before **11 November 2024** are legacy: Read/Write or Read Only on GraphQL, but full access to the AI API regardless. Replace them.
</div>

### What `verify-auth.py` does

Three read-only calls: `get_user`, `get_gpus`, `get_pods`. Nothing is created, so nothing is billed. The last one matters most — it lists Pods you already have running, which is how you find one left over from a previous session that is still charging you.

### Tooling by track

| Tool | Needed for | Install |
|---|---|---|
| Python 3.10+ | all | `uv venv --python 3.11` |
| Docker | Serverless | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Terraform 1.6+ | Terraform | `brew install hashicorp/tap/terraform` |
| `runpodctl` | Pod (optional) | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP (optional) | `brew install node` |

<div class="note" markdown="1">
**Two traps on macOS.** The system `python3` is 3.9 and the Runpod SDK requires 3.10+, so use `uv venv --python 3.11`. And Homebrew's `terraform` formula is frozen at 1.5.7, which cannot install the Runpod provider — use the HashiCorp tap instead.
</div>

### Ways to reach Runpod from code

| Path | Best for |
|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | Scripts, and the worker runtime itself |
| [`runpodctl`](https://github.com/runpod/runpodctl) | Quick CLI operations, file transfer |
| [Terraform provider](https://registry.terraform.io/providers/runpod/runpod) | Reproducible infrastructure |
| [MCP server](https://github.com/runpod/runpod-mcp) | Driving Runpod from Claude Code or Cursor |

### MCP — Runpod from an AI agent

The official [MCP server](https://github.com/runpod/runpod-mcp) is the most actively maintained integration in the Runpod org. The hosted mode needs no install and stores no API key on disk:

```bash
claude mcp add --transport http runpod -s user https://mcp.getrunpod.io/
```

<div class="warn" markdown="1">
An agent with a read/write MCP connection can create Pods, and a Pod bills from the moment it starts. Use a read-only key unless the task genuinely needs to provision something.
</div>

[Full details in the repo →](https://github.com/litkhai/runpod-hols/tree/main/setup)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

다른 트랙들이 "이미 했다"고 가정하는 것들입니다.

### 빠른 시작

```bash
./setup/check-setup.sh          # 1. 도구가 갖춰졌는가
./setup/init-env.sh             # 2. 비밀값 입력 → .env 생성 (0600)
python setup/verify-auth.py     # 3. 키가 실제로 동작하는가
```

### API 키

[콘솔 → Settings → API Keys](https://console.runpod.io/user/settings) 에서 생성한 뒤 `./setup/init-env.sh` 를 실행합니다. 터미널 에코를 끈 채 키를 입력받고 `.env` 를 `0600` 권한으로 작성하며 마스킹된 확인값만 출력하므로, 키가 화면에도 셸 히스토리에도 남지 않습니다. 여러 번 실행해도 안전합니다. 기존 값이 기본값으로 제시되고 이전 파일은 백업됩니다.

<div class="warn" markdown="1">
**Runpod 은 키를 한 번만 보여주고 저장하지 않습니다.** 생성 시점에 비밀번호 관리자에 복사해 두세요. 분실하면 복구할 수 없고 새로 만드는 수밖에 없습니다.
</div>

키에는 생성 시 지정하는 권한 등급이 있습니다.

| 등급 | 내용 |
|---|---|
| **All** | 전체 접근 |
| **Restricted** | API 별로 직접 설정 — `None`, `Restricted`, `Read/Write`, `Read Only` |
| **Read Only** | 읽기만, 쓰기 불가 |

| 작업 | 등급 |
|---|---|
| `verify-auth.py`, GPU 타입·리소스 조회 | **Read Only** |
| 콘솔에서 Lab 01 배포 | 키 불필요 |
| 배포한 엔드포인트 호출 | 해당 엔드포인트 접근 권한 |
| `terraform/01-endpoint` | 쓰기 권한 |
| `terraform/02-pod` | **All** |

문서화된 `Restricted` 모드는 *Serverless 엔드포인트 단위*로 접근을 설정하며 Pod 나 Network Volume 범위는 명확히 다루지 않으므로, Pod 실습에는 `All` 이 확실합니다.

권한은 **나중에 수정할 수 있습니다.** Settings 페이지에서 편집하면 되고 두 번째 키를 발급할 필요가 없습니다. Read Only 로 시작해 Terraform 실습에서 올리세요.

<div class="warn" markdown="1">
키가 공개된 곳에 노출되는 즉시 폐기하세요. 커밋, 스크린샷, 채팅 붙여넣기 모두 해당됩니다. 커밋을 지우는 것만으로는 부족하고 콘솔에서 revoke 해야 합니다.

**2024년 11월 11일 이전**에 만든 키는 레거시입니다. GraphQL 에는 Read/Write 또는 Read Only 가 적용되지만 AI API 에는 무조건 전체 접근 권한을 가집니다. 교체하세요.
</div>

### `verify-auth.py` 가 하는 일

읽기 전용 호출 세 건입니다: `get_user`, `get_gpus`, `get_pods`. 생성하는 것이 없어 과금되지 않습니다. 마지막 항목이 가장 중요한데, 현재 실행 중인 Pod 를 나열해 줍니다. 이전 세션에서 끄지 않고 남겨둔, 지금도 과금되고 있는 Pod 를 찾는 방법입니다.

### 트랙별 필요 도구

| 도구 | 필요한 트랙 | 설치 |
|---|---|---|
| Python 3.10+ | 전체 | `uv venv --python 3.11` |
| Docker | Serverless | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Terraform 1.6+ | Terraform | `brew install hashicorp/tap/terraform` |
| `runpodctl` | Pod (선택) | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP (선택) | `brew install node` |

<div class="note" markdown="1">
**macOS 에서 걸리는 두 가지.** 시스템 `python3` 는 3.9 인데 Runpod SDK 는 3.10 이상을 요구하므로 `uv venv --python 3.11` 을 쓰세요. 그리고 Homebrew 의 `terraform` 포뮬러는 1.5.7 에 멈춰 있어 Runpod 프로바이더를 설치할 수 없으므로 HashiCorp tap 을 사용해야 합니다.
</div>

### 코드로 Runpod 에 접근하는 경로

| 경로 | 적합한 용도 |
|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | 스크립트, 그리고 워커 런타임 자체 |
| [`runpodctl`](https://github.com/runpod/runpodctl) | 간단한 CLI 작업, 파일 전송 |
| [Terraform provider](https://registry.terraform.io/providers/runpod/runpod) | 재현 가능한 인프라 |
| [MCP 서버](https://github.com/runpod/runpod-mcp) | Claude Code 나 Cursor 에서 Runpod 조작 |

### MCP — AI 에이전트에서 Runpod 다루기

공식 [MCP 서버](https://github.com/runpod/runpod-mcp) 는 Runpod 조직에서 가장 활발히 관리되는 연동 프로젝트입니다. Hosted 방식은 설치가 필요 없고 디스크에 API 키를 저장하지 않습니다.

```bash
claude mcp add --transport http runpod -s user https://mcp.getrunpod.io/
```

<div class="warn" markdown="1">
읽기/쓰기 권한으로 MCP 가 연결된 에이전트는 Pod 를 생성할 수 있고, Pod 는 기동 시점부터 과금됩니다. 실제로 리소스를 만들어야 하는 작업이 아니라면 읽기 전용 키를 사용하세요.
</div>

[저장소에서 전체 내용 보기 →](https://github.com/litkhai/runpod-hols/tree/main/setup)

</div>
