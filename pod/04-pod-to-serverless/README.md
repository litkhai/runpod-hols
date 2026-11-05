# Pod Lab 04 — From a Pod to Serverless Through a Network Volume

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** write and test a handler on a GPU Pod, then serve the very same file from a Serverless endpoint — no image build — by putting both on one network volume.

**Time:** ~30 minutes · **Cost:** an RTX 4090 Pod for ~15 minutes plus two Serverless jobs; under $0.40 on 2026-11-05

### The idea

| | Pod (develop) | Serverless worker (serve) |
|---|---|---|
| Image | `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404` | Same |
| Network volume mounted at | `/workspace` | `/runpod-volume` |
| Your code | `/workspace/app/handler.py` | `/runpod-volume/app/handler.py` — the same file |
| Python packages | `pip install --target /workspace/app/deps` | `PYTHONPATH=/runpod-volume/app/deps` |
| Start | You, over SSH | Template `dockerStartCmd: ["python3", "-u", "/runpod-volume/app/handler.py"]` |

The usual way to ship a worker is to bake the code into an image, as [Serverless Lab 01](../../serverless/01-hello-worker) does. Sharing a volume skips the build, so you can edit on the Pod and the next cold worker runs the edit. The price is paid at every cold start: the worker imports from a network filesystem.

### Files

| File | Role |
|---|---|
| `handler.py` | The code under development: a GPU matrix multiply that reports which file it was loaded from |
| `lab.py` | Volume, Pod, template + endpoint, and a job, over the REST API; ids in `.p2s.json` |
| `common.py` | `.env` loading and REST calls, standard library only |

### Step 1 — Volume and a development Pod

```bash
cd pod/04-pod-to-serverless
python3 lab.py volume create        # 10 GB, EU-RO-1
python3 lab.py pod create           # RTX 4090, the volume at /workspace
python3 lab.py pod show             # SSH command, about 2 minutes after create
```

The endpoint can only use GPUs in the volume's data center, so pick one that stocks the GPU you will serve on.

### Step 2 — Develop and test on the Pod

```bash
scp -P <port> handler.py root@<ip>:/workspace/app/handler.py
ssh root@<ip> -p <port>
cd /workspace/app
pip install --target /workspace/app/deps runpod==1.12.0
PYTHONPATH=/workspace/app/deps python3 handler.py --test_input '{"input": {"n": 2048}}'
```

```
INFO   | Job result: {'output': {'device': 'NVIDIA GeForce RTX 4090', 'loaded_from': '/workspace/app/handler.py', 'runpod_sdk': '1.12.0', 'torch': '2.9.1+cu128', 'n': 2048, 'matmul_s': 0.081}}
```

`--test_input` runs the handler once, locally, the way the worker will. torch comes from the image; only `runpod` and its dependencies go on the volume.

**Writing many small files to the network volume is slow.** The `pip install --target` above took about ten minutes for 9,237 files. They hold 159 MB of data (`du --apparent-size`), yet `du` reported 2,016 MB. The test run itself took 35 s, most of it imports.

### Step 3 — Serve the same file

```bash
python3 lab.py pod delete
python3 lab.py endpoint create      # template with dockerStartCmd + PYTHONPATH, endpoint on the volume
python3 lab.py run                  # one job, polls until done
```

```json
{
  "delayTime": 205230,
  "executionTime": 204,
  "output": {
    "device": "NVIDIA GeForce RTX 4090",
    "loaded_from": "/runpod-volume/app/handler.py",
    "matmul_s": 0.0148,
    "n": 4096,
    "runpod_sdk": "1.12.0",
    "torch": "2.9.1+cu128"
  },
  "status": "COMPLETED"
}
```

`loaded_from` is the proof: the worker ran the file the Pod wrote. Two more things showed up:

- **`runsync` does not wait out a cold start.** It returned `{"status": "IN_QUEUE"}` with the job id after 90.9 s; the job finished at 205 s. `lab.py run` now polls `/status/{id}` after that.
- **The second job waited 47 s.** With `idleTimeout` 5 the first worker was gone, so the next container started again, this time from an image the host already had.

### Step 4 — Clean up

```bash
python3 lab.py endpoint delete
python3 lab.py volume delete
python3 lab.py status
```

The endpoint and the volume deleted at once. The template did not: *"Template is still held by deleted endpoint …, which is pending cleanup. It can be deleted once that endpoint's last worker has been billed, within about 90 minutes"* — the same as in [Serverless Lab 03](../../serverless/03-vllm-endpoint). `lab.py endpoint delete` keeps the template id; delete it later.

### When to use this, and when not

| Use a shared volume | Bake an image |
|---|---|
| Iterating: edit on a Pod, test on Serverless | Anything you call in production |
| Large files the worker should not download each time | Code that must not change under a running endpoint |
| One data center is enough | Workers in any data center |

The volume ties the endpoint to its data center, every cold start imports over the network, and whoever can write the volume changes what the endpoint runs.

### What was run

2026-11-05, Secure Cloud EU-RO-1, RTX 4090, `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404`, runpod SDK 1.12.0 on the volume, REST v1.

| Step | Result |
|---|---|
| Pod with the network volume | SSH after about 2 minutes |
| `pip install --target` onto the volume | About 10 minutes, 9,237 files; 159 MB apparent, 2,016 MB by `du` |
| `handler.py --test_input` on the Pod | Output above, 35 s |
| Endpoint with `dockerStartCmd` and `PYTHONPATH` on the same volume | Worker ran `/runpod-volume/app/handler.py` |
| First job | `runsync` returned `IN_QUEUE` at 90.9 s; `delayTime` 205 s, `executionTime` 0.2 s |
| Second job | `delayTime` 47 s, `executionTime` 0.2 s |
| Clean up | Endpoint and volume deleted at once; template deleted 92 min after the endpoint |

Not run: editing the handler on the Pod while the endpoint is live, a volume shared by a Pod and a worker at the same time, FlashBoot, another data center.

---

## 한국어

**목표:** GPU Pod 에서 핸들러를 작성하고 테스트한 뒤, 이미지 빌드 없이 바로 그 파일을 Serverless 엔드포인트에서 서빙합니다. 둘을 하나의 네트워크 볼륨에 올리는 방식입니다.

**소요 시간:** 약 30분 · **비용:** RTX 4090 Pod 약 15분과 Serverless 작업 두 개. 2026-11-05 기준 $0.40 미만

### 아이디어

| | Pod (개발) | Serverless 워커 (서빙) |
|---|---|---|
| 이미지 | `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404` | 같음 |
| 네트워크 볼륨 마운트 위치 | `/workspace` | `/runpod-volume` |
| 코드 | `/workspace/app/handler.py` | `/runpod-volume/app/handler.py` — 같은 파일 |
| Python 패키지 | `pip install --target /workspace/app/deps` | `PYTHONPATH=/runpod-volume/app/deps` |
| 시작 | SSH 로 직접 | 템플릿 `dockerStartCmd: ["python3", "-u", "/runpod-volume/app/handler.py"]` |

워커를 배포하는 일반적인 방법은 [Serverless Lab 01](../../serverless/01-hello-worker) 처럼 코드를 이미지에 굽는 것입니다. 볼륨을 공유하면 빌드를 건너뛰므로, Pod 에서 고친 것을 다음 콜드 워커가 바로 실행합니다. 대가는 콜드 스타트마다 치릅니다. 워커가 네트워크 파일시스템에서 import 합니다.

### 파일 구성

| 파일 | 역할 |
|---|---|
| `handler.py` | 개발 중인 코드. GPU 행렬곱을 하고 자신이 어느 파일에서 로드됐는지 보고 |
| `lab.py` | REST API 로 볼륨, Pod, 템플릿과 엔드포인트, 작업 실행. id 는 `.p2s.json` 에 기록 |
| `common.py` | `.env` 로딩과 REST 호출. 표준 라이브러리만 사용 |

### 1단계 — 볼륨과 개발용 Pod

```bash
cd pod/04-pod-to-serverless
python3 lab.py volume create        # 10 GB, EU-RO-1
python3 lab.py pod create           # RTX 4090, 볼륨은 /workspace
python3 lab.py pod show             # 생성 약 2분 뒤 SSH 명령 출력
```

엔드포인트는 볼륨이 있는 데이터센터의 GPU 만 쓸 수 있으니, 서빙할 GPU 가 있는 곳을 고르세요.

### 2단계 — Pod 에서 개발하고 테스트

```bash
scp -P <port> handler.py root@<ip>:/workspace/app/handler.py
ssh root@<ip> -p <port>
cd /workspace/app
pip install --target /workspace/app/deps runpod==1.12.0
PYTHONPATH=/workspace/app/deps python3 handler.py --test_input '{"input": {"n": 2048}}'
```

```
INFO   | Job result: {'output': {'device': 'NVIDIA GeForce RTX 4090', 'loaded_from': '/workspace/app/handler.py', 'runpod_sdk': '1.12.0', 'torch': '2.9.1+cu128', 'n': 2048, 'matmul_s': 0.081}}
```

`--test_input` 은 워커가 할 방식 그대로 핸들러를 로컬에서 한 번 실행합니다. torch 는 이미지에 있고, 볼륨에는 `runpod` 와 그 의존성만 올립니다.

**네트워크 볼륨에 작은 파일을 많이 쓰는 것은 느립니다.** 위의 `pip install --target` 은 파일 9,237개에 약 10분이 걸렸습니다. 데이터는 159 MB (`du --apparent-size`) 인데 `du` 는 2,016 MB 로 보고했습니다. 테스트 실행 자체는 35초였고, 대부분 import 시간입니다.

### 3단계 — 같은 파일을 서빙

```bash
python3 lab.py pod delete
python3 lab.py endpoint create      # dockerStartCmd + PYTHONPATH 템플릿, 볼륨을 붙인 엔드포인트
python3 lab.py run                  # 작업 하나, 끝날 때까지 폴링
```

```json
{
  "delayTime": 205230,
  "executionTime": 204,
  "output": {
    "device": "NVIDIA GeForce RTX 4090",
    "loaded_from": "/runpod-volume/app/handler.py",
    "matmul_s": 0.0148,
    "n": 4096,
    "runpod_sdk": "1.12.0",
    "torch": "2.9.1+cu128"
  },
  "status": "COMPLETED"
}
```

`loaded_from` 이 증거입니다. 워커가 Pod 이 쓴 파일을 실행했습니다. 그 밖에 두 가지가 보였습니다.

- **`runsync` 는 콜드 스타트를 끝까지 기다리지 않습니다.** 90.9초 뒤 job id 와 함께 `{"status": "IN_QUEUE"}` 를 돌려줬고, 작업은 205초에 끝났습니다. `lab.py run` 은 그 뒤 `/status/{id}` 를 폴링합니다.
- **두 번째 작업은 47초 기다렸습니다.** `idleTimeout` 5 라 첫 워커는 이미 없었고, 다음 컨테이너가 다시 시작됐습니다. 이번에는 호스트에 이미 있는 이미지였습니다.

### 4단계 — 정리

```bash
python3 lab.py endpoint delete
python3 lab.py volume delete
python3 lab.py status
```

엔드포인트와 볼륨은 바로 지워졌습니다. 템플릿은 아니었습니다. *"Template is still held by deleted endpoint …, which is pending cleanup. It can be deleted once that endpoint's last worker has been billed, within about 90 minutes"* — [Serverless Lab 03](../../serverless/03-vllm-endpoint) 과 같습니다. `lab.py endpoint delete` 는 템플릿 id 를 남겨 두니 나중에 지우세요.

### 언제 쓰고 언제 쓰지 말까

| 볼륨 공유 | 이미지에 굽기 |
|---|---|
| 반복 개발: Pod 에서 고치고 Serverless 에서 테스트 | 프로덕션에서 호출하는 모든 것 |
| 워커가 매번 내려받으면 안 되는 큰 파일 | 실행 중인 엔드포인트 아래에서 바뀌면 안 되는 코드 |
| 데이터센터 하나로 충분 | 어느 데이터센터의 워커든 |

볼륨은 엔드포인트를 그 데이터센터에 묶고, 콜드 스타트마다 네트워크 너머로 import 하며, 볼륨에 쓸 수 있는 사람이 엔드포인트가 실행할 코드를 바꿀 수 있습니다.

### 실행 내역

2026-11-05, Secure Cloud EU-RO-1, RTX 4090, `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404`, 볼륨에 runpod SDK 1.12.0, REST v1.

| 단계 | 결과 |
|---|---|
| 네트워크 볼륨을 붙인 Pod | 약 2분 뒤 SSH |
| 볼륨에 `pip install --target` | 약 10분, 파일 9,237개. 실제 159 MB, `du` 기준 2,016 MB |
| Pod 에서 `handler.py --test_input` | 위 출력, 35초 |
| 같은 볼륨에 `dockerStartCmd` 와 `PYTHONPATH` 를 쓴 엔드포인트 | 워커가 `/runpod-volume/app/handler.py` 실행 |
| 첫 작업 | `runsync` 가 90.9초에 `IN_QUEUE` 반환. `delayTime` 205초, `executionTime` 0.2초 |
| 두 번째 작업 | `delayTime` 47초, `executionTime` 0.2초 |
| 정리 | 엔드포인트와 볼륨은 바로 삭제. 템플릿은 엔드포인트 삭제 92분 뒤 삭제 |

실행하지 않은 것: 엔드포인트가 살아 있는 동안 Pod 에서 핸들러 수정, Pod 과 워커가 동시에 쓰는 볼륨, FlashBoot, 다른 데이터센터.
