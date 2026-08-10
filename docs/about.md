---
layout: default
title: About
permalink: /about/
---

# About This Repository

<div class="lang" data-lang="en" markdown="1">

## English

An unofficial, self-directed set of hands-on labs for [Runpod](https://runpod.io), written while learning the platform. Source at [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols).

### What it is for

Understanding the Runpod SDK and the surrounding AI infrastructure by using them, rather than by reading about them. Each track is something you run on a real account and observe.

### Everything is verified by running it

Command output, image sizes, latency figures and error messages in these pages were produced against a real account. Where something has **not** been run — `terraform apply`, the Pod track — the page says so.

That distinction carries the whole value. This repo is only worth more than the official docs where it contradicts or completes them, and it can only claim that honestly if you can tell verified from assumed.

Some of what that turned up:

| Finding | How it surfaced |
|---|---|
| `worker-template`'s README describes a `src/` directory it does not have | Reading the repo alongside the docs |
| The console's **Build context** field is undocumented, and is required for a nested Dockerfile | Two failed builds, then a build log |
| `{"input": {}}` never returns — 90 s, zero bytes, `retries: 1` | Calling the endpoint; `health()` later showed the failures |
| `/runsync` can return `IN_PROGRESS`, not just `COMPLETED` | Same |
| Returning `{"error": ...}` fails the job; it is a control key, not data | Reading the SDK source, then running each case |
| The SDK's cached-model path disagrees with the docs | Reading `rp_model_cache.py` |
| Terraform provider v1.0.9 is published but its schema will not load | `terraform init` |
| Homebrew's `terraform` is frozen at 1.5.7 and cannot install the provider | Trying it |

### Conventions

**Labs are self-contained.** Each lab directory holds a `Dockerfile` with bare `COPY` paths, so the folder builds alone and can be lifted out unchanged. This mirrors Runpod's own layout: `runpod-workers/*` is one repo per worker, and the `runpod/containers` monorepo sets a per-target `context` rather than reaching across directories. The cost is that deploying from a subdirectory needs the console's **Build context** field.

**Bilingual, English first.** Every page carries a full English section and a full Korean one. Interface text — nav, footer — stays English; the toggle governs content, not chrome.

**Flat top level.** `setup / serverless / pod / cluster / terraform` sit side by side. The repository name already says these are labs, so a `labs/` wrapper would only repeat it.

### How this site is built

`docs/` builds to GitHub Pages through a workflow that runs on every push touching it.

| Choice | Why |
|---|---|
| Jekyll with a hand-written layout, no remote theme | No upstream gem to break; full control over the bilingual toggle |
| Palette from Runpod's own assets | `docs.json` and the logo SVGs, not invented colours |
| Dark by default, light opt-in | A `<head>` guard applies the saved theme before first paint |
| Contents built in the browser | Each page holds both languages; a server-rendered list would duplicate every heading, and half the anchors would point into a hidden block |

Preview locally without installing Ruby:

```bash
docker run --rm -v "$PWD/docs":/site -w /site -p 4000:4000 ruby:3.3 \
  bash -c "gem install jekyll -N && jekyll serve --host 0.0.0.0"
```

### License

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE). Take anything here and use it.

`serverless/01-hello-worker` derives from `runpod-workers/worker-template`, which is MIT licensed, and the LICENSE file carries its copyright notice as MIT requires. The Python SDK, container images and Terraform provider this repo builds on are MIT as well.

### Not affiliated with Runpod

An independent learning exercise. Nothing here is reviewed or endorsed by Runpod. Where it disagrees with the official documentation, the disagreement is recorded with the evidence — but the official docs remain the authority.

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

[Runpod](https://runpod.io) 을 배우면서 작성한 비공식 실습 자료입니다. 소스는 [litkhai/runpod-hols](https://github.com/litkhai/runpod-hols) 에 있습니다.

### 목적

Runpod SDK 와 그 주변의 AI 인프라를, 읽어서가 아니라 **직접 써보면서** 이해하는 것입니다. 각 트랙은 실제 계정에서 실행하고 관찰하는 대상입니다.

### 모든 것은 실행해서 검증합니다

이 페이지들의 명령 출력, 이미지 크기, 지연시간 수치, 오류 메시지는 실제 계정에서 얻은 것입니다. 아직 실행하지 **않은** 것 — `terraform apply`, Pod 트랙 — 은 그렇다고 명시합니다.

이 구분이 전체 가치를 지탱합니다. 이 저장소가 공식 문서보다 가치 있는 지점은 공식 문서와 어긋나거나 그것을 보완하는 부분뿐이고, 검증된 것과 가정한 것을 구별할 수 있어야 그 주장이 정직해집니다.

그렇게 드러난 것들입니다.

| 발견 | 드러난 경로 |
|---|---|
| `worker-template` README 가 존재하지 않는 `src/` 디렉토리를 설명함 | 문서와 저장소를 나란히 읽다가 |
| 콘솔의 **Build context** 필드가 문서화돼 있지 않고, 하위 디렉토리 Dockerfile 에는 필수 | 빌드 두 번 실패 후 빌드 로그에서 |
| `{"input": {}}` 은 응답이 오지 않음 — 90초, 0바이트, `retries: 1` | 엔드포인트 호출. 이후 `health()` 가 실패 기록을 보여줌 |
| `/runsync` 가 `COMPLETED` 뿐 아니라 `IN_PROGRESS` 도 반환 | 위와 동일 |
| `{"error": ...}` 반환은 작업을 실패시킴. 데이터가 아니라 제어 키 | SDK 소스를 읽고 각 경우를 실행 |
| SDK 의 모델 캐시 경로가 문서와 다름 | `rp_model_cache.py` 를 읽다가 |
| Terraform 프로바이더 v1.0.9 는 배포됐지만 스키마가 로드되지 않음 | `terraform init` |
| Homebrew 의 `terraform` 은 1.5.7 에 멈춰 있어 프로바이더 설치 불가 | 실제로 해보다가 |

### 관례

**실습은 자체 완결적입니다.** 각 실습 디렉토리는 접두사 없는 `COPY` 경로의 `Dockerfile` 을 갖고 있어 폴더 단독으로 빌드되고 그대로 옮겨도 동작합니다. Runpod 의 구성 방식과 같습니다. `runpod-workers/*` 는 워커마다 저장소를 두고, `runpod/containers` 모노레포는 디렉토리를 가로지르는 대신 타겟마다 `context` 를 지정합니다. 대신 하위 디렉토리에서 배포할 때 콘솔의 **Build context** 필드가 필요합니다.

**영문 우선 이중 언어.** 모든 페이지가 완전한 영문 절과 완전한 한글 절을 담습니다. 인터페이스 텍스트(네비게이션, 푸터)는 영문을 유지합니다. 토글이 관장하는 것은 본문이지 UI 가 아닙니다.

**평평한 최상위.** `setup / serverless / pod / cluster / terraform` 이 나란히 놓입니다. 저장소 이름이 이미 실습임을 말하므로 `labs/` 로 한 번 더 감쌀 이유가 없습니다.

### 이 사이트의 빌드 방식

`docs/` 가 해당 디렉토리를 건드리는 푸시마다 워크플로를 통해 GitHub Pages 로 배포됩니다.

| 선택 | 이유 |
|---|---|
| 원격 테마 없이 직접 작성한 Jekyll 레이아웃 | 깨질 외부 gem 이 없고, 이중 언어 토글을 완전히 제어 |
| Runpod 공식 자산에서 가져온 색상 | 임의로 고른 색이 아니라 `docs.json` 과 로고 SVG 기준 |
| 기본 다크, 라이트는 선택 | `<head>` 가드가 첫 페인트 전에 저장된 테마를 적용 |
| 목차를 브라우저에서 생성 | 각 페이지가 두 언어를 담고 있어, 서버에서 만들면 제목이 두 배가 되고 앵커 절반이 숨겨진 블록을 가리킴 |

Ruby 설치 없이 로컬에서 미리 보려면:

```bash
docker run --rm -v "$PWD/docs":/site -w /site -p 4000:4000 ruby:3.3 \
  bash -c "gem install jekyll -N && jekyll serve --host 0.0.0.0"
```

### 라이선스

[MIT](https://github.com/litkhai/runpod-hols/blob/main/LICENSE). 여기 있는 것은 무엇이든 가져다 쓰셔도 됩니다.

`serverless/01-hello-worker` 는 MIT 라이선스인 `runpod-workers/worker-template` 에서 파생됐으며, MIT 가 요구하는 대로 LICENSE 파일에 원본 저작권 표시를 포함했습니다. 이 저장소가 기반으로 삼는 Python SDK, 컨테이너 이미지, Terraform 프로바이더도 모두 MIT 입니다.

### Runpod 과 무관합니다

독립적인 학습 자료입니다. 여기 있는 어떤 내용도 Runpod 의 검토나 승인을 거치지 않았습니다. 공식 문서와 어긋나는 부분은 근거와 함께 기록했지만, 공식 문서가 여전히 권위 있는 출처입니다.

</div>
