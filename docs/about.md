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

That matters because it is what makes the disagreements trustworthy:

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

공식 문서와 어긋나는 지점을 신뢰할 수 있게 만드는 것이 이 원칙입니다.

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
