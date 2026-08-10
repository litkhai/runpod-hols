# SDK Reference

[English](#english) | [한국어](#한국어)

---

## English

The `runpod` Python package is two halves that share a name and never meet. Which one you are reading about depends on **where the code runs**.

| | Runs | Entry point | Reference |
|---|---|---|---|
| **Worker** | Inside the container, to *be* an endpoint | `runpod.serverless.start()` | [worker.md](./worker.md) |
| **Client** | On your machine, to *call and manage* Runpod | `runpod.Endpoint`, `runpod.api.*` | [client.md](./client.md) |

The handler contract is one section of the worker half, not a peer of the SDK — a distinction the earlier layout of these docs got wrong.

| Half | Covers |
|---|---|
| [Worker](./worker.md) | Handler contract · startup fitness checks · handler utilities · internals · local development |
| [Client](./client.md) | `Endpoint` / `Job` · control plane · AI agent detection · the bundled `runpod` CLI |

Both were read out of the installed source (`runpod` 1.11.0) and confirmed by running them. Where behaviour is surprising, the observed output is included.

---

## 한국어

`runpod` Python 패키지는 이름만 공유하고 서로 만나지 않는 두 절반입니다. 어느 쪽 이야기인지는 **코드가 어디서 도는가**로 갈립니다.

| | 실행 위치 | 진입점 | 문서 |
|---|---|---|---|
| **Worker** | 컨테이너 안. 엔드포인트가 *되기* 위해 | `runpod.serverless.start()` | [worker.md](./worker.md) |
| **Client** | 내 컴퓨터. Runpod 을 *호출하고 관리*하기 위해 | `runpod.Endpoint`, `runpod.api.*` | [client.md](./client.md) |

Handler 계약은 SDK 와 나란한 항목이 아니라 **워커 절반의 한 절**입니다. 이전 문서 구성이 잘못 표현했던 부분입니다.

| 절반 | 다루는 내용 |
|---|---|
| [Worker](./worker.md) | Handler 계약 · 기동 시 fitness check · handler 유틸리티 · 내부 동작 · 로컬 개발 |
| [Client](./client.md) | `Endpoint` / `Job` · 컨트롤 플레인 · AI 에이전트 감지 · 함께 설치되는 `runpod` CLI |

두 문서 모두 설치된 소스(`runpod` 1.11.0)를 직접 읽고 실행해 확인했습니다. 동작이 직관과 다른 부분은 실제 출력을 함께 실었습니다.
