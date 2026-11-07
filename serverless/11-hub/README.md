# Serverless Lab 11 — One-Click Deploy from the Hub

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** deploy a ready-made worker from the **Runpod Hub** in the console, measure its first and warm requests, and look at what the console created on your behalf.

**Time:** ~15 minutes · **Cost:** a few cents on a 16 GB GPU pool (2026-11-07)

### Files

| File | Role |
|---|---|
| `call.py` | Sends the listing's sample request (`gettysburg.wav`) with `/run` and records `delayTime`, `executionTime`, worker id and the transcription |
| `results/calls.jsonl` | The eight calls below |

### Steps

1. Console → **Hub** → **Serverless Repos** → **Faster Whisper** (runpod-workers, v1.0.10, 2,335 deploys).
2. **Deploy 1.0.10** → a dialog for environment variables (none for this repo) → **Next**.
3. Deployment type **Endpoint**, then a GPU pool. **Check the pool before you click Create Endpoint:** the dialog preselected the *24 GB PRO* pool at USD 1.34/hr. This lab unticked it and kept only the 16 GB pool at USD 0.58/hr — four GPU types, which is what the "4 GPUs" badge counts.
4. **Create Endpoint**. The endpoint page opens with a Quick start already filled with the sample input.

```bash
python3 call.py <endpoint_id> --label cold_turbo
python3 call.py <endpoint_id> --label first_large_v3 --model large-v3
```

### What the console created

| Setting | Value |
|---|---|
| Image | `registry.runpod.net/runpod-workers-worker-faster-whisper-main-dockerfile:bd500dc88` — built from the repo's `main` by Runpod, not pulled from Docker Hub |
| GPU types | RTX A4000, RTX A4500, RTX 4000 Ada, RTX 2000 Ada; every worker landed on an RTX A4500 in EU-RO-1 |
| Workers | max 3, min 0, idle timeout 5 s, queue delay 4 s, FlashBoot on |
| Execution timeout | 600 s |
| CUDA | 12.3–12.7 allowed |
| Template env | empty — no keys or tokens |
| Worker SDK | `runpod` 1.7.9 (the labs here use 1.12) |

`rp endpoint workers` listed five workers for this max-3 endpoint, all idle until called.

### Requests (2026-11-07, 10 s of audio)

| Call | `delayTime` | `executionTime` |
|---|---|---|
| First, `turbo` | 8.9 s | 6.5 s |
| Warm, `turbo` (×3) | 0.09 s | 0.88–0.89 s |
| After 90 s idle, `turbo` — a different worker | 9.5 s | 5.7 s |
| First `large-v3` on that worker | 0.09 s | 6.4 s |
| Second `large-v3` | 0.10 s | 1.2 s |
| First `base` | 0.09 s | 1.5 s |

- **Cold starts were under 10 s** because the image was already on the hosts: the log shows "Image is up to date" and no model download.
- **The worker holds one model at a time.** Each change of `model` unloaded the previous one and loaded the new one (large-v3: ~5 s). Pin one model per endpoint if callers mix them.
- The console's Quick start sends `"transcription": "plain text"` instead of the documented `plain_text`; the worker accepted it and returned plain text.

The endpoint was deleted after the run; its template is held by the platform for up to 90 minutes after the delete, as with every endpoint here.

---

## 한국어

**목표:** 콘솔에서 **Runpod Hub** 의 기성 워커를 배포하고, 첫 요청과 웜 요청을 재고, 콘솔이 대신 만든 것을 살펴본다.

**시간:** 약 15분 · **비용:** 16 GB GPU 풀에서 몇 센트 (2026-11-07)

### 파일

| 파일 | 역할 |
|---|---|
| `call.py` | 목록의 예제 요청 (`gettysburg.wav`) 을 `/run` 으로 보내고 `delayTime`, `executionTime`, 워커 id, 전사 결과를 기록 |
| `results/calls.jsonl` | 아래 여덟 번의 호출 |

### 단계

1. 콘솔 → **Hub** → **Serverless Repos** → **Faster Whisper** (runpod-workers, v1.0.10, 배포 2,335회).
2. **Deploy 1.0.10** → 환경 변수 대화상자 (이 저장소는 없음) → **Next**.
3. 배포 유형 **Endpoint**, 그다음 GPU 풀. **Create Endpoint 를 누르기 전에 풀을 확인하자:** 대화상자는 USD 1.34/hr 의 *24 GB PRO* 풀을 미리 골라 두었다. 이 실습은 그것을 해제하고 USD 0.58/hr 의 16 GB 풀만 남겼다 — GPU 종류 네 개이고, "4 GPUs" 배지가 세는 것이 이것이다.
4. **Create Endpoint**. 엔드포인트 페이지가 열리고, Quick start 에 예제 입력이 채워져 있다.

```bash
python3 call.py <endpoint_id> --label cold_turbo
python3 call.py <endpoint_id> --label first_large_v3 --model large-v3
```

### 콘솔이 만든 것

| 설정 | 값 |
|---|---|
| 이미지 | `registry.runpod.net/runpod-workers-worker-faster-whisper-main-dockerfile:bd500dc88` — Docker Hub 가 아니라 Runpod 이 저장소의 `main` 으로 빌드 |
| GPU 종류 | RTX A4000, RTX A4500, RTX 4000 Ada, RTX 2000 Ada; 워커는 모두 EU-RO-1 의 RTX A4500 |
| 워커 | 최대 3, 최소 0, 유휴 타임아웃 5초, queue delay 4초, FlashBoot 켬 |
| 실행 시간 제한 | 600초 |
| CUDA | 12.3–12.7 허용 |
| 템플릿 env | 비어 있음 — 키나 토큰 없음 |
| 워커 SDK | `runpod` 1.7.9 (이 저장소의 실습은 1.12) |

`rp endpoint workers` 는 최대 3 인 이 엔드포인트에 워커 다섯 개를 보여 줬고, 호출 전까지 모두 idle 이었다.

### 요청 (2026-11-07, 10초 오디오)

| 호출 | `delayTime` | `executionTime` |
|---|---|---|
| 첫 호출, `turbo` | 8.9초 | 6.5초 |
| 웜, `turbo` (3회) | 0.09초 | 0.88–0.89초 |
| 90초 유휴 뒤, `turbo` — 다른 워커 | 9.5초 | 5.7초 |
| 그 워커의 첫 `large-v3` | 0.09초 | 6.4초 |
| 두 번째 `large-v3` | 0.10초 | 1.2초 |
| 첫 `base` | 0.09초 | 1.5초 |

- **콜드 스타트가 10초 미만이었다.** 이미지가 이미 호스트에 있었기 때문이다: 로그에 "Image is up to date" 가 있고 모델 다운로드는 없었다.
- **워커는 한 번에 모델 하나만 들고 있다.** `model` 을 바꿀 때마다 이전 모델을 내리고 새 모델을 올렸다 (large-v3: 약 5초). 호출자가 모델을 섞는다면 엔드포인트마다 모델 하나로 고정한다.
- 콘솔의 Quick start 는 문서의 `plain_text` 대신 `"transcription": "plain text"` 를 보낸다. 워커는 받아들였고 일반 텍스트를 돌려줬다.

엔드포인트는 실행 뒤 삭제했다. 이 저장소의 다른 엔드포인트처럼, 템플릿은 삭제 후 최대 90분 동안 플랫폼이 붙잡고 있다.
