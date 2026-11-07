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

Keys carry a permission level, set at creation:

| Level | Meaning |
|---|---|
| **All** | Full access |
| **Restricted** | Per-API access you configure — `None`, `Restricted`, `Read/Write`, `Read Only` |
| **Read Only** | Read access, no writes |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}" alt="Create API key dialog: the All, Restricted and Read only levels from the table above" loading="lazy" width="1400" height="998"></a><figcaption>Create API key, 2026-11-07. The console now keeps keys under <strong>Credentials → API Keys</strong> rather than Settings.</figcaption></figure>

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

키에는 생성 시 지정하는 권한 등급이 있습니다.

| 등급 | 내용 |
|---|---|
| **All** | 전체 접근 |
| **Restricted** | API 별로 직접 설정 — `None`, `Restricted`, `Read/Write`, `Read Only` |
| **Read Only** | 읽기만, 쓰기 불가 |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}" alt="Create API key 화면: 위 표의 All, Restricted, Read only 권한" loading="lazy" width="1400" height="998"></a><figcaption>Create API key, 2026-11-07. 콘솔은 이제 키를 Settings 가 아니라 <strong>Credentials → API Keys</strong> 에 둔다.</figcaption></figure>

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

密钥带有在创建时设定的权限级别：

| 级别 | 含义 |
|---|---|
| **All** | 完全访问 |
| **Restricted** | 由你按 API 配置访问——`None`、`Restricted`、`Read/Write`、`Read Only` |
| **Read Only** | 只读，不可写入 |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}" alt="Create API key 对话框：上表中的 All、Restricted、Read only 三种权限" loading="lazy" width="1400" height="998"></a><figcaption>Create API key，2026-11-07。控制台现在把密钥放在 <strong>Credentials → API Keys</strong>，而不是 Settings。</figcaption></figure>

| 任务 | 级别 |
|---|---|
| `verify-auth.py`，浏览 GPU 类型和资源 | **Read Only** |
| 通过控制台部署实验 01 | 无需密钥 |
| 调用已部署的端点 | 对该端点的访问权限 |
| `terraform/01-endpoint` | 写入权限 |
| `terraform/02-pod` | **All** |

文档中的 `Restricted` 模式是*按 Serverless 端点*定制访问，并未明确涵盖 Pod 或 Network Volume 的范围，因此对 Pod 实验来说，`All` 是可靠的选择。

权限可以之后在 Settings 页面**修改**——无需再签发第二个密钥。先从 Read Only 开始，到了 Terraform 实验再提升。

<div class="warn" markdown="1">
密钥一旦出现在任何公开场所——一次提交、一张截图、一次聊天粘贴——就立即轮换。删除提交是不够的；必须在控制台中吊销该密钥。

**2024 年 11 月 11 日**之前创建的密钥属于旧版：在 GraphQL 上是 Read/Write 或 Read Only，但无论如何对 AI API 都拥有完全访问权限。请替换它们。
</div>

### `verify-auth.py` 做了什么

三个只读调用：`get_user`、`get_gpus`、`get_pods`。不创建任何东西，所以不产生任何费用。最后一个最重要——它列出你已经在运行的 Pod，你就是靠它找到上一次会话遗留下来、仍在计费的 Pod。

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

キーには作成時に設定する権限レベルがあります。

| レベル | 意味 |
|---|---|
| **All** | フルアクセス |
| **Restricted** | API ごとに自分で設定するアクセス：`None`、`Restricted`、`Read/Write`、`Read Only` |
| **Read Only** | 読み取りのみ、書き込み不可 |

<figure class="shot"><a href="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}"><img src="{{ '/assets/img/setup/create-api-key.webp' | relative_url }}" alt="Create API key ダイアログ：上の表の All、Restricted、Read only の 3 レベル" loading="lazy" width="1400" height="998"></a><figcaption>Create API key、2026-11-07。コンソールはキーを Settings ではなく <strong>Credentials → API Keys</strong> に置くようになりました。</figcaption></figure>

| 作業 | レベル |
|---|---|
| `verify-auth.py`、GPU タイプとリソースの参照 | **Read Only** |
| コンソールからのラボ 01 のデプロイ | キー不要 |
| デプロイ済みエンドポイントの呼び出し | そのエンドポイントへのアクセス |
| `terraform/01-endpoint` | 書き込みアクセス |
| `terraform/02-pod` | **All** |

ドキュメントにある `Restricted` モードは *Serverless エンドポイント単位*でアクセスをカスタマイズするもので、Pod や Network Volume の範囲を明確にはカバーしていません。そのため Pod ラボでは `All` が確実な選択です。

権限は Settings ページから**後で編集できます。** 2 つ目のキーを発行する必要はありません。Read Only で始め、Terraform ラボに進んだら引き上げてください。

<div class="warn" markdown="1">
キーが公開の場所に出たら、その瞬間にローテーションしてください。コミット、スクリーンショット、チャットへの貼り付けも含みます。コミットを削除するだけでは不十分で、コンソールでキーを失効させる必要があります。

**2024 年 11 月 11 日**より前に作成されたキーはレガシーです。GraphQL では Read/Write または Read Only ですが、AI API には関係なくフルアクセスを持ちます。置き換えてください。
</div>

### `verify-auth.py` がすること

読み取り専用の呼び出し 3 つ：`get_user`、`get_gpus`、`get_pods`。何も作成しないので、何も課金されません。最も重要なのは最後のもので、すでに稼働中の Pod を一覧表示します。前のセッションから残っていて、今も課金されている Pod はこれで見つけます。

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
