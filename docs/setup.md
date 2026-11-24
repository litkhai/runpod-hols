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

Create one at [Console → Credentials → API Keys](https://console.runpod.io/user/credentials?tab=api-keys), then run `./setup/init-env.sh`. It reads the key with terminal echo disabled, writes `.env` with `0600` permissions, and prints only a masked confirmation — so the key never reaches your screen or shell history. Re-running is safe: existing values become defaults and the old file is backed up.

<div class="warn" markdown="1">
**Runpod shows the key once and does not store it.** Copy it into a password manager at creation time. If you lose it you cannot recover it — only create a new one.
</div>

Each key carries scopes per API, set at creation and editable later from the key's menu (**Edit**):

| API | Choices |
|---|---|
| REST (`api.runpod.io/v2`) | Read and Write per resource — Pods, Serverless, Instant clusters, Volumes, Templates, Secrets, Authentication, Billing, Tags; Read only for Audit logs, Catalog, Account. *All resources* ticks every row |
| GraphQL (`api.runpod.io/graphql`) | None, Read / Write, Read only |
| Serverless endpoints (`api.runpod.ai`) | Read, Write, optionally limited to chosen endpoints |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}" alt="Create API key, REST API section: Write on Pods, Serverless, Instant clusters, Volumes, Templates and Secrets; Authentication off; Audit logs read" loading="lazy" width="1400" height="729"></a><figcaption>Create API key, 2026-11-24: the lab key below. Write on what the labs create, Authentication left off.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}" alt="Lower half of the dialog: Billing, Catalog, Tags and Account read; GraphQL API collapsed at None; api.runpod.ai Read and Write" loading="lazy" width="1400" height="729"></a><figcaption>The rest of the same key: Billing, Catalog, Tags and Account read-only, GraphQL None, <code>api.runpod.ai</code> Read and Write.</figcaption></figure>

**Out-of-scope calls are refused.** On 2026-11-24 a key holding only REST Serverless Read got 200 from `GET /v2/serverless` and 403 with the missing scope named — *this API key does not grant pods:read* — from `GET /v2/pods`, the catalog, billing, audit-log and account reads, `PATCH /v2/serverless/{id}` (`serverless:write`) and `POST /v2/tags`. GraphQL answered 401 and `api.runpod.ai/v2/<id>/health` 403.

What the labs need:

| Task | Scopes |
|---|---|
| `verify-auth.py` | REST Account, Catalog, Pods, Serverless — Read |
| Deploying Lab 01 through the console | No key needed |
| Calling a deployed endpoint | Serverless endpoints Read and Write, or only that endpoint |
| Pod, Serverless, storage and cluster labs on REST | REST Write on Pods, Serverless, Instant clusters, Volumes, Templates, Secrets; Read on Audit logs, Billing, Catalog, Tags, Account; Serverless endpoints Read and Write — the key above |
| `pod/01` (SDK 1.12), cluster stage 2, the stock snapshots in `inference-characterization` | Add GraphQL Read / Write; these still call GraphQL |
| `terraform/` | Not yet checked with a scoped key |

The lab key leaves GraphQL at None on purpose: a GraphQL grant has no per-resource split. Two 403s are not about the key — `GET /v2/tags` answered *Resource tagging is not enabled for this user* with Tags Read granted, and `GET /v2/organization` needs `membership:read`, which this personal account's dialog does not list.

**Exec and logs need GraphQL.** `POST /v2/pods/{id}/exec` needs GraphQL Read / Write on the key; Pod and worker logs need GraphQL Read only ([#112](https://github.com/litkhai/runpod-hols/issues/112), [#104](https://github.com/litkhai/runpod-hols/issues/104)). The lab key keeps GraphQL at None: create a short-lived key for those calls and delete it after.

**Keys now expire.** Since about 2026-11-24 the dialog has an **Expires** date, 30 days ahead by default, and a *Never expire* box; the lab key above stops working on 2026-12-24. Keys made earlier show *Never*.

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}" alt="Create API key dialog with the Expires date set to Dec 24, 2026 and a Never expire checkbox" loading="lazy" width="1400" height="648"></a><figcaption>Create API key, 2026-11-24: a new key expires after 30 days unless <em>Never expire</em> is ticked.</figcaption></figure>

<div class="warn" markdown="1">
Rotate a key the moment it lands anywhere public — a commit, a screenshot, a paste in chat. Deleting the commit is not enough; the key must be revoked in the console.

Keys created before **11 November 2024** are legacy: Read/Write or Read Only on GraphQL, but full access to the AI API regardless. Replace them.
</div>

### What `verify-auth.py` does

Read-only REST v2 calls: `/account`, `/catalog/gpus`, `/pods`, `/serverless`. Nothing is created, so nothing is billed, and no SDK is needed. The last two matter most — they list Pods already running and endpoints holding active workers, which is how you find something left over from a previous session that is still charging you. A call outside the key's scopes prints the 403 reason and the script carries on.

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

<figure class="shot"><a href="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}"><img src="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}" alt="Console home with the Onboard your agent to Runpod card" loading="lazy" width="1400" height="998"></a><figcaption>The console home, 2026-11-07: Runpod now offers the agent setup itself — one line to paste into a coding agent installs its skills and the MCP server.</figcaption></figure>

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

[콘솔 → Credentials → API Keys](https://console.runpod.io/user/credentials?tab=api-keys) 에서 생성한 뒤 `./setup/init-env.sh` 를 실행합니다. 터미널 에코를 끈 채 키를 입력받고 `.env` 를 `0600` 권한으로 작성하며 마스킹된 확인값만 출력하므로, 키가 화면에도 셸 히스토리에도 남지 않습니다. 여러 번 실행해도 안전합니다. 기존 값이 기본값으로 제시되고 이전 파일은 백업됩니다.

<div class="warn" markdown="1">
**Runpod 은 키를 한 번만 보여주고 저장하지 않습니다.** 생성 시점에 비밀번호 관리자에 복사해 두세요. 분실하면 복구할 수 없고 새로 만드는 수밖에 없습니다.
</div>

키에는 API 별 범위(scope)가 있으며, 생성할 때 정하고 나중에 키 메뉴의 **Edit** 에서 바꿀 수 있습니다.

| API | 선택지 |
|---|---|
| REST (`api.runpod.io/v2`) | 리소스별 Read·Write — Pods, Serverless, Instant clusters, Volumes, Templates, Secrets, Authentication, Billing, Tags. Audit logs, Catalog, Account 는 Read 만. *All resources* 는 모든 행을 체크 |
| GraphQL (`api.runpod.io/graphql`) | None, Read / Write, Read only |
| Serverless endpoints (`api.runpod.ai`) | Read, Write. 특정 엔드포인트로 제한 가능 |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}" alt="Create API key 의 REST API 영역: Pods, Serverless, Instant clusters, Volumes, Templates, Secrets 에 Write, Authentication 은 끔, Audit logs 는 Read" loading="lazy" width="1400" height="729"></a><figcaption>Create API key, 2026-11-24: 아래의 실습용 키. 실습이 만드는 리소스에 Write, Authentication 은 끔.</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}" alt="대화상자 아래쪽: Billing, Catalog, Tags, Account 는 Read, GraphQL API 는 None 으로 접힘, api.runpod.ai 는 Read 와 Write" loading="lazy" width="1400" height="729"></a><figcaption>같은 키의 나머지: Billing, Catalog, Tags, Account 는 읽기만, GraphQL 은 None, <code>api.runpod.ai</code> 는 Read 와 Write.</figcaption></figure>

**범위 밖 호출은 거부됩니다.** 2026-11-24 에 REST Serverless Read 만 가진 키로 `GET /v2/serverless` 는 200, `GET /v2/pods` 와 카탈로그·과금·감사 로그·계정 조회, `PATCH /v2/serverless/{id}` (`serverless:write`), `POST /v2/tags` 는 빠진 범위를 밝힌 403 — *this API key does not grant pods:read* — 이었습니다. GraphQL 은 401, `api.runpod.ai/v2/<id>/health` 는 403 이었습니다.

실습별로 필요한 범위입니다.

| 작업 | 범위 |
|---|---|
| `verify-auth.py` | REST Account, Catalog, Pods, Serverless — Read |
| 콘솔에서 Lab 01 배포 | 키 불필요 |
| 배포한 엔드포인트 호출 | Serverless endpoints Read·Write, 또는 그 엔드포인트만 |
| REST 를 쓰는 Pod·Serverless·스토리지·클러스터 실습 | REST 의 Pods, Serverless, Instant clusters, Volumes, Templates, Secrets 에 Write, Audit logs, Billing, Catalog, Tags, Account 에 Read, Serverless endpoints Read·Write — 위 화면의 키 |
| `pod/01` (SDK 1.12), 클러스터 2단계, `inference-characterization` 의 재고 스냅샷 | GraphQL Read / Write 추가. 아직 GraphQL 을 부름 |
| `terraform/` | scoped 키로는 아직 확인하지 않음 |

실습용 키는 GraphQL 을 일부러 None 으로 둡니다. GraphQL 권한은 리소스별로 나뉘지 않습니다. 키와 무관한 403 이 두 가지 있었습니다. `GET /v2/tags` 는 Tags Read 가 있어도 *Resource tagging is not enabled for this user* 였고, `GET /v2/organization` 은 `membership:read` 가 필요한데 이 개인 계정의 대화상자에는 그 항목이 없습니다.

**exec 와 로그에는 GraphQL 이 필요합니다.** `POST /v2/pods/{id}/exec` 는 키에 GraphQL Read / Write 가, Pod·워커 로그는 GraphQL Read only 가 있어야 합니다 ([#112](https://github.com/litkhai/runpod-hols/issues/112), [#104](https://github.com/litkhai/runpod-hols/issues/104)). 실습용 키는 GraphQL 을 None 으로 유지하고, 이 호출이 필요할 때만 단기 키를 만들어 쓰고 지웁니다.

**키에 만료가 생겼습니다.** 2026-11-24 무렵부터 대화상자에 **Expires** 날짜 (기본 30일 뒤) 와 *Never expire* 체크박스가 있습니다. 위의 실습용 키는 2026-12-24 에 만료됩니다. 그 전에 만든 키는 *Never* 로 표시됩니다.

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}" alt="Expires 날짜가 2026년 12월 24일이고 Never expire 체크박스가 있는 Create API key 대화상자" loading="lazy" width="1400" height="648"></a><figcaption>Create API key, 2026-11-24: <em>Never expire</em> 를 체크하지 않으면 새 키는 30일 뒤 만료된다.</figcaption></figure>

<div class="warn" markdown="1">
키가 공개된 곳에 노출되는 즉시 폐기하세요. 커밋, 스크린샷, 채팅 붙여넣기 모두 해당됩니다. 커밋을 지우는 것만으로는 부족하고 콘솔에서 revoke 해야 합니다.

**2024년 11월 11일 이전**에 만든 키는 레거시입니다. GraphQL 에는 Read/Write 또는 Read Only 가 적용되지만 AI API 에는 무조건 전체 접근 권한을 가집니다. 교체하세요.
</div>

### `verify-auth.py` 가 하는 일

REST v2 읽기 호출입니다: `/account`, `/catalog/gpus`, `/pods`, `/serverless`. 생성하는 것이 없어 과금되지 않고 SDK 도 필요 없습니다. 마지막 두 항목이 가장 중요한데, 실행 중인 Pod 와 활성 워커를 둔 엔드포인트를 나열해 줍니다. 이전 세션에서 남겨둔, 지금도 과금되고 있는 것을 찾는 방법입니다. 키 범위 밖의 호출은 403 사유를 출력하고 계속 진행합니다.

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

<figure class="shot"><a href="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}"><img src="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}" alt="콘솔 홈의 Onboard your agent to Runpod 카드" loading="lazy" width="1400" height="998"></a><figcaption>콘솔 홈, 2026-11-07: Runpod 이 에이전트 설정을 직접 안내한다. 코딩 에이전트에 한 줄을 붙여 넣으면 스킬과 MCP 서버가 설치된다.</figcaption></figure>

```bash
claude mcp add --transport http runpod -s user https://mcp.getrunpod.io/
```

<div class="warn" markdown="1">
읽기/쓰기 권한으로 MCP 가 연결된 에이전트는 Pod 를 생성할 수 있고, Pod 는 기동 시점부터 과금됩니다. 실제로 리소스를 만들어야 하는 작업이 아니라면 읽기 전용 키를 사용하세요.
</div>

[저장소에서 전체 내용 보기 →](https://github.com/litkhai/runpod-hols/tree/main/setup)

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

其他路线默认你已经完成的所有事情。

### 快速开始

```bash
./setup/check-setup.sh          # 1. are the tools present?
./setup/init-env.sh             # 2. enter your secrets, writes .env (0600)
python setup/verify-auth.py     # 3. does the key actually work?
```

### API 密钥

在 [Console → Credentials → API Keys](https://console.runpod.io/user/credentials?tab=api-keys) 创建一个，然后运行 `./setup/init-env.sh`。它在关闭终端回显的情况下读取密钥，以 `0600` 权限写入 `.env`，并只打印经过遮盖的确认信息——因此密钥不会出现在屏幕或 shell 历史中。可以安全地重复运行：已有的值会成为默认值，旧文件会被备份。

<div class="warn" markdown="1">
**Runpod 只显示一次密钥，并且不保存它。** 创建时就把它复制到密码管理器中。一旦丢失就无法找回——只能新建一个。
</div>

每个密钥按 API 设置权限范围（scope），在创建时指定，之后可在密钥菜单的 **Edit** 中修改：

| API | 选项 |
|---|---|
| REST（`api.runpod.io/v2`） | 按资源分 Read 和 Write——Pods、Serverless、Instant clusters、Volumes、Templates、Secrets、Authentication、Billing、Tags；Audit logs、Catalog、Account 仅 Read。*All resources* 勾选所有行 |
| GraphQL（`api.runpod.io/graphql`） | None、Read / Write、Read only |
| Serverless endpoints（`api.runpod.ai`） | Read、Write，可限定到指定 endpoint |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}" alt="Create API key 的 REST API 区域：Pods、Serverless、Instant clusters、Volumes、Templates、Secrets 勾选 Write，Authentication 未勾选，Audit logs 为 Read" loading="lazy" width="1400" height="729"></a><figcaption>Create API key，2026-11-24：下文的实验密钥。对实验会创建的资源授予 Write，不授予 Authentication。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}" alt="对话框下半部分：Billing、Catalog、Tags、Account 为 Read，GraphQL API 折叠且为 None，api.runpod.ai 为 Read 和 Write" loading="lazy" width="1400" height="729"></a><figcaption>同一密钥的其余部分：Billing、Catalog、Tags、Account 只读，GraphQL 为 None，<code>api.runpod.ai</code> 为 Read 和 Write。</figcaption></figure>

**超出范围的调用会被拒绝。** 2026-11-24，用只有 REST Serverless Read 的密钥：`GET /v2/serverless` 返回 200；`GET /v2/pods`、目录、计费、审计日志和账号读取、`PATCH /v2/serverless/{id}`（`serverless:write`）以及 `POST /v2/tags` 均返回 403，并指出缺少的范围——*this API key does not grant pods:read*。GraphQL 返回 401，`api.runpod.ai/v2/<id>/health` 返回 403。

各实验所需范围：

| 任务 | 范围 |
|---|---|
| `verify-auth.py` | REST Account、Catalog、Pods、Serverless——Read |
| 通过控制台部署 Lab 01 | 不需要密钥 |
| 调用已部署的 endpoint | Serverless endpoints Read 和 Write，或仅限该 endpoint |
| 使用 REST 的 Pod、Serverless、存储和集群实验 | REST 的 Pods、Serverless、Instant clusters、Volumes、Templates、Secrets 授予 Write；Audit logs、Billing、Catalog、Tags、Account 授予 Read；Serverless endpoints Read 和 Write——即上图中的密钥 |
| `pod/01`（SDK 1.12）、集群第二阶段、`inference-characterization` 中的库存快照 | 另加 GraphQL Read / Write；它们仍调用 GraphQL |
| `terraform/` | 尚未用 scoped 密钥检查 |

实验密钥有意把 GraphQL 设为 None：GraphQL 权限不按资源细分。有两个 403 与密钥无关——即使授予了 Tags Read，`GET /v2/tags` 仍返回 *Resource tagging is not enabled for this user*；`GET /v2/organization` 需要 `membership:read`，而这个个人账号的对话框中没有该项。

**exec 和日志需要 GraphQL。** `POST /v2/pods/{id}/exec` 要求密钥具有 GraphQL Read / Write；Pod 和 worker 日志需要 GraphQL Read only（[#112](https://github.com/litkhai/runpod-hols/issues/112)、[#104](https://github.com/litkhai/runpod-hols/issues/104)）。实验密钥保持 GraphQL 为 None：需要这些调用时创建一个短期密钥，用完删除。

**密钥现在会过期。** 大约从 2026-11-24 起，对话框中有 **Expires** 日期（默认 30 天后）和 *Never expire* 复选框；上面的实验密钥将于 2026-12-24 失效。此前创建的密钥显示为 *Never*。

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}" alt="Create API key 对话框，Expires 日期为 2026 年 12 月 24 日，并有 Never expire 复选框" loading="lazy" width="1400" height="648"></a><figcaption>Create API key，2026-11-24：除非勾选 <em>Never expire</em>，新密钥 30 天后过期。</figcaption></figure>

<div class="warn" markdown="1">
密钥一旦出现在任何公开场所——一次提交、一张截图、一次聊天粘贴——就立即轮换。删除提交是不够的；必须在控制台中吊销该密钥。

**2024 年 11 月 11 日**之前创建的密钥属于旧版：在 GraphQL 上是 Read/Write 或 Read Only，但无论如何对 AI API 都拥有完全访问权限。请替换它们。
</div>

### `verify-auth.py` 做了什么

REST v2 只读调用：`/account`、`/catalog/gpus`、`/pods`、`/serverless`。不创建任何东西，所以不产生任何费用，也不需要 SDK。最后两个最重要——它们列出已经在运行的 Pod 和保留了 active worker 的 endpoint，你就是靠它们找到上一次会话遗留下来、仍在计费的资源。超出密钥范围的调用会打印 403 原因，脚本继续执行。

### 各路线所需工具

| 工具 | 用于 | 安装 |
|---|---|---|
| Python 3.10+ | 全部 | `uv venv --python 3.11` |
| Docker | Serverless | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Terraform 1.6+ | Terraform | `brew install hashicorp/tap/terraform` |
| `runpodctl` | Pod（可选） | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP（可选） | `brew install node` |

<div class="note" markdown="1">
**macOS 上的两个陷阱。** 系统自带的 `python3` 是 3.9，而 Runpod SDK 需要 3.10+，所以请使用 `uv venv --python 3.11`。另外，Homebrew 的 `terraform` formula 停留在 1.5.7，无法安装 Runpod provider——请改用 HashiCorp tap。
</div>

### 从代码访问 Runpod 的途径

| 途径 | 最适合 |
|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | 脚本，以及 worker 运行时本身 |
| [`runpodctl`](https://github.com/runpod/runpodctl) | 快速的 CLI 操作、文件传输 |
| [Terraform provider](https://registry.terraform.io/providers/runpod/runpod) | 可复现的基础设施 |
| [MCP server](https://github.com/runpod/runpod-mcp) | 从 Claude Code 或 Cursor 操控 Runpod |

### MCP——从 AI 智能体使用 Runpod

官方 [MCP server](https://github.com/runpod/runpod-mcp) 是 Runpod 组织中维护最活跃的集成。托管模式无需安装，也不会在磁盘上保存 API 密钥：

<figure class="shot"><a href="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}"><img src="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}" alt="控制台首页的 Onboard your agent to Runpod 卡片" loading="lazy" width="1400" height="998"></a><figcaption>控制台首页，2026-11-07：Runpod 现在直接提供 agent 配置——把一行文字粘贴到编码 agent 中，就会安装其 skills 和 MCP 服务器。</figcaption></figure>

```bash
claude mcp add --transport http runpod -s user https://mcp.getrunpod.io/
```

<div class="warn" markdown="1">
拥有读写 MCP 连接的智能体可以创建 Pod，而 Pod 从启动那一刻起就开始计费。除非任务确实需要创建资源，否则请使用只读密钥。
</div>

[在仓库中查看完整内容 →](https://github.com/litkhai/runpod-hols/tree/main/setup)

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

他のトラックが「もう済んでいる」と前提にしていることのすべてです。

### クイックスタート

```bash
./setup/check-setup.sh          # 1. are the tools present?
./setup/init-env.sh             # 2. enter your secrets, writes .env (0600)
python setup/verify-auth.py     # 3. does the key actually work?
```

### API キー

[Console → Credentials → API Keys](https://console.runpod.io/user/credentials?tab=api-keys) で作成し、`./setup/init-env.sh` を実行します。ターミナルのエコーを無効にした状態でキーを読み取り、`.env` を `0600` のパーミッションで書き込み、マスクされた確認表示だけを出力します。そのためキーが画面にもシェル履歴にも残りません。何度実行しても安全です。既存の値がデフォルトになり、古いファイルはバックアップされます。

<div class="warn" markdown="1">
**Runpod はキーを一度しか表示せず、保存もしません。** 作成時にパスワードマネージャーにコピーしてください。紛失すると復元できず、新しく作るしかありません。
</div>

キーには API ごとのスコープがあり、作成時に設定し、あとからキーのメニューの **Edit** で変更できます。

| API | 選択肢 |
|---|---|
| REST（`api.runpod.io/v2`） | リソースごとの Read と Write——Pods、Serverless、Instant clusters、Volumes、Templates、Secrets、Authentication、Billing、Tags。Audit logs、Catalog、Account は Read のみ。*All resources* はすべての行にチェック |
| GraphQL（`api.runpod.io/graphql`） | None、Read / Write、Read only |
| Serverless endpoints（`api.runpod.ai`） | Read、Write。特定の endpoint に限定可能 |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-scopes.webp' | relative_url }}" alt="Create API key の REST API 部分：Pods、Serverless、Instant clusters、Volumes、Templates、Secrets に Write、Authentication はオフ、Audit logs は Read" loading="lazy" width="1400" height="729"></a><figcaption>Create API key、2026-11-24：下のラボ用キー。ラボが作るリソースに Write、Authentication はオフ。</figcaption></figure>

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-graphql-endpoints.webp' | relative_url }}" alt="ダイアログの下半分：Billing、Catalog、Tags、Account は Read、GraphQL API は None のまま折りたたみ、api.runpod.ai は Read と Write" loading="lazy" width="1400" height="729"></a><figcaption>同じキーの残り：Billing、Catalog、Tags、Account は読み取りのみ、GraphQL は None、<code>api.runpod.ai</code> は Read と Write。</figcaption></figure>

**スコープ外の呼び出しは拒否されます。** 2026-11-24、REST の Serverless Read だけを持つキーでは、`GET /v2/serverless` が 200、`GET /v2/pods` とカタログ・課金・監査ログ・アカウントの読み取り、`PATCH /v2/serverless/{id}`（`serverless:write`）、`POST /v2/tags` は、足りないスコープを示す 403——*this API key does not grant pods:read*——でした。GraphQL は 401、`api.runpod.ai/v2/<id>/health` は 403 でした。

ラボごとに必要なスコープ：

| 作業 | スコープ |
|---|---|
| `verify-auth.py` | REST の Account、Catalog、Pods、Serverless——Read |
| コンソールから Lab 01 をデプロイ | キー不要 |
| デプロイした endpoint の呼び出し | Serverless endpoints の Read と Write、またはその endpoint のみ |
| REST を使う Pod・Serverless・ストレージ・クラスターのラボ | REST の Pods、Serverless、Instant clusters、Volumes、Templates、Secrets に Write、Audit logs、Billing、Catalog、Tags、Account に Read、Serverless endpoints の Read と Write——上の画面のキー |
| `pod/01`（SDK 1.12）、クラスターのステージ 2、`inference-characterization` の在庫スナップショット | GraphQL Read / Write を追加。まだ GraphQL を呼びます |
| `terraform/` | scoped キーではまだ確認していません |

ラボ用キーは GraphQL を意図的に None にしています。GraphQL の権限はリソースごとに分かれません。キーとは関係のない 403 が 2 つありました。`GET /v2/tags` は Tags Read を付けても *Resource tagging is not enabled for this user* で、`GET /v2/organization` には `membership:read` が必要ですが、この個人アカウントのダイアログにはその項目がありません。

**exec とログには GraphQL が必要です。** `POST /v2/pods/{id}/exec` にはキーの GraphQL Read / Write が、Pod とワーカーのログには GraphQL Read only が必要です（[#112](https://github.com/litkhai/runpod-hols/issues/112)、[#104](https://github.com/litkhai/runpod-hols/issues/104)）。ラボ用キーは GraphQL を None のままにし、これらの呼び出しが必要なときだけ短期キーを作り、使い終わったら削除します。

**キーに有効期限ができました。** 2026-11-24 ごろから、ダイアログに **Expires** の日付（既定は 30 日後）と *Never expire* のチェックボックスがあります。上のラボ用キーは 2026-12-24 に失効します。それ以前に作ったキーは *Never* と表示されます。

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key-expires.webp' | relative_url }}" alt="Expires が 2026 年 12 月 24 日で、Never expire のチェックボックスがある Create API key ダイアログ" loading="lazy" width="1400" height="648"></a><figcaption>Create API key、2026-11-24：<em>Never expire</em> にチェックしない限り、新しいキーは 30 日後に失効する。</figcaption></figure>

<div class="warn" markdown="1">
キーが公開の場所に出たら、その瞬間にローテーションしてください。コミット、スクリーンショット、チャットへの貼り付けも含みます。コミットを削除するだけでは不十分で、コンソールでキーを失効させる必要があります。

**2024 年 11 月 11 日**より前に作成されたキーはレガシーです。GraphQL では Read/Write または Read Only ですが、AI API には関係なくフルアクセスを持ちます。置き換えてください。
</div>

### `verify-auth.py` がすること

REST v2 の読み取り専用呼び出し：`/account`、`/catalog/gpus`、`/pods`、`/serverless`。何も作成しないので何も課金されず、SDK も不要です。最も重要なのは最後の 2 つで、稼働中の Pod とアクティブワーカーを持つ endpoint を一覧表示します。前のセッションから残っていて、今も課金されているものはこれで見つけます。キーのスコープ外の呼び出しは 403 の理由を表示し、スクリプトはそのまま続行します。

### トラック別のツール

| ツール | 必要なトラック | インストール |
|---|---|---|
| Python 3.10+ | すべて | `uv venv --python 3.11` |
| Docker | Serverless | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Terraform 1.6+ | Terraform | `brew install hashicorp/tap/terraform` |
| `runpodctl` | Pod（任意） | `brew install runpod/runpodctl/runpodctl` |
| Node 18+ | MCP（任意） | `brew install node` |

<div class="note" markdown="1">
**macOS の 2 つの落とし穴。** システムの `python3` は 3.9 で、Runpod SDK は 3.10+ を必要とするため、`uv venv --python 3.11` を使ってください。また、Homebrew の `terraform` formula は 1.5.7 で止まっていて Runpod provider をインストールできません。代わりに HashiCorp tap を使ってください。
</div>

### コードから Runpod にアクセスする方法

| 方法 | 最適な用途 |
|---|---|
| [Python SDK](https://github.com/runpod/runpod-python) | スクリプト、そして worker ランタイムそのもの |
| [`runpodctl`](https://github.com/runpod/runpodctl) | 手早い CLI 操作、ファイル転送 |
| [Terraform provider](https://registry.terraform.io/providers/runpod/runpod) | 再現可能なインフラ |
| [MCP server](https://github.com/runpod/runpod-mcp) | Claude Code や Cursor から Runpod を操作 |

### MCP：AI エージェントから Runpod を使う

公式の [MCP server](https://github.com/runpod/runpod-mcp) は、Runpod org の中で最も活発にメンテナンスされている連携です。ホスト型モードはインストール不要で、API キーをディスクに保存しません。

<figure class="shot"><a href="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}"><img src="{{ '/assets/img/setup/home-agent-card.webp' | relative_url }}" alt="コンソールのホームにある Onboard your agent to Runpod カード" loading="lazy" width="1400" height="998"></a><figcaption>コンソールのホーム、2026-11-07：Runpod がエージェントの設定を自ら案内しています。コーディングエージェントに 1 行貼り付けると、スキルと MCP サーバーが入ります。</figcaption></figure>

```bash
claude mcp add --transport http runpod -s user https://mcp.getrunpod.io/
```

<div class="warn" markdown="1">
読み書き可能な MCP 接続を持つエージェントは Pod を作成でき、Pod は起動した瞬間から課金されます。タスクが本当に何かをプロビジョニングする必要がない限り、読み取り専用のキーを使ってください。
</div>

[リポジトリで詳細を見る →](https://github.com/litkhai/runpod-hols/tree/main/setup)

</div>
