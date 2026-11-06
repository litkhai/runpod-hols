---
layout: default
title: About
permalink: /about/
---

# About This Repository

<div class="lang" data-lang="en" markdown="1">

## English

An unofficial set of hands-on labs for [Runpod](https://runpod.io), written while learning the platform. Source at [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols).

The aim is to understand the Runpod SDK and the AI infrastructure around it by running things, not by reading about them.

### Everything here was run

Command output, image sizes, latency figures and error messages are from a real account. Where something has **not** been run — `terraform apply`, the Pod track — the page says so.

| Finding | Where it is documented |
|---|---|
| The console's **Build context** field is undocumented, and required for a nested Dockerfile | [Serverless]({{ '/serverless/' | relative_url }}) |
| `{"input": {}}` never returns — 90 s, zero bytes, `retries: 1` | [Serverless]({{ '/serverless/' | relative_url }}) |
| `/runsync` can return `IN_PROGRESS`, not just `COMPLETED` | [Client SDK]({{ '/sdk/client/' | relative_url }}) |
| Returning `{"error": ...}` fails the job — it is a control key, not data | [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| Terraform provider v1.0.9 is published but its schema will not load | [Terraform]({{ '/terraform/' | relative_url }}) |
| Homebrew's `terraform` is frozen at 1.5.7 and cannot install the provider | [Terraform]({{ '/terraform/' | relative_url }}) |

Runpod's own documentation and background articles are collected under [Readings]({{ '/readings/' | relative_url }}).

### License

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE). Take anything here and use it.

`serverless/01-hello-worker` derives from `runpod-workers/worker-template`, which is MIT licensed; its copyright notice travels with the repo in [NOTICE](https://github.com/litkhai/runpod-hols/blob/main/NOTICE).

### Not affiliated with Runpod

An independent learning exercise. Nothing here is reviewed or endorsed by Runpod. Where it disagrees with the official documentation, the disagreement is recorded with evidence — but the official docs remain the authority.

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

[Runpod](https://runpod.io) 을 배우면서 작성한 비공식 실습 자료입니다. 소스는 [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols) 에 있습니다.

목표는 Runpod SDK 와 그 주변 AI 인프라를, 읽어서가 아니라 직접 돌려보면서 이해하는 것입니다.

### 여기 있는 것은 전부 실행해본 것입니다

명령 출력, 이미지 크기, 지연시간 수치, 오류 메시지는 실제 계정에서 얻었습니다. 아직 실행하지 **않은** 것 — `terraform apply`, Pod 트랙 — 은 그렇다고 명시합니다.

| 발견 | 문서 위치 |
|---|---|
| 콘솔의 **Build context** 필드가 미문서화, 하위 디렉토리 Dockerfile 에는 필수 | [Serverless]({{ '/serverless/' | relative_url }}) |
| `{"input": {}}` 은 응답이 오지 않음 — 90초, 0바이트, `retries: 1` | [Serverless]({{ '/serverless/' | relative_url }}) |
| `/runsync` 가 `COMPLETED` 뿐 아니라 `IN_PROGRESS` 도 반환 | [Client SDK]({{ '/sdk/client/' | relative_url }}) |
| `{"error": ...}` 반환은 작업을 실패시킴 — 데이터가 아니라 제어 키 | [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| Terraform 프로바이더 v1.0.9 는 배포됐지만 스키마가 로드되지 않음 | [Terraform]({{ '/terraform/' | relative_url }}) |
| Homebrew 의 `terraform` 은 1.5.7 에 멈춰 있어 프로바이더 설치 불가 | [Terraform]({{ '/terraform/' | relative_url }}) |

Runpod 공식 문서와 배경 자료는 [Readings]({{ '/readings/' | relative_url }}) 에 모아두었습니다.

### 라이선스

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE). 여기 있는 것은 무엇이든 가져다 쓰셔도 됩니다.

`serverless/01-hello-worker` 는 MIT 라이선스인 `runpod-workers/worker-template` 에서 파생됐으며, 원본 저작권 표시는 [NOTICE](https://github.com/litkhai/runpod-hols/blob/main/NOTICE) 에 함께 담았습니다.

### Runpod 과 무관합니다

독립적인 학습 자료입니다. 여기 있는 어떤 내용도 Runpod 의 검토나 승인을 거치지 않았습니다. 공식 문서와 어긋나는 부분은 근거와 함께 기록했지만, 공식 문서가 여전히 권위 있는 출처입니다.

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

一套非官方的 [Runpod](https://runpod.io) 实践实验，在学习这个平台的过程中写成。源代码在 [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols)。

目标是通过实际运行，而不是阅读，来理解 Runpod SDK 及其周边的 AI 基础设施。

### 这里的一切都实际运行过

命令输出、镜像大小、延迟数据和错误信息都来自真实账号。凡是**没有**运行过的内容——`terraform apply`、Pod 路线——页面上都会注明。

| 发现 | 记录位置 |
|---|---|
| 控制台的 **Build context** 字段没有文档说明，而子目录中的 Dockerfile 必须填写它 | [Serverless]({{ '/serverless/' | relative_url }}) |
| `{"input": {}}` 永远不会返回——90 秒，零字节，`retries: 1` | [Serverless]({{ '/serverless/' | relative_url }}) |
| `/runsync` 可能返回 `IN_PROGRESS`，而不只是 `COMPLETED` | [Client SDK]({{ '/sdk/client/' | relative_url }}) |
| 返回 `{"error": ...}` 会使作业失败——它是控制键，不是数据 | [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| Terraform provider v1.0.9 已发布，但其 schema 无法加载 | [Terraform]({{ '/terraform/' | relative_url }}) |
| Homebrew 的 `terraform` 停留在 1.5.7，无法安装该 provider | [Terraform]({{ '/terraform/' | relative_url }}) |

Runpod 官方文档和背景文章汇总在 [Readings]({{ '/readings/' | relative_url }})。

### 许可证

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE)。这里的任何内容都可以拿去使用。

`serverless/01-hello-worker` 派生自采用 MIT 许可证的 `runpod-workers/worker-template`，其版权声明随仓库一起保存在 [NOTICE](https://github.com/litkhai/runpod-hols/blob/main/NOTICE) 中。

### 与 Runpod 无关

这是一个独立的学习项目。这里的任何内容都未经 Runpod 审阅或认可。与官方文档不一致之处都附有证据记录——但官方文档仍是权威来源。

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

[Runpod](https://runpod.io) の非公式ハンズオンラボ集です。プラットフォームを学びながら書きました。ソースは [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols) にあります。

目的は、Runpod SDK とその周辺の AI インフラを、読むのではなく実際に動かして理解することです。

### ここにあるものはすべて実行済みです

コマンド出力、イメージサイズ、レイテンシの数値、エラーメッセージは実際のアカウントで得たものです。実行して**いない**もの（`terraform apply`、Pod トラック）は、ページにそう明記しています。

| 発見 | 記載場所 |
|---|---|
| コンソールの **Build context** フィールドはドキュメント化されておらず、サブディレクトリの Dockerfile には必須 | [Serverless]({{ '/serverless/' | relative_url }}) |
| `{"input": {}}` は返ってこない（90 秒、0 バイト、`retries: 1`） | [Serverless]({{ '/serverless/' | relative_url }}) |
| `/runsync` は `COMPLETED` だけでなく `IN_PROGRESS` も返しうる | [Client SDK]({{ '/sdk/client/' | relative_url }}) |
| `{"error": ...}` を返すとジョブが失敗する（データではなく制御キー） | [Worker SDK]({{ '/sdk/worker/' | relative_url }}) |
| Terraform プロバイダ v1.0.9 は公開されているが、スキーマが読み込めない | [Terraform]({{ '/terraform/' | relative_url }}) |
| Homebrew の `terraform` は 1.5.7 で止まっており、プロバイダをインストールできない | [Terraform]({{ '/terraform/' | relative_url }}) |

Runpod 公式ドキュメントと背景記事は [Readings]({{ '/readings/' | relative_url }}) にまとめています。

### ライセンス

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE)。ここにあるものは何でも自由に使ってください。

`serverless/01-hello-worker` は MIT ライセンスの `runpod-workers/worker-template` から派生しており、その著作権表示は [NOTICE](https://github.com/litkhai/runpod-hols/blob/main/NOTICE) としてリポジトリに同梱しています。

### Runpod とは無関係です

独立した学習プロジェクトです。ここにある内容は Runpod によるレビューや承認を受けていません。公式ドキュメントと食い違う点は根拠とともに記録していますが、権威ある情報源はあくまで公式ドキュメントです。

</div>
