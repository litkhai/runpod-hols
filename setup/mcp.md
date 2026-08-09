# MCP — Driving Runpod from an AI Agent

[English](#english) | [한국어](#한국어)

---

## English

[`runpod/runpod-mcp`](https://github.com/runpod/runpod-mcp) is Runpod's official Model Context Protocol server. It lets agents like Claude Code, Claude Desktop, Cursor, Windsurf and VS Code manage your Pods, Serverless endpoints, templates and network volumes conversationally.

It is the most actively maintained integration in the Runpod org (v3.2.0, ⭐74), which makes it a practical complement to the SDK and Terraform tracks — the SDK is for code you ship, MCP is for the exploratory work around it.

### Two Connection Modes

| Mode | How it works | API key on disk |
|---|---|---|
| **Hosted** (recommended) | Client points at `https://mcp.getrunpod.io/`, you sign in with Runpod (OAuth) | **No** |
| **Local** | Server runs locally through `npx`, key stored in the client config | Yes |

Prefer hosted. There is nothing to install and no long-lived key sitting in a config file.

### Claude Code — Hosted

```bash
claude mcp add --transport http runpod -s user https://mcp.getrunpod.io/
```

`-s user` registers it for your whole user account rather than just this project. Drop it to scope the server to one repo.

### Guided Installer

Detects which clients you have and writes the config for you:

```bash
npx @runpod/mcp-server@latest add
```

To undo:

```bash
npx @runpod/mcp-server@latest remove
```

### Other Clients

Any client that accepts a URL-based MCP entry:

```json
{
  "mcpServers": {
    "runpod": {
      "url": "https://mcp.getrunpod.io/"
    }
  }
}
```

### The Full Plugin Bundle

[`runpod/runpod-plugins-official`](https://github.com/runpod/runpod-plugins-official) bundles the MCP server with skills for `runpodctl`, `flash`, usage reporting and more. In Claude Code:

```
/plugin marketplace add runpod/runpod-plugins-official
/plugin install runpod@runpod
```

This wires up the hosted MCP server including OAuth, so no separate step is needed.

### Requirements

- Node.js 18+
- A Runpod account and API key (hosted mode authenticates by OAuth instead)

### ⚠️ A Note on Agents and Billing

An agent with a read/write MCP connection can **create Pods**, and a Pod bills from the moment it starts. Two habits worth keeping:

- Use a **read-only** API key unless the task genuinely needs to provision something.
- Set a spending limit in the console regardless.

Reviewing what an agent is about to create is cheaper than discovering it on the invoice.

---

## 한국어

[`runpod/runpod-mcp`](https://github.com/runpod/runpod-mcp) 는 Runpod 의 공식 Model Context Protocol 서버입니다. Claude Code, Claude Desktop, Cursor, Windsurf, VS Code 같은 에이전트에서 Pod, Serverless 엔드포인트, 템플릿, 네트워크 볼륨을 대화로 관리할 수 있게 해줍니다.

Runpod 조직에서 가장 활발히 관리되는 연동 프로젝트입니다 (v3.2.0, ⭐74). SDK 는 배포할 코드를 위한 것이고 MCP 는 그 주변의 탐색적 작업을 위한 것이라, SDK · Terraform 트랙과 상호 보완적입니다.

### 두 가지 연결 방식

| 방식 | 동작 | 디스크에 API 키 저장 |
|---|---|---|
| **Hosted** (권장) | 클라이언트가 `https://mcp.getrunpod.io/` 를 바라보고 Runpod 계정으로 로그인 (OAuth) | **없음** |
| **Local** | `npx` 로 로컬에서 서버 실행, 클라이언트 설정에 키 저장 | 있음 |

Hosted 를 권장합니다. 설치할 것이 없고 설정 파일에 장기 유효 키가 남지 않습니다.

### Claude Code — Hosted 방식

```bash
claude mcp add --transport http runpod -s user https://mcp.getrunpod.io/
```

`-s user` 는 이 프로젝트만이 아니라 사용자 계정 전체에 등록합니다. 특정 저장소에만 적용하려면 이 옵션을 빼면 됩니다.

### 가이드 설치 도구

설치된 클라이언트를 자동 감지해 설정을 대신 작성해 줍니다.

```bash
npx @runpod/mcp-server@latest add
```

되돌리려면:

```bash
npx @runpod/mcp-server@latest remove
```

### 그 외 클라이언트

URL 기반 MCP 항목을 지원하는 클라이언트라면:

```json
{
  "mcpServers": {
    "runpod": {
      "url": "https://mcp.getrunpod.io/"
    }
  }
}
```

### 플러그인 번들

[`runpod/runpod-plugins-official`](https://github.com/runpod/runpod-plugins-official) 는 MCP 서버에 더해 `runpodctl`, `flash`, 사용량 리포트 등의 스킬을 함께 제공합니다. Claude Code 에서:

```
/plugin marketplace add runpod/runpod-plugins-official
/plugin install runpod@runpod
```

Hosted MCP 서버와 OAuth 까지 함께 설정되므로 별도 작업이 필요 없습니다.

### 요구 사항

- Node.js 18 이상
- Runpod 계정과 API 키 (Hosted 방식은 OAuth 로 인증하므로 키 불필요)

### ⚠️ 에이전트와 과금에 대한 주의

읽기/쓰기 권한으로 MCP 가 연결된 에이전트는 **Pod 를 생성할 수 있고**, Pod 는 기동 시점부터 과금됩니다. 두 가지 습관을 권합니다.

- 실제로 리소스를 만들어야 하는 작업이 아니라면 **읽기 전용** API 키를 사용하세요.
- 그와 별개로 콘솔에서 지출 한도를 설정해 두세요.

에이전트가 무엇을 만들려 하는지 미리 확인하는 편이, 청구서에서 발견하는 것보다 훨씬 저렴합니다.
