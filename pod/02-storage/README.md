# Pod Lab 02 — Storage: What Survives a Stop and a Terminate

[English](#english) | [한국어](#한국어)

---

## English

**Goal:** put a marker file on each storage tier of a Pod, then stop, resume, terminate and re-attach, and see which markers are still there.

**Time:** ~20 minutes · **Cost:** a few minutes of an RTX 4090 and a CPU Pod; under $0.10 on 2026-11-05

### The three tiers

| Tier | Where | Billed while stopped? |
|---|---|---|
| Container disk | `/` (here `/root`) | No — it is gone |
| Pod volume | `/workspace` | Yes |
| Network volume | `/workspace`, replacing the Pod volume | Yes, until you delete the volume |

A Pod has a Pod volume *or* a network volume at `/workspace`, not both: *"If attached, a network volume replaces the Pod network volume"* ([`POST /pods`](https://rest.runpod.io/v1/openapi.json)).

### Files

| File | Role |
|---|---|
| `lab.py` | Network volume and Pod create, show, stop, start, delete over the REST API; ids in `.storage.json` |
| `marks.sh` | Runs inside the Pod: `write <tag>` puts a marker in `/root` and `/workspace`, `check` lists them with the filesystem under each |
| `common.py` | `.env` loading and REST calls, standard library only |

The lab calls the REST API directly rather than the Python SDK, whose Pod calls changed shape in 2.0 ([#37](https://github.com/litkhai/runpod-hols/issues/37)). `python3` from the system is enough.

### Step 1 — Pod volume: stop and resume

```bash
cd pod/02-storage
python3 lab.py pod create --disk volume       # RTX 4090, EU-RO-1, 10 GB Pod volume
python3 lab.py pod show                       # prints the SSH command once ready
ssh root@<ip> -p <port> 'bash -s write before-stop' < marks.sh
python3 lab.py pod stop
python3 lab.py pod start
ssh root@<ip> -p <new port> 'bash -s check' < marks.sh
```

```
/root       overlay overlay              (no marker)
/workspace  mfs#euro.runpod.net:9421 fuse before-stop 2026-11-05T07:06:24Z;
```

The container disk was reset by the stop; the Pod volume kept its marker. The SSH port changed (12465 → 12788), so read it again after every start.

**Resume is not guaranteed.** The first `start`, 40 seconds after the stop, failed:

```
POST /pods/brkv1ospiwhwz2/start -> 500 {"error":"start pod: There are not enough free GPUs on the host machine to start this pod."}
```

A stopped Pod stays tied to its machine (`machineId` did not change). Eight minutes later the same call succeeded on the same machine. Until it does, the data on the Pod volume is unreachable — which is the case for a network volume.

**While stopped:** the account's `currentSpendPerHr` read `0.003` for the 10 GB Pod volume. The Pod's own `costPerHr` still read `0.89`, the running GPU rate, so do not read spend from it.

### Step 2 — Network volume: terminate and re-attach

```bash
python3 lab.py volume create                  # 10 GB in EU-RO-1
python3 lab.py pod create --disk network
ssh … 'bash -s write pod-A' < marks.sh
python3 lab.py pod delete
python3 lab.py pod create --disk network      # a new Pod, same volume
ssh … 'bash -s check' < marks.sh
```

```
/root       overlay overlay              (no marker)
/workspace  mfs#euro.runpod.net:9421 fuse pod-A 2026-11-05T07:15:20Z;
```

The second Pod landed on a different host (a different public IP) and found Pod A's marker. A Pod with a network volume could also be stopped; the API accepted it.

### Step 3 — CPU Pods

```bash
python3 lab.py pod create --cpu --disk network
python3 lab.py pod create --cpu --disk volume
```

| CPU Pod (`cpu3c`, 2 vCPU, $0.06/hr) | `/workspace` |
|---|---|
| With the network volume | `mfs#euro.runpod.net:9421 fuse`, Pod A's marker present |
| With `volumeInGb: 10` | `overlay` — no Pod volume was created (`volumeInGb` 0) |

[Lab 01](../01-launch-connect) found the same through the SDK. On a CPU Pod the network volume is the only storage that outlives a stop.

### Step 4 — Clean up

```bash
python3 lab.py pod delete
python3 lab.py volume delete
python3 lab.py status        # Pods (0), Network volumes (0)
```

### What `df` does not tell you

Both the Pod volume and the network volume were mounted from `mfs#euro.runpod.net:9421`, a FUSE filesystem, in EU-RO-1 — the Pod volume is not a local disk there. `df` showed the shared filesystem, not your allocation:

```
mfs#euro.runpod.net:9421  2.3P  1.9P  399T  83% /workspace
```

The 10 GB limit is real all the same. Writing 12,000 MiB stopped at 9,999,220,736 bytes with `Disk quota exceeded`. A 1 GiB `dd … oflag=direct` wrote at 1.6 GB/s to the network volume and 5.4 GB/s to the container disk — one run each.

### Global volume (beta) — what was measured

A third kind of persistent storage, listed first in **Add volume** with a **Global** badge: no datacenter, no size, USD 0.09 per GB-month stored plus IOPS. It is created through `POST https://api.runpod.io/v2/global-volumes` (name only) or the console, but REST v1 cannot attach it: the console's deploy mutation passes `volumeMounts: [{volumeId, volumeType: "OBJECT_STORE_VOLUME", mountPath: "/workspace"}]`. Inside the Pod it is a FUSE mount of an object store.

| 2026-11-07 | Pod A, CA-MTL-1 (RTX A5000) | Pod B, EU-RO-1 (RTX 4090) |
|---|---|---|
| `/workspace` | `fuse.geesefs`, 1.0P | same volume |
| Write 512 MiB | **61 MiB/s** (container disk 273) | |
| First read of that file | 344 MiB/s | **39 MiB/s** across regions |
| Re-read | 275 MiB/s | 985 MiB/s (local cache) |
| 200 small files | 338 ms | 59 ms |

- **One volume, two continents.** A marker and a 512 MiB file written in Canada were readable in Romania with the same sha256; a new file written in Romania appeared in Canada **3 s** later.
- **Concurrent writes diverge.** Both Pods wrote the same file at the same moment; each kept reading its own version — still so 45 s later. The docs say the last write wins and recommend network volumes for shared mutable data; here neither Pod saw the other's write.
- **Billing is per object.** The Storage page showed 537 MB, 205 objects, USD 0.05/month for this test.
- Pod B was deployed with the same GraphQL mutation and `dataCenterId: "EU-RO-1"` — the first choice, RTX A5000, had no capacity there.

Use it for read-mostly data that several regions need — weights, configs, datasets — and keep checkpoints and anything two workers write on a network volume or the container disk.

### What was run

2026-11-05, Secure Cloud, EU-RO-1, image `runpod/base:1.0.2-ubuntu2404`, REST API v1.

| Step | Result |
|---|---|
| GPU Pod, Pod volume, stop | `/root` marker gone, `/workspace` marker kept |
| First start after stop | Refused: not enough free GPUs on the host |
| Start eight minutes later | Same machine, SSH port changed |
| Spend while stopped | `currentSpendPerHr` 0.003; Pod `costPerHr` still 0.89 |
| GPU Pod, network volume, stop | Accepted |
| New GPU Pod, same network volume | Different host, marker present |
| Network volume quota | `Disk quota exceeded` at ~10 GB; `df` shows 2.3 PB |
| CPU Pod + network volume | Mounted, marker present |
| CPU Pod + `volumeInGb` 10 | No Pod volume |
| Clean up | No Pods, no volumes, `currentSpendPerHr` 0 |

Not run: other data centers, a Pod volume on a host where it might be local disk, read throughput, the storage price per GB (read it from [Pricing](https://docs.runpod.io/pods/pricing)), a stop that never resumes.

---

## 한국어

**목표:** Pod 의 스토리지 계층마다 표식 파일을 두고, 중지·재개·삭제·재연결을 거친 뒤 어떤 표식이 남는지 봅니다.

**소요 시간:** 약 20분 · **비용:** RTX 4090 과 CPU Pod 몇 분. 2026-11-05 기준 $0.10 미만

### 세 계층

| 계층 | 위치 | 중지 중 과금? |
|---|---|---|
| 컨테이너 디스크 | `/` (여기서는 `/root`) | 아니요 — 사라집니다 |
| Pod 볼륨 | `/workspace` | 예 |
| 네트워크 볼륨 | `/workspace`, Pod 볼륨을 대체 | 예, 볼륨을 지울 때까지 |

Pod 은 `/workspace` 에 Pod 볼륨 *또는* 네트워크 볼륨을 가집니다. 둘 다는 아닙니다. *"If attached, a network volume replaces the Pod network volume"* ([`POST /pods`](https://rest.runpod.io/v1/openapi.json)).

### 파일 구성

| 파일 | 역할 |
|---|---|
| `lab.py` | REST API 로 네트워크 볼륨과 Pod 생성·조회·중지·시작·삭제. id 는 `.storage.json` 에 기록 |
| `marks.sh` | Pod 안에서 실행. `write <tag>` 는 `/root` 와 `/workspace` 에 표식을 쓰고, `check` 는 각 경로의 파일시스템과 함께 표식을 보여줌 |
| `common.py` | `.env` 로딩과 REST 호출. 표준 라이브러리만 사용 |

Python SDK 는 2.0 에서 Pod 호출 형태가 바뀌었으므로 ([#37](https://github.com/litkhai/runpod-hols/issues/37)) REST API 를 직접 호출합니다. 시스템 `python3` 로 충분합니다.

### 1단계 — Pod 볼륨: 중지와 재개

```bash
cd pod/02-storage
python3 lab.py pod create --disk volume       # RTX 4090, EU-RO-1, 10 GB Pod 볼륨
python3 lab.py pod show                       # 준비되면 SSH 명령 출력
ssh root@<ip> -p <port> 'bash -s write before-stop' < marks.sh
python3 lab.py pod stop
python3 lab.py pod start
ssh root@<ip> -p <새 port> 'bash -s check' < marks.sh
```

```
/root       overlay overlay              (no marker)
/workspace  mfs#euro.runpod.net:9421 fuse before-stop 2026-11-05T07:06:24Z;
```

중지하면서 컨테이너 디스크는 초기화됐고, Pod 볼륨은 표식을 유지했습니다. SSH 포트가 바뀌었으니 (12465 → 12788) 시작할 때마다 다시 확인하세요.

**재개는 보장되지 않습니다.** 중지 40초 뒤의 첫 `start` 가 실패했습니다.

```
POST /pods/brkv1ospiwhwz2/start -> 500 {"error":"start pod: There are not enough free GPUs on the host machine to start this pod."}
```

중지된 Pod 은 원래 머신에 묶여 있습니다 (`machineId` 가 바뀌지 않음). 8분 뒤 같은 호출이 같은 머신에서 성공했습니다. 그 전까지는 Pod 볼륨의 데이터에 접근할 수 없습니다. 네트워크 볼륨이 필요한 이유입니다.

**중지 중에는** 계정의 `currentSpendPerHr` 가 10 GB Pod 볼륨에 대해 `0.003` 이었습니다. Pod 자체의 `costPerHr` 는 실행 중 GPU 요금인 `0.89` 그대로였으니, 지출을 거기서 읽지 마세요.

### 2단계 — 네트워크 볼륨: 삭제 후 다시 연결

```bash
python3 lab.py volume create                  # EU-RO-1 에 10 GB
python3 lab.py pod create --disk network
ssh … 'bash -s write pod-A' < marks.sh
python3 lab.py pod delete
python3 lab.py pod create --disk network      # 새 Pod, 같은 볼륨
ssh … 'bash -s check' < marks.sh
```

```
/root       overlay overlay              (no marker)
/workspace  mfs#euro.runpod.net:9421 fuse pod-A 2026-11-05T07:15:20Z;
```

두 번째 Pod 은 다른 호스트 (다른 공인 IP) 에 떴고 Pod A 의 표식을 찾았습니다. 네트워크 볼륨이 붙은 Pod 도 중지할 수 있었습니다. API 가 받아들였습니다.

### 3단계 — CPU Pod

```bash
python3 lab.py pod create --cpu --disk network
python3 lab.py pod create --cpu --disk volume
```

| CPU Pod (`cpu3c`, vCPU 2개, $0.06/hr) | `/workspace` |
|---|---|
| 네트워크 볼륨 연결 | `mfs#euro.runpod.net:9421 fuse`, Pod A 의 표식 있음 |
| `volumeInGb: 10` | `overlay` — Pod 볼륨이 만들어지지 않음 (`volumeInGb` 0) |

[Lab 01](../01-launch-connect) 이 SDK 로 본 것과 같습니다. CPU Pod 에서 중지를 넘어 살아남는 스토리지는 네트워크 볼륨뿐입니다.

### 4단계 — 정리

```bash
python3 lab.py pod delete
python3 lab.py volume delete
python3 lab.py status        # Pods (0), Network volumes (0)
```

### `df` 가 알려주지 않는 것

EU-RO-1 에서는 Pod 볼륨과 네트워크 볼륨 모두 FUSE 파일시스템 `mfs#euro.runpod.net:9421` 에서 마운트됐습니다. 그곳의 Pod 볼륨은 로컬 디스크가 아닙니다. `df` 는 내 할당량이 아니라 공유 파일시스템 전체를 보여줬습니다.

```
mfs#euro.runpod.net:9421  2.3P  1.9P  399T  83% /workspace
```

그래도 10 GB 제한은 실재합니다. 12,000 MiB 를 쓰자 9,999,220,736 바이트에서 `Disk quota exceeded` 로 멈췄습니다. 1 GiB `dd … oflag=direct` 는 네트워크 볼륨에 1.6 GB/s, 컨테이너 디스크에 5.4 GB/s 였습니다. 각각 한 번 측정입니다.

### Global volume (베타) — 측정한 것

세 번째 영구 스토리지로, **Add volume** 목록 맨 앞에 **Global** 배지와 함께 나옵니다. 데이터센터도 크기도 없고, 저장 GB·월 USD 0.09 에 IOPS 요금이 붙습니다. `POST https://api.runpod.io/v2/global-volumes` (이름만) 나 콘솔로 만들지만, REST v1 로는 Pod 에 붙일 수 없습니다. 콘솔의 배포 mutation 은 `volumeMounts: [{volumeId, volumeType: "OBJECT_STORE_VOLUME", mountPath: "/workspace"}]` 를 보냅니다. Pod 안에서는 오브젝트 스토어의 FUSE 마운트입니다.

| 2026-11-07 | Pod A, CA-MTL-1 (RTX A5000) | Pod B, EU-RO-1 (RTX 4090) |
|---|---|---|
| `/workspace` | `fuse.geesefs`, 1.0P | 같은 볼륨 |
| 512 MiB 쓰기 | **61 MiB/s** (컨테이너 디스크 273) | |
| 그 파일 첫 읽기 | 344 MiB/s | 지역 간 **39 MiB/s** |
| 다시 읽기 | 275 MiB/s | 985 MiB/s (로컬 캐시) |
| 작은 파일 200개 | 338 ms | 59 ms |

- **볼륨 하나, 두 대륙.** 캐나다에서 쓴 마커와 512 MiB 파일을 루마니아에서 같은 sha256 으로 읽었고, 루마니아에서 쓴 새 파일은 **3초** 뒤 캐나다에 보였습니다.
- **동시 쓰기는 갈라집니다.** 두 Pod 이 같은 순간에 같은 파일을 쓰자 각자 자기 버전을 계속 읽었고, 45초 뒤에도 그대로였습니다. 문서는 마지막 쓰기가 이긴다고 하고 공유 가변 데이터에는 네트워크 볼륨을 권하는데, 여기서는 어느 쪽도 상대의 쓰기를 보지 못했습니다.
- **과금은 객체 단위입니다.** Storage 화면에 이 테스트는 537 MB, 객체 205개, 월 USD 0.05 로 나왔습니다.
- Pod B 는 같은 GraphQL mutation 에 `dataCenterId: "EU-RO-1"` 을 넣어 띄웠습니다. 첫 선택인 RTX A5000 은 그곳에 자리가 없었습니다.

여러 지역이 함께 읽는 데이터 — 가중치, 설정, 데이터셋 — 에 쓰고, 체크포인트처럼 둘 이상이 쓰는 데이터는 네트워크 볼륨이나 컨테이너 디스크에 두세요.

### 실행 내역

2026-11-05, Secure Cloud, EU-RO-1, 이미지 `runpod/base:1.0.2-ubuntu2404`, REST API v1.

| 단계 | 결과 |
|---|---|
| GPU Pod, Pod 볼륨, 중지 | `/root` 표식 사라짐, `/workspace` 표식 유지 |
| 중지 후 첫 시작 | 거부: 호스트에 여유 GPU 없음 |
| 8분 뒤 시작 | 같은 머신, SSH 포트 변경 |
| 중지 중 지출 | `currentSpendPerHr` 0.003. Pod `costPerHr` 는 여전히 0.89 |
| GPU Pod, 네트워크 볼륨, 중지 | 받아들여짐 |
| 새 GPU Pod, 같은 네트워크 볼륨 | 다른 호스트, 표식 있음 |
| 네트워크 볼륨 할당량 | 약 10 GB 에서 `Disk quota exceeded`. `df` 는 2.3 PB |
| CPU Pod + 네트워크 볼륨 | 마운트됨, 표식 있음 |
| CPU Pod + `volumeInGb` 10 | Pod 볼륨 없음 |
| 정리 | Pod 없음, 볼륨 없음, `currentSpendPerHr` 0 |

실행하지 않은 것: 다른 데이터센터, Pod 볼륨이 로컬 디스크일 수 있는 호스트, 읽기 처리량, GB 당 스토리지 요금 ([Pricing](https://docs.runpod.io/pods/pricing) 참고), 끝내 재개되지 않는 중지.
