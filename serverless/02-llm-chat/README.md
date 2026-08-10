# Lab 02 — LLM Chat Worker

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** serve a small instruct model on Serverless, deployed from GitHub, with the weights supplied by Runpod's cached-model store instead of the container image.

**Time:** ~30 minutes · **Cost:** GPU seconds only while a request is running

### Why this lab exists

Lab 01 taught the deploy loop, but a hello-world handler cannot show the thing that actually matters in Serverless: **where the model lives, and who pays for loading it.** This lab makes that visible.

| | Lab 01 | Lab 02 |
|---|---|---|
| Image | `python:3.11-slim`, 106MB | PyTorch CUDA runtime, ~4GB |
| Model | none | `Qwen/Qwen2.5-1.5B-Instruct`, not in the image |
| Deploy | Docker Hub or GitHub | GitHub |
| Teaches | handler, job, endpoint | cached models, cold start, module-scope loading |

### The key idea — three places a model can live

| Where | Cold start | Image size | Download billed? |
|---|---|---|---|
| Downloaded at runtime | Slow, every new worker | Small | **Yes** — you pay while it downloads |
| Baked into the image | Fast | Huge | No, but builds and pulls are slow |
| **Runpod cached model** | Seconds | Small | **No** |

Runpod's docs are explicit: *"You aren't billed for worker time while your model is being downloaded."* Workers on the same host share one copy. That is why this repo puts **code in Git and weights in the Model field** — they are not alternatives, they compose.

Cached models work with public, gated (supply a Hugging Face token) and private-but-on-Hugging-Face models. A private model *not* on Hugging Face has to be baked into the image instead.

### Files

| File | Role |
|---|---|
| `handler.py` | Loads the model at module scope, then answers one job per call |

> The SDK's handler contract — control keys, exceptions, streaming, concurrency — is documented in [sdk/worker.md](../../sdk/worker.md).
| `model_cache.py` | Resolves the cached snapshot path. Dependency-free, so it is unit-testable without CUDA |
| `requirements.txt` | `runpod`, `transformers`, `accelerate` — **not** `torch` |
| `Dockerfile` | `pytorch/pytorch:2.9.1-cuda12.6-cudnn9-runtime` |
| `.runpod/hub.json` | Hub metadata, exposes `MODEL_ID` as a configurable env var |

### Two things in `handler.py` worth reading

**1. Import order is load-bearing.**

```python
_CACHED_PATH = snapshot_path(MODEL_ID)     # before transformers
if _CACHED_PATH:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
```

`HF_HUB_OFFLINE` is read when `huggingface_hub` is imported. Set it afterwards and it silently does nothing — you would think you were serving from cache while actually downloading on the clock. Hence the dependency-free `model_cache` module: it can run before the heavy imports.

**2. The docs and the SDK disagree about where the cache lives.**

| Source | Path |
|---|---|
| Docs (`serverless/development/huggingface-models`) | `/runpod-volume/huggingface-cache/hub/models--<org>--<name>/snapshots/<rev>` |
| SDK (`runpod.serverless.utils.rp_model_cache`, v1.11.0) | `/runpod/cache/<org>/<name>/<revision>` |

Which one an endpoint actually populates is undocumented, so `model_cache.py` probes both — two `stat()` calls at import, and no guess.

**3. It falls back to the Hub when there is no cache.**

`snapshot_path()` returns `None` rather than raising, so the same file runs locally (downloads from the Hub) and on Runpod (loads from cache). Runpod's own example raises here, which makes its handler impossible to test off-platform.

The response reports which path was taken:

```json
{ "loaded_from": "cache", "model_load_seconds": 4.1, "device": "cuda:0" }
```

### Step 1 — Deploy from GitHub

Nothing to build locally. Runpod clones the repo, builds the image and stores it in its own registry.

1. Console → [Settings](https://console.runpod.io/user/settings) → **Connections** → **GitHub** → **Connect**.
2. [Serverless](https://console.runpod.io/serverless) → **New Endpoint** → **Import Git Repository** → `runpod-hols`.
3. **Branch** `main`, **Dockerfile Path** `/serverless/02-llm-chat/Dockerfile`, **Advanced settings → Build context** `/serverless/02-llm-chat`. The build context is required and confirmed working — without it the build fails with `"/handler.py": not found`. Save it before triggering a build.
4. In **Endpoint Configuration**, set **Model** to `Qwen/Qwen2.5-1.5B-Instruct`. The console shows the model size and the GPU it suggests.
5. **Active Workers 0**, **Max Workers** 1–2, GPU per the console's suggestion (16GB is ample for 1.5B).
6. **Deploy Endpoint**, then watch the **Builds** tab.

> The first build pulls a ~4GB base image, so expect several minutes. Later builds reuse cached layers.

> **Use a release to redeploy.** The docs say a **GitHub release** is required; in testing a plain push also triggered builds, but only on an endpoint with no successful build yet. Treat the release as the reliable trigger, and get the config right before deploying — the iteration loop is slow.

### Step 2 — Call it

```bash
source ../../.env
curl -X POST "https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "What is Runpod Serverless in two sentences?", "max_tokens": 120}}'
```

Message form works too:

```json
{"input": {"messages": [
  {"role": "system", "content": "Answer with a single word."},
  {"role": "user", "content": "What colour is the sky on a clear day?"}
]}}
```

| Field | Default | Notes |
|---|---|---|
| `prompt` | — | Either this or `messages` |
| `messages` | — | `[{role, content}, …]` |
| `system` | "You are a concise, helpful assistant." | Ignored when `messages` is given |
| `max_tokens` | 256 | Clamped to 1024 |
| `temperature` | 0.7 | `0` disables sampling |
| `top_p` | 0.9 | |

### Step 3 — Watch the cold start

Send one request, wait for the worker to idle out, then send another. The first pays container start plus `model_load_seconds`; the second pays neither. That gap is exactly what module-scope loading buys, and why `workers_min = 0` trades latency for cost.

### Local testing

Possible but slow: on CPU a 1.5B model generates at a few tokens per second, and the first run downloads roughly 3GB.

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python torch transformers accelerate runpod
.venv/bin/python handler.py
```

The cache resolver is testable on its own with no dependencies at all:

```bash
python3 -c "from model_cache import snapshot_path; print(snapshot_path('Qwen/Qwen2.5-1.5B-Instruct'))"
# None locally — meaning the handler would fall back to the Hub
```

### Troubleshooting

| Symptom | Cause |
|---|---|
| `"/handler.py": not found` during build | **Build context** not set, or saved after the build was triggered. Put `/serverless/02-llm-chat` in Advanced settings and save before triggering |
| `loaded_from: "hub"` on Runpod | The endpoint's **Model** field is empty or does not match `MODEL_ID` |
| Very long first request | Model was downloaded, not cached — check the Model field |
| CUDA OOM | GPU too small; raise it or pick a smaller model |
| Changes not live | You pushed but did not create a **GitHub release** |

### Not yet verified

The deploy itself has not been run. Unverified: that this lab's build succeeds, and actual cold-start numbers. The build context question is settled: a Lab 01 deploy proved the console's Build context field works when saved before the build is triggered. Verified locally: `model_cache.py` against five fixture cases, the base image tag and model ID both resolve, and the handler compiles.

---

## 한국어

**목표:** 소형 instruct 모델을 Serverless 로 서빙합니다. 배포는 GitHub 연동으로, 가중치는 컨테이너 이미지가 아니라 Runpod 의 모델 캐시에서 공급받습니다.

**소요 시간:** 약 30분 · **비용:** 요청이 실행되는 동안의 GPU 시간만

### 이 랩이 필요한 이유

Lab 01 은 배포 흐름을 가르쳤지만, hello-world 핸들러로는 Serverless 에서 정작 중요한 것을 보여줄 수 없습니다. **모델이 어디에 있고, 그것을 로드하는 비용을 누가 내는가** 입니다. 이 랩이 그것을 드러냅니다.

| | Lab 01 | Lab 02 |
|---|---|---|
| 이미지 | `python:3.11-slim`, 106MB | PyTorch CUDA runtime, 약 4GB |
| 모델 | 없음 | `Qwen/Qwen2.5-1.5B-Instruct`, 이미지에 없음 |
| 배포 | Docker Hub 또는 GitHub | GitHub |
| 다루는 것 | handler, job, 엔드포인트 | 모델 캐싱, 콜드 스타트, 모듈 스코프 로딩 |

### 핵심 — 모델이 있을 수 있는 세 곳

| 위치 | 콜드 스타트 | 이미지 크기 | 다운로드 과금 |
|---|---|---|---|
| 런타임 다운로드 | 느림, 새 워커마다 | 작음 | **있음** — 받는 동안 과금 |
| 이미지에 굽기 | 빠름 | 매우 큼 | 없음, 대신 빌드·pull 이 느림 |
| **Runpod 모델 캐시** | 수 초 | 작음 | **없음** |

Runpod 문서에 명시돼 있습니다. *"You aren't billed for worker time while your model is being downloaded."* 같은 호스트의 워커들은 사본 하나를 공유합니다. 이 저장소가 **코드는 Git 에, 가중치는 Model 필드에** 두는 이유입니다. 둘은 양자택일이 아니라 함께 씁니다.

모델 캐싱은 public, gated(Hugging Face 토큰 필요), 그리고 Hugging Face 에 있는 private 모델까지 지원합니다. Hugging Face 에 *없는* private 모델이라면 이미지에 구워야 합니다.

### 파일 구성

| 파일 | 역할 |
|---|---|
| `handler.py` | 모듈 스코프에서 모델을 로드하고, 호출마다 작업 1건을 처리 |

> SDK 의 핸들러 계약(제어 키, 예외 처리, 스트리밍, 동시성)은 [sdk/worker.md](../../sdk/worker.md) 에 정리돼 있습니다.
| `model_cache.py` | 캐시된 스냅샷 경로 확인. 의존성이 없어 CUDA 없이도 단위 테스트 가능 |
| `requirements.txt` | `runpod`, `transformers`, `accelerate` — `torch` 는 **없음** |
| `Dockerfile` | `pytorch/pytorch:2.9.1-cuda12.6-cudnn9-runtime` |
| `.runpod/hub.json` | Hub 메타데이터, `MODEL_ID` 를 설정 가능한 환경변수로 노출 |

### `handler.py` 에서 눈여겨볼 두 가지

**1. import 순서가 동작에 영향을 줍니다.**

```python
_CACHED_PATH = snapshot_path(MODEL_ID)     # transformers 보다 먼저
if _CACHED_PATH:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
```

`HF_HUB_OFFLINE` 는 `huggingface_hub` 가 import 될 때 읽힙니다. 그 뒤에 설정하면 아무 효과 없이 조용히 무시되고, 캐시에서 서빙한다고 믿는 동안 실제로는 과금되며 다운로드하게 됩니다. 무거운 import 앞에서 실행될 수 있도록 `model_cache` 모듈을 의존성 없이 분리한 이유입니다.

**2. 문서와 SDK 가 캐시 위치를 다르게 말합니다.**

| 출처 | 경로 |
|---|---|
| 문서 (`serverless/development/huggingface-models`) | `/runpod-volume/huggingface-cache/hub/models--<org>--<name>/snapshots/<rev>` |
| SDK (`runpod.serverless.utils.rp_model_cache`, v1.11.0) | `/runpod/cache/<org>/<name>/<revision>` |

엔드포인트가 실제로 어느 쪽을 채우는지는 문서화돼 있지 않습니다. 그래서 `model_cache.py` 가 양쪽을 모두 확인합니다. import 시점의 `stat()` 두 번이면 되므로 추측할 이유가 없습니다.

**3. 캐시가 없으면 Hub 로 폴백합니다.**

`snapshot_path()` 는 예외를 던지지 않고 `None` 을 반환합니다. 덕분에 같은 파일이 로컬(Hub 다운로드)과 Runpod(캐시 로드) 양쪽에서 동작합니다. Runpod 공식 예제는 여기서 예외를 던지기 때문에 플랫폼 밖에서는 테스트할 수 없습니다.

응답이 어느 경로를 탔는지 알려줍니다.

```json
{ "loaded_from": "cache", "model_load_seconds": 4.1, "device": "cuda:0" }
```

### 1단계 — GitHub 연동 배포

로컬에서 빌드할 것이 없습니다. Runpod 이 저장소를 클론해 이미지를 빌드하고 자체 레지스트리에 저장합니다.

1. 콘솔 → [Settings](https://console.runpod.io/user/settings) → **Connections** → **GitHub** → **Connect**.
2. [Serverless](https://console.runpod.io/serverless) → **New Endpoint** → **Import Git Repository** → `runpod-hols`.
3. **Branch** `main`, **Dockerfile Path** `/serverless/02-llm-chat/Dockerfile`, **Advanced settings → Build context** `/serverless/02-llm-chat`. Build context 는 필수이며 동작이 확인됐습니다. 지정하지 않으면 `"/handler.py": not found` 로 실패합니다. 빌드 트리거 전에 저장하세요.
4. **Endpoint Configuration** 에서 **Model** 에 `Qwen/Qwen2.5-1.5B-Instruct` 입력. 콘솔이 모델 크기와 권장 GPU 를 표시합니다.
5. **Active Workers 0**, **Max Workers** 1~2, GPU 는 콘솔 권장값 (1.5B 에는 16GB 로 충분).
6. **Deploy Endpoint** 후 **Builds** 탭에서 진행 확인.

> 첫 빌드는 약 4GB 베이스 이미지를 받으므로 수 분 걸립니다. 이후 빌드는 레이어 캐시를 재사용합니다.

> **재배포는 릴리스로 하세요.** 문서는 **GitHub 릴리스**가 필요하다고 하고, 실제로는 일반 푸시도 빌드를 트리거했지만 성공한 빌드가 없던 엔드포인트에서만 확인됐습니다. 릴리스를 확실한 트리거로 보시고, 반복 주기가 느리므로 배포 전에 설정을 제대로 잡아두세요.

### 2단계 — 호출

```bash
source ../../.env
curl -X POST "https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "Runpod Serverless 를 두 문장으로 설명해줘", "max_tokens": 120}}'
```

메시지 형식도 됩니다.

```json
{"input": {"messages": [
  {"role": "system", "content": "한 단어로만 답하세요."},
  {"role": "user", "content": "맑은 날 하늘은 무슨 색인가요?"}
]}}
```

| 필드 | 기본값 | 비고 |
|---|---|---|
| `prompt` | — | `messages` 와 둘 중 하나 |
| `messages` | — | `[{role, content}, …]` |
| `system` | "You are a concise, helpful assistant." | `messages` 를 주면 무시됨 |
| `max_tokens` | 256 | 1024 로 상한 |
| `temperature` | 0.7 | `0` 이면 샘플링 비활성화 |
| `top_p` | 0.9 | |

### 3단계 — 콜드 스타트 관찰

요청을 한 번 보내고, 워커가 유휴 종료될 때까지 기다렸다가 다시 보내보세요. 첫 요청은 컨테이너 기동과 `model_load_seconds` 를 모두 부담하고, 두 번째는 둘 다 부담하지 않습니다. 이 차이가 모듈 스코프 로딩이 만들어내는 이득이며, `workers_min = 0` 이 지연시간과 비용을 맞바꾸는 지점입니다.

### 로컬 테스트

가능하지만 느립니다. CPU 에서 1.5B 모델은 초당 몇 토큰 수준이고, 첫 실행에서 약 3GB 를 받습니다.

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python torch transformers accelerate runpod
.venv/bin/python handler.py
```

캐시 확인 로직은 의존성 없이 단독으로 테스트할 수 있습니다.

```bash
python3 -c "from model_cache import snapshot_path; print(snapshot_path('Qwen/Qwen2.5-1.5B-Instruct'))"
# 로컬에서는 None — 핸들러가 Hub 로 폴백한다는 뜻
```

### 문제 해결

| 증상 | 원인 |
|---|---|
| 빌드 중 `"/handler.py": not found` | **Build context** 미지정이거나, 빌드 트리거 후에 저장한 경우. Advanced settings 에 `/serverless/02-llm-chat` 를 넣고 저장한 뒤 트리거할 것 |
| Runpod 에서 `loaded_from: "hub"` | 엔드포인트 **Model** 필드가 비었거나 `MODEL_ID` 와 불일치 |
| 첫 요청이 지나치게 오래 걸림 | 캐시가 아니라 다운로드한 것. Model 필드 확인 |
| CUDA OOM | GPU 가 작음. 사양을 올리거나 더 작은 모델 사용 |
| 변경사항이 반영되지 않음 | 푸시만 하고 **GitHub 릴리스**를 만들지 않음 |

### 아직 검증하지 않은 것

실제 배포는 아직 실행하지 않았습니다. 미검증: 이 랩의 빌드 성공 여부와 실제 콜드 스타트 수치. 빌드 컨텍스트 문제는 Lab 01 배포로 해결됐습니다. 콘솔의 Build context 필드는 빌드 트리거 전에 저장하면 정상 동작합니다. 로컬에서 검증한 것: `model_cache.py` 픽스처 5개 케이스, 베이스 이미지 태그와 모델 ID 실재 확인, 핸들러 컴파일.
