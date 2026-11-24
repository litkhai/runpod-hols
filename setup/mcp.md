# MCP — Driving Runpod from an AI Agent

[English](#english) | [한국어](#한국어)

---

## English

[`runpod/runpod-mcp`](https://github.com/runpod/runpod-mcp) is Runpod's official Model Context Protocol server. It lets agents like Claude Code, Claude Desktop, Cursor, Windsurf and VS Code manage Pods, Serverless endpoints, storage, templates, the account and the organization conversationally.

The version described here is `@runpod/mcp-server` **5.0.0** (2026-11-23, ⭐88). The tool list below was read from the source at that tag on 2026-11-24; the server was not connected and no tool was called ([#106](https://github.com/litkhai/runpod-hols/issues/106)). The SDK is for code you ship; MCP is for the exploratory work around it.

### Two Connection Modes

| Mode | How it works | API key on disk |
|---|---|---|
| **Hosted** (recommended) | Client points at `https://mcp.runpod.io/` and signs in with Runpod (OAuth), or sends an API key as a header | **No** with OAuth |
| **Local** | Server runs through `npx`, key in the client config as `RUNPOD_API_KEY` | Yes |

The hosted address used to be `https://mcp.getrunpod.io/`; both answer, and Runpod's own README and plugin now use `mcp.runpod.io`.

### Claude Code — Hosted

```bash
claude mcp add --transport http runpod -s user https://mcp.runpod.io/
```

`-s user` registers it for your whole user account rather than just this project. Drop it to scope the server to one repo.

### Guided Installer

Detects which clients you have and writes the config for you:

```bash
npx @runpod/mcp-server@latest add
```

`--client cursor --local` picks one client and local mode; `--list` shows what was detected. To undo:

```bash
npx @runpod/mcp-server@latest remove
```

### Other Clients

Any client that accepts a URL-based MCP entry:

```json
{
  "mcpServers": {
    "runpod": {
      "url": "https://mcp.runpod.io/"
    }
  }
}
```

### What the Server Exposes

138 tools in 5.0.0, most generated from the REST v2 spec. Each carries MCP annotations (`readOnlyHint`, `destructiveHint`, …) so a client can auto-approve reads and stop on `delete-pod` or `purge-endpoint-queue`.

| Area | Tools |
|---|---|
| Pods | `list-pods`, `get-pod`, `create-pod`, `update-pod`, `delete-pod`, `pod-action`, `exec-pod`, `stream-pod-logs`; queued Pods: `list-queued-pods`, `get-queued-pod`, `delete-queued-pod` |
| Serverless | endpoint CRUD, `set-endpoint-gpus`, `endpoint-health`; jobs: `run-endpoint`, `runsync-endpoint`, `get-job-status`, `stream-job`, `cancel-job`, `retry-job`, `purge-endpoint-queue`; `list-endpoint-workers`, `stream-worker-logs`, builds, releases, request / cold-start / worker metrics |
| Storage | network volumes and **global volumes** — list, get, create, update, delete |
| Templates and credentials | templates and their readmes, container registries, ECR delegations, **secrets**, account SSH keys |
| Clusters | Instant Cluster CRUD, `list-cluster-pods` |
| **Organizations** | organization, users, groups and members, roles and capabilities, invites |
| Account and billing | `get-account`, `get-account-limits`, `get-balance`, six billing lists, cost centers, tags, `list-audit-logs` |
| Catalog and Hub | GPU and CPU types, data centers, `get-capacity`, public templates, `list-hub-repos`, `deploy-hub-repo`, `list-public-endpoints` |
| **Knowledge base** | `search-docs`, `list-guides` and `read-guide` (118 plugin guides), `search-concepts`, `lookup-concept` |
| **Feedback** | `report_feedback` — sends one observation (with a severity) to Runpod for internal review; nothing comes back to the session |

Changes since the 3.2.0 this page was first written for, that affect use here:

- **Every list returns one page** (5.0.0): `limit` 1–100, default 20, and a `cursor`; follow `pagination.nextCursor`.
- **A scoped key with GraphQL set to None is accepted** by the hosted server (5.0.0): its pre-flight now falls back to `GET /v2/account`. The lab key from [#103](https://github.com/litkhai/runpod-hols/issues/103) is such a key.
- **Node.js 20** or newer for local mode (was 18).

### The Full Plugin Bundle

[`runpod/runpod-plugins-official`](https://github.com/runpod/runpod-plugins-official) 2.2.1 (2026-11-20) bundles the hosted server with skills. In Claude Code:

```bash
claude plugin marketplace add runpod/runpod-plugins-official
claude plugin install runpod@runpod
```

It registers `https://mcp.runpod.io/` (sign in with `/mcp`) and installs 18 skills — a `runpod` router, `runpod-mcp`, `runpodctl`, `runpod-flash`, `runpod-pod-deploy`, `runpod-pod-doctor`, `runpod-serverless-deploy`, `runpod-endpoint-ops`, `runpod-vllm`, `runpod-discovery`, `runpod-cost-audit`, `runpod-lifecycle-crud`, `runpod-templates`, `runpod-build-template`, `runpod-usage`, `runpod-companion-clis`, `runpod-migrate`, `runpod-cloud-migrate` — and two commands, `/runpod:migrate` and `/runpod:migrate-cloud`. `/runpod:migrate` was compared against a hand migration in [#101](https://github.com/litkhai/runpod-hols/issues/101). Other agents get the skills with `npx skills add runpod/runpod-plugins-official`.

### Requirements

- Node.js 20+ for local mode
- A Runpod account; an API key for local mode or header auth (hosted mode can sign in by OAuth instead)

### ⚠️ A Note on Agents and Billing

An agent with a read/write MCP connection can **create Pods**, and a Pod bills from the moment it starts. Two habits worth keeping:

- Give the agent a **scoped key** with only what the task needs — read-only for exploring. See [API Key](./README.md#1-api-key).
- Set a spending limit in the console regardless; `get-account-limits` shows it and the current spend rate.

Reviewing what an agent is about to create is cheaper than discovering it on the invoice.

---

## 한국어

[`runpod/runpod-mcp`](https://github.com/runpod/runpod-mcp) 는 Runpod 의 공식 Model Context Protocol 서버입니다. Claude Code, Claude Desktop, Cursor, Windsurf, VS Code 같은 에이전트에서 Pod, Serverless 엔드포인트, 스토리지, 템플릿, 계정과 조직을 대화로 관리할 수 있게 해줍니다.

여기서 다루는 버전은 `@runpod/mcp-server` **5.0.0** (2026-11-23, ⭐88) 입니다. 아래 도구 목록은 2026-11-24 에 그 태그의 소스에서 읽었으며, 서버에 연결하거나 도구를 호출하지는 않았습니다 ([#106](https://github.com/litkhai/runpod-hols/issues/106)). SDK 는 배포할 코드를 위한 것이고 MCP 는 그 주변의 탐색적 작업을 위한 것입니다.

### 두 가지 연결 방식

| 방식 | 동작 | 디스크에 API 키 |
|---|---|---|
| **Hosted** (권장) | 클라이언트가 `https://mcp.runpod.io/` 를 가리키고 Runpod 로그인(OAuth) 또는 헤더의 API 키로 인증 | OAuth 면 **없음** |
| **Local** | `npx` 로 서버를 실행, 클라이언트 설정에 `RUNPOD_API_KEY` 저장 | 있음 |

hosted 주소는 원래 `https://mcp.getrunpod.io/` 였습니다. 둘 다 응답하며, Runpod 의 README 와 플러그인은 이제 `mcp.runpod.io` 를 씁니다.

### Claude Code — Hosted 방식

```bash
claude mcp add --transport http runpod -s user https://mcp.runpod.io/
```

`-s user` 는 현재 프로젝트가 아니라 사용자 계정 전체에 등록합니다. 빼면 이 저장소에만 적용됩니다.

### 가이드 설치 도구

설치된 클라이언트를 감지해 설정을 써 줍니다.

```bash
npx @runpod/mcp-server@latest add
```

`--client cursor --local` 은 클라이언트 하나와 local 방식을 고르고, `--list` 는 감지 결과를 보여줍니다. 되돌리려면:

```bash
npx @runpod/mcp-server@latest remove
```

### 그 외 클라이언트

URL 기반 MCP 항목을 받는 클라이언트라면:

```json
{
  "mcpServers": {
    "runpod": {
      "url": "https://mcp.runpod.io/"
    }
  }
}
```

### 서버가 제공하는 것

5.0.0 의 도구는 138개이며 대부분 REST v2 스펙에서 생성됩니다. 각 도구에 MCP 어노테이션 (`readOnlyHint`, `destructiveHint` 등) 이 붙어 있어, 클라이언트가 읽기는 자동 승인하고 `delete-pod` 나 `purge-endpoint-queue` 에서는 멈출 수 있습니다.

| 영역 | 도구 |
|---|---|
| Pod | `list-pods`, `get-pod`, `create-pod`, `update-pod`, `delete-pod`, `pod-action`, `exec-pod`, `stream-pod-logs`. 대기 Pod: `list-queued-pods`, `get-queued-pod`, `delete-queued-pod` |
| Serverless | 엔드포인트 CRUD, `set-endpoint-gpus`, `endpoint-health`. 작업: `run-endpoint`, `runsync-endpoint`, `get-job-status`, `stream-job`, `cancel-job`, `retry-job`, `purge-endpoint-queue`. `list-endpoint-workers`, `stream-worker-logs`, 빌드, 릴리스, 요청·콜드 스타트·워커 지표 |
| 스토리지 | 네트워크 볼륨과 **글로벌 볼륨** — 목록, 조회, 생성, 수정, 삭제 |
| 템플릿과 자격 증명 | 템플릿과 readme, 컨테이너 레지스트리, ECR 위임, **시크릿**, 계정 SSH 키 |
| 클러스터 | Instant Cluster CRUD, `list-cluster-pods` |
| **조직** | 조직, 사용자, 그룹과 멤버, 역할과 권한, 초대 |
| 계정과 과금 | `get-account`, `get-account-limits`, `get-balance`, 과금 목록 6종, 비용 센터, 태그, `list-audit-logs` |
| 카탈로그와 Hub | GPU·CPU 종류, 데이터센터, `get-capacity`, 공개 템플릿, `list-hub-repos`, `deploy-hub-repo`, `list-public-endpoints` |
| **지식 베이스** | `search-docs`, `list-guides` 와 `read-guide` (플러그인 가이드 118개), `search-concepts`, `lookup-concept` |
| **피드백** | `report_feedback` — 관찰 하나를 심각도와 함께 Runpod 내부 검토용으로 보냄. 세션으로 돌아오는 것은 없음 |

이 문서를 처음 쓴 3.2.0 이후, 여기서 쓰는 데 영향이 있는 변화:

- **모든 목록이 한 페이지씩 돌려줍니다** (5.0.0). `limit` 1–100, 기본 20, 그리고 `cursor`. `pagination.nextCursor` 를 따라가세요.
- **GraphQL 을 None 으로 둔 scoped 키도 받습니다** (5.0.0). hosted 서버의 사전 확인이 이제 `GET /v2/account` 로 다시 확인합니다. [#103](https://github.com/litkhai/runpod-hols/issues/103) 의 실습용 키가 그런 키입니다.
- local 방식은 **Node.js 20** 이상 (이전 18).

### 플러그인 번들

[`runpod/runpod-plugins-official`](https://github.com/runpod/runpod-plugins-official) 2.2.1 (2026-11-20) 은 hosted 서버와 스킬을 묶어 제공합니다. Claude Code 에서:

```bash
claude plugin marketplace add runpod/runpod-plugins-official
claude plugin install runpod@runpod
```

`https://mcp.runpod.io/` 를 등록하고 (`/mcp` 로 로그인), 스킬 18개 — `runpod` 라우터, `runpod-mcp`, `runpodctl`, `runpod-flash`, `runpod-pod-deploy`, `runpod-pod-doctor`, `runpod-serverless-deploy`, `runpod-endpoint-ops`, `runpod-vllm`, `runpod-discovery`, `runpod-cost-audit`, `runpod-lifecycle-crud`, `runpod-templates`, `runpod-build-template`, `runpod-usage`, `runpod-companion-clis`, `runpod-migrate`, `runpod-cloud-migrate` — 와 명령 두 개 `/runpod:migrate`, `/runpod:migrate-cloud` 를 설치합니다. `/runpod:migrate` 는 [#101](https://github.com/litkhai/runpod-hols/issues/101) 에서 손으로 한 이전과 비교했습니다. 다른 에이전트는 `npx skills add runpod/runpod-plugins-official` 로 스킬을 받습니다.

### 요구 사항

- local 방식은 Node.js 20 이상
- Runpod 계정. local 방식이나 헤더 인증에는 API 키 (hosted 방식은 OAuth 로그인으로 대신할 수 있음)

### ⚠️ 에이전트와 과금에 대한 주의

읽기/쓰기 MCP 연결을 가진 에이전트는 **Pod 를 생성**할 수 있고, Pod 는 시작하는 순간부터 과금됩니다. 지켜둘 습관 두 가지:

- 작업에 필요한 것만 담은 **scoped 키**를 주세요. 탐색만 한다면 읽기 전용으로. [API 키](./README.md#1-api-키) 참조.
- 그와 별개로 콘솔에서 지출 한도를 설정하세요. `get-account-limits` 가 한도와 현재 지출 속도를 보여줍니다.

에이전트가 무엇을 만들려는지 미리 검토하는 편이 청구서에서 발견하는 것보다 쌉니다.
