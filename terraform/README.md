# Terraform Track — Runpod as Infrastructure as Code

[English](#english) | [한국어](#한국어)

---

## English

Everything the `serverless/` and `pod/` tracks do by hand in the console, done declaratively instead. Same resources, reproducible and reviewable.

### 📚 Labs

| Lab | Creates | Cost while idle |
|---|---|---|
| [01-endpoint](./01-endpoint) | `runpod_template` + `runpod_endpoint` | **None** — `workers_min = 0` |
| [02-pod](./02-pod) | `runpod_pod` (+ optional `runpod_network_volume`) | **Billed per minute** |

Start with 01. It provisions the worker from `serverless/01-hello-worker` and costs nothing until you send a request.

### ⚠️ Read This First — Two Blocking Issues

Both were found by actually running `init` / `validate` against the provider, not by reading docs.

**1. Terraform 1.5.x cannot install this provider.**

```
Error while installing runpod/runpod v1.0.9: error decoding signing key:
openpgp: invalid data: armor invalid
```

You need **Terraform 1.6+**. Verified working on 1.15.8. Note that Homebrew's `terraform` formula is frozen at 1.5.7 (it stopped tracking upstream after the BUSL licence change), so `brew install terraform` gives you a version that will not work:

```bash
brew install hashicorp/tap/terraform
```

**2. Provider v1.0.9 is published but unusable.**

Its `endpoint_jobs` and `endpoint_workers` data sources declare an attribute with none of `Required`, `Optional` or `Computed` set. Terraform cannot load the provider schema at all, so **every** command fails — `validate`, `plan` and `apply` alike:

```
Error converting data source schema: The schema for the data source
"runpod_endpoint_workers" couldn't be converted into a usable type.
AttributeName("workers"): must have Required, Optional, or Computed set..
```

These labs therefore pin **exactly** `= 1.0.8`. A range such as `~> 1.0.8` would silently resolve to 1.0.9 and break.

### The 1.0.8 vs 1.0.9 Schema Difference

This matters because the provider's own examples target 1.0.9 and will not work on 1.0.8:

| | v1.0.8 (used here) | v1.0.9 (broken) |
|---|---|---|
| `runpod_endpoint` image | via `template_id` → `runpod_template` | `image_name` directly |
| GPU selection | `gpu_type_ids` (list, priority order) | `gpu_type_id` (single string) |

So on 1.0.8 an endpoint is a two-resource affair — register a template holding the image, then point an endpoint at it. That actually mirrors the console more faithfully, and one template can back several endpoints.

Also note the upstream `examples/network_volume/main.tf` sets `type = ...` on `runpod_network_volume`, but no such attribute exists in the 1.0.8 schema (it has `storage_tier`). Treat the upstream examples as sketches, not as working code.

### ✅ What Has Been Verified Against the Live API

Everything below was checked with a real API key using **read-only calls and `terraform plan`**. No resources were created, so none of it cost anything.

| Check | Result |
|---|---|
| `terraform init` on 1.15.8 | Provider `= 1.0.8` installs cleanly |
| `terraform validate` (both labs) | Success |
| `terraform plan` on `01-endpoint` | `Plan: 2 to add, 0 to change, 0 to destroy` — the template and endpoint resolve correctly against the real API |
| `gpu_type_ids` defaults | `NVIDIA GeForce RTX 4090` and `NVIDIA RTX A4000` both appear in the live catalogue of 48 GPU types |
| `data_center_id` default (then `US-KS-2`) | `US-KS-2` exists among 49 data centers, and reports `global_network = true`. The default is now `EU-RO-1` — see the `02-pod` run below |

`terraform plan` reaching "2 to add" is the meaningful one: it proves the provider authenticates, the schema matches, and nothing in the config is rejected. Only `apply` would create anything.

**`apply` and `destroy` on `01-endpoint`, 2026-10-11** (Terraform 1.16.4, provider 1.0.8): the template and endpoint were created, a `plan` straight after showed no changes, and `destroy` removed both, leaving no template, no endpoint and `currentSpendPerHr` 0. It took two fixes found on the way:

| What happened | Fix in `main.tf` |
|---|---|
| `Provider produced inconsistent result after apply` on `runpod_template`: `.readme`, `.container_registry_auth_id` and `.ports` came back as `""` / `["8888/http","22/tcp"]`, not null. The template was created and left tainted | Set `readme = ""`, `container_registry_auth_id = ""`, `ports = ["8888/http", "22/tcp"]`. `ports = []` is not kept; the API fills in its defaults |
| Same error on `runpod_endpoint` for `.network_volume_id` | Set `network_volume_id = ""` |

The provider declares these attributes Optional but not Computed, so it cannot accept a value the API fills in. A tainted resource is replaced on the next `apply` and removed by `destroy`.

**The image has to be one Runpod can pull without the console.** The run used the Lab 01 image the console built from GitHub (`registry.runpod.net/…-01-hello-worker-dockerfile:<sha>`). Every worker stayed `INITIALIZING` with `Failed to get Hub registry auth. Is this a template you have access to?`, so the job was cancelled. The Runpod registry only serves templates the console's GitHub integration created. Build and push the image to a registry you control, as in [`serverless/01-hello-worker`](../serverless/01-hello-worker) Option B.

**Serving a request on `01-endpoint`, 2026-10-20** (same Terraform and provider, image `docker.io/litkhai/hello-worker:v1.0.0` built from Lab 01 with `--platform linux/amd64` and pushed to Docker Hub): `apply` created both resources in 1 s each. One `/run` with `{"input": {"name": "Terraform"}}` came back `COMPLETED` with `{"greeting": "Hello, Terraform!"}`, `delayTime` 6,280 ms and `executionTime` 57 ms, on an RTX 4090 — the first entry in `gpu_type_ids`. The worker log showed the pull by digest, all seven SDK 1.12.0 fitness checks passing, then `Started.` and `Finished.` for the job. `destroy` removed both; no template or endpoint named `hol-hello-worker` remained and `currentSpendPerHr` was 0.

**`apply` and `destroy` on `02-pod`, 2026-10-16** (Terraform 1.16.4, provider 1.0.8, image `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404`): three runs, all destroyed, account left with no Pod, no network volume and `currentSpendPerHr` 0.

| Run | Result |
|---|---|
| Without a network volume | `Apply complete` in 2 s; SSH port public after about 3 min; `ssh root@<ip> -p <port>` worked, `nvidia-smi` and `torch.cuda.is_available()` True; `destroy` clean |
| With a 20 GB network volume in `EU-RO-1` | Volume and Pod created; the Pod landed in `EU-RO-1` with the volume mounted at `/workspace` (network filesystem), a file written and read back; `destroy` removed both |
| With `lifecycle { ignore_changes = [machine_id] }` | `plan` right after `apply` showed no resource change, only output values |

What it showed:

| Finding | Consequence |
|---|---|
| **`gpu_type_id` is not sent.** The provider's create request carries no GPU field, so Runpod picks by availability (`gpuTypePriority` defaults to `availability`) | Asked for RTX A4500 ($0.25/hr); every Pod came up as RTX 4090 at $0.89/hr, while state still said A4500. Read `cost_per_hr` after `apply` |
| **`machine_id` drifts.** Read stores the machine the Pod landed on; the attribute is Optional, not Computed | Without the `ignore_changes` above, every `plan` after `apply` proposes an in-place update |
| **`start_ssh` / `start_jupyter` are not sent either** | SSH worked anyway — the image exposes port 22 by default. Jupyter was not checked |
| **The volume's data center must support storage.** `US-KS-2`, the previous default, reported `storageSupport = false` | Default changed to `EU-RO-1`. Check `dataCenters { id storageSupport }` before applying |

**Not yet verified:** Jupyter on the `02-pod` Pod.

### Discovering Valid IDs

Rather than guessing GPU or data-center IDs, read them from the provider. This is a data-source-only config, so `apply` creates nothing:

```hcl
terraform {
  required_providers {
    runpod = { source = "runpod/runpod", version = "= 1.0.8" }
  }
}
provider "runpod" {}

data "runpod_data_centers" "all" {}
data "runpod_gpu_types" "all" {}

output "data_centers" { value = data.runpod_data_centers.all }
output "gpu_types" { value = data.runpod_gpu_types.all }
```

Or from the SDK, which is quicker for a one-off:

```bash
python -c "
import os, runpod
runpod.api_key = os.environ['RUNPOD_API_KEY']
for g in runpod.get_gpus(): print(g['id'])
"
```

Available data sources: `gpu_types`, `data_centers`, `user`, `machine`, `machines`, `pod`, `template`, `container_registry_auths`, `billing_pod`, `billing_endpoint`, `billing_network_volume`.

### Authentication

The provider reads `RUNPOD_API_KEY` from the environment, so **no key goes in any `.tf` or `.tfvars` file**:

```bash
set -a; . ../../.env; set +a     # load the repo .env
# or / 또는
export RUNPOD_API_KEY="..."
```

The provider block is deliberately empty:

```hcl
provider "runpod" {}
```

### Workflow

```bash
cd terraform/01-endpoint
cp terraform.tfvars.example terraform.tfvars   # set your image_name
set -a; . ../../.env; set +a

terraform init
terraform plan       # always read this before applying
terraform apply
terraform output test_command

terraform destroy    # when finished
```

### 🔒 State Files

`terraform.tfstate` records everything the provider returned, in plaintext. The repo `.gitignore` covers `*.tfstate*`, `*.tfvars` and `.terraform/`, while deliberately keeping `.terraform.lock.hcl` (it pins provider hashes and belongs in version control).

This is not a hypothetical concern: the official Runpod provider repo has `examples/pytorch/terraform.tfstate` committed. Do not copy that habit.

### Referenced Resources

| Resource | Notes |
|---|---|
| [registry.terraform.io/providers/runpod/runpod](https://registry.terraform.io/providers/runpod/runpod) | The published provider. v1.0.9 latest, ~2k downloads |
| [runpod/terraform-provider-runpod](https://github.com/runpod/terraform-provider-runpod) | Source. 10 resources, 16 data sources. Examples target 1.0.9 |
| [runpod/pulumi-runpod](https://github.com/runpod/pulumi-runpod) | Pulumi alternative, less mature |
| [Runpod API reference](https://docs.runpod.io/api-reference) | What the provider wraps |

**Resources available:** `runpod_pod`, `runpod_endpoint`, `runpod_template`, `runpod_network_volume`, `runpod_container_registry_auth`, `runpod_machine`, `runpod_pod_action`, `runpod_endpoint_job`, `runpod_endpoint_worker`, `runpod_ecr_delegation`

**Data sources include:** `gpu_types`, `data_centers`, `billing_pod`, `billing_endpoint`, `billing_network_volume`, `endpoint_jobs`, `endpoint_workers`, `user`

### Lessons from the First Apply

From running `apply` → request → `destroy` on `01-endpoint`, 2026-10-11:

| Lesson | What showed it |
|---|---|
| **`plan` passing does not mean `apply` will.** `plan` validates the config against the schema; only `apply` sees what the API sends back | `plan` said `2 to add`; `apply` then failed twice on values the API filled in |
| **A failed `apply` can still create a real resource.** After the error, check `terraform state list` and the account, not just the exit code | The template existed in the account and sat in state as `tainted`; the next `apply` replaced it and `destroy` removed it |
| **Find Optional-but-not-Computed attributes before applying.** `terraform providers schema -json` lists them; if the API fills one in, set it explicitly to the value the API returns | `readme`, `container_registry_auth_id`, `ports`, `network_volume_id` — see the fixes above |
| **Check for drift right after `apply`.** `terraform plan -detailed-exitcode` returns 0 when config and live state agree | Returned 0 after the fixes |
| **Confirm the account is empty after `destroy`.** List templates and endpoints, and read `myself { currentSpendPerHr }` | No `hol-*` template, no extra endpoint, spend 0 |
| **Use an image the template can pull on its own.** Console GitHub builds land in `registry.runpod.net`, which only serves the templates the console created | `Failed to get Hub registry auth` on every worker |

### Honest Assessment

The provider works for the core cases, but it is young — 9 releases, ~2,000 downloads, no generated registry documentation, examples that do not match the pinned version, a latest release that does not load, and resource schemas that reject values the API fills in, so a clean `plan` can still fail on `apply`. Pin exactly, read `terraform plan` carefully, check the schema for Optional-but-not-Computed attributes, and expect to consult the Go source when an attribute behaves oddly. For production use today, the console or SDK is the safer path; this track is about understanding the IaC model.

---

## 한국어

`serverless/` 와 `pod/` 트랙에서 콘솔로 직접 하던 작업을 선언적으로 처리합니다. 같은 리소스를, 재현 가능하고 리뷰 가능한 형태로 만듭니다.

### 📚 실습 목록

| 실습 | 생성 대상 | 유휴 시 비용 |
|---|---|---|
| [01-endpoint](./01-endpoint) | `runpod_template` + `runpod_endpoint` | **없음** — `workers_min = 0` |
| [02-pod](./02-pod) | `runpod_pod` (+ 선택적 `runpod_network_volume`) | **분 단위 과금** |

01 부터 시작하세요. `serverless/01-hello-worker` 의 워커를 프로비저닝하며, 요청을 보내기 전까지는 비용이 발생하지 않습니다.

### ⚠️ 먼저 읽을 것 — 두 가지 차단 이슈

둘 다 문서를 읽어서가 아니라 실제로 `init` / `validate` 를 돌려서 확인한 내용입니다.

**1. Terraform 1.5.x 에서는 이 프로바이더를 설치할 수 없습니다.**

```
Error while installing runpod/runpod v1.0.9: error decoding signing key:
openpgp: invalid data: armor invalid
```

**Terraform 1.6 이상**이 필요합니다. 1.15.8 에서 동작을 확인했습니다. Homebrew 의 `terraform` 포뮬러는 1.5.7 에 멈춰 있으므로(BUSL 라이선스 변경 이후 추적 중단), `brew install terraform` 으로는 동작하지 않는 버전이 설치됩니다.

```bash
brew install hashicorp/tap/terraform
```

**2. 프로바이더 v1.0.9 는 배포돼 있지만 사용할 수 없습니다.**

`endpoint_jobs` 와 `endpoint_workers` 데이터소스의 속성에 `Required`, `Optional`, `Computed` 중 아무것도 설정돼 있지 않습니다. Terraform 이 프로바이더 스키마 자체를 로드하지 못하므로 `validate`, `plan`, `apply` 를 포함한 **모든** 명령이 실패합니다.

```
Error converting data source schema: The schema for the data source
"runpod_endpoint_workers" couldn't be converted into a usable type.
AttributeName("workers"): must have Required, Optional, or Computed set..
```

따라서 이 실습들은 **정확히** `= 1.0.8` 로 고정합니다. `~> 1.0.8` 같은 범위 지정은 조용히 1.0.9 로 해석되어 깨집니다.

### 1.0.8 과 1.0.9 의 스키마 차이

프로바이더 공식 예제가 1.0.9 를 기준으로 작성돼 있어 1.0.8 에서는 동작하지 않으므로, 이 차이를 알아둘 필요가 있습니다.

| | v1.0.8 (여기서 사용) | v1.0.9 (깨짐) |
|---|---|---|
| `runpod_endpoint` 의 이미지 지정 | `template_id` → `runpod_template` 경유 | `image_name` 직접 지정 |
| GPU 선택 | `gpu_type_ids` (목록, 우선순위 순) | `gpu_type_id` (단일 문자열) |

즉 1.0.8 에서 엔드포인트는 리소스 두 개로 구성됩니다. 이미지를 담은 템플릿을 먼저 등록하고, 엔드포인트가 그것을 가리킵니다. 실제로는 이 쪽이 콘솔의 흐름을 더 충실히 반영하며, 하나의 템플릿으로 여러 엔드포인트를 만들 수 있습니다.

또한 공식 `examples/network_volume/main.tf` 는 `runpod_network_volume` 에 `type = ...` 을 설정하지만, 1.0.8 스키마에는 그런 속성이 없습니다(`storage_tier` 가 있음). 공식 예제는 동작하는 코드가 아니라 스케치로 취급하세요.

### ✅ 실제 API 로 검증한 항목

아래 내용은 실제 API 키로 **읽기 전용 호출과 `terraform plan`** 만 사용해 확인했습니다. 리소스를 생성하지 않았으므로 비용은 발생하지 않았습니다.

| 확인 항목 | 결과 |
|---|---|
| 1.15.8 에서 `terraform init` | 프로바이더 `= 1.0.8` 정상 설치 |
| `terraform validate` (두 실습 모두) | Success |
| `01-endpoint` 의 `terraform plan` | `Plan: 2 to add, 0 to change, 0 to destroy` — 템플릿과 엔드포인트가 실제 API 기준으로 정상 해석됨 |
| `gpu_type_ids` 기본값 | `NVIDIA GeForce RTX 4090`, `NVIDIA RTX A4000` 모두 실제 카탈로그(48종)에 존재 |
| `data_center_id` 기본값 (당시 `US-KS-2`) | `US-KS-2` 는 49개 데이터센터 중 실재하며 `global_network = true`. 현재 기본값은 `EU-RO-1` — 아래 `02-pod` 실행 참조 |

`terraform plan` 이 "2 to add" 까지 도달했다는 점이 핵심입니다. 프로바이더 인증이 되고, 스키마가 맞고, 설정 중 거부되는 항목이 없다는 뜻입니다. 실제로 무언가를 생성하는 것은 `apply` 뿐입니다.

**`01-endpoint` 의 `apply` 와 `destroy`, 2026-10-11** (Terraform 1.16.4, 프로바이더 1.0.8): 템플릿과 엔드포인트가 생성됐고, 직후의 `plan` 은 변경 없음이었으며, `destroy` 가 둘 다 지워 템플릿·엔드포인트가 남지 않고 `currentSpendPerHr` 는 0 이었습니다. 도중에 찾은 두 가지 수정이 필요했습니다:

| 일어난 일 | `main.tf` 의 수정 |
|---|---|
| `runpod_template` 에서 `Provider produced inconsistent result after apply`: `.readme`, `.container_registry_auth_id`, `.ports` 가 null 이 아니라 `""` / `["8888/http","22/tcp"]` 로 돌아옴. 템플릿은 생성된 채 tainted 로 남음 | `readme = ""`, `container_registry_auth_id = ""`, `ports = ["8888/http", "22/tcp"]` 로 설정. `ports = []` 는 유지되지 않고 API 기본값으로 채워진다 |
| `runpod_endpoint` 에서 `.network_volume_id` 로 같은 오류 | `network_volume_id = ""` 로 설정 |

프로바이더가 이 속성들을 Optional 로만(Computed 아님) 선언해서 API 가 채운 값을 받아들이지 못합니다. tainted 리소스는 다음 `apply` 에서 교체되고 `destroy` 로 지워집니다.

**이미지는 콘솔 없이도 Runpod 이 pull 할 수 있는 것이어야 합니다.** 이번 실행은 콘솔이 GitHub 에서 빌드한 Lab 01 이미지(`registry.runpod.net/…-01-hello-worker-dockerfile:<sha>`)를 썼습니다. 모든 워커가 `Failed to get Hub registry auth. Is this a template you have access to?` 를 남기고 `INITIALIZING` 에 머물러 작업을 취소했습니다. Runpod 레지스트리는 콘솔의 GitHub 연동이 만든 템플릿에만 이미지를 내줍니다. [`serverless/01-hello-worker`](../serverless/01-hello-worker) 의 방법 B 처럼 직접 관리하는 레지스트리에 빌드·푸시하세요.

**`01-endpoint` 의 요청 처리, 2026-10-20** (같은 Terraform·프로바이더, Lab 01 을 `--platform linux/amd64` 로 빌드해 Docker Hub 에 푸시한 `docker.io/litkhai/hello-worker:v1.0.0`): `apply` 가 두 리소스를 각각 1초 만에 만들었습니다. `{"input": {"name": "Terraform"}}` 로 `/run` 한 건을 보내 `COMPLETED` 와 `{"greeting": "Hello, Terraform!"}` 를 받았고, `delayTime` 6,280 ms, `executionTime` 57 ms, GPU 는 `gpu_type_ids` 의 첫 항목인 RTX 4090 이었습니다. 워커 로그에는 digest 기준 pull, SDK 1.12.0 fitness check 일곱 개 통과, 그 작업의 `Started.` 와 `Finished.` 가 남았습니다. `destroy` 가 둘 다 지웠고, `hol-hello-worker` 템플릿·엔드포인트는 남지 않았으며 `currentSpendPerHr` 는 0 이었습니다.

**`02-pod` 의 `apply` 와 `destroy`, 2026-10-16** (Terraform 1.16.4, 프로바이더 1.0.8, 이미지 `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404`): 세 번 실행했고 모두 삭제했으며, 계정에는 Pod·네트워크 볼륨이 남지 않았고 `currentSpendPerHr` 는 0 이었습니다.

| 실행 | 결과 |
|---|---|
| 네트워크 볼륨 없이 | 2 초 만에 `Apply complete`; 약 3 분 뒤 SSH 포트 공개; `ssh root@<ip> -p <port>` 접속, `nvidia-smi` 와 `torch.cuda.is_available()` True; `destroy` 정상 |
| `EU-RO-1` 에 20 GB 네트워크 볼륨과 함께 | 볼륨과 Pod 생성; Pod 이 `EU-RO-1` 에 배치되고 볼륨이 `/workspace` 에 마운트됨(네트워크 파일시스템), 파일 쓰기·읽기 확인; `destroy` 가 둘 다 삭제 |
| `lifecycle { ignore_changes = [machine_id] }` 추가 | `apply` 직후 `plan` 에 리소스 변경 없음, 출력값만 변경 |

드러난 것:

| 발견 | 영향 |
|---|---|
| **`gpu_type_id` 가 전송되지 않습니다.** 프로바이더의 생성 요청에 GPU 필드가 없어 Runpod 이 가용성 기준으로 고릅니다(`gpuTypePriority` 기본값 `availability`) | RTX A4500(시간당 $0.25)을 지정했지만 모든 Pod 이 시간당 $0.89 인 RTX 4090 으로 떴고, state 에는 A4500 으로 남았습니다. `apply` 후 `cost_per_hr` 를 확인하세요 |
| **`machine_id` 가 drift 합니다.** Read 가 Pod 이 배치된 머신을 저장하는데, 이 속성은 Optional 이고 Computed 가 아닙니다 | 위의 `ignore_changes` 가 없으면 `apply` 이후 모든 `plan` 이 in-place update 를 제안합니다 |
| **`start_ssh` / `start_jupyter` 도 전송되지 않습니다** | 이미지가 기본으로 22 번 포트를 열어 SSH 는 동작했습니다. Jupyter 는 확인하지 않았습니다 |
| **볼륨의 데이터센터가 스토리지를 지원해야 합니다.** 이전 기본값 `US-KS-2` 는 `storageSupport = false` 였습니다 | 기본값을 `EU-RO-1` 로 바꿨습니다. apply 전에 `dataCenters { id storageSupport }` 를 확인하세요 |

**아직 검증하지 않은 것:** `02-pod` Pod 의 Jupyter.

### 유효한 ID 조회하기

GPU 나 데이터센터 ID 를 추측하지 말고 프로바이더에서 직접 읽으세요. 데이터소스만 있는 설정이라 `apply` 해도 생성되는 것이 없습니다.

```hcl
terraform {
  required_providers {
    runpod = { source = "runpod/runpod", version = "= 1.0.8" }
  }
}
provider "runpod" {}

data "runpod_data_centers" "all" {}
data "runpod_gpu_types" "all" {}

output "data_centers" { value = data.runpod_data_centers.all }
output "gpu_types" { value = data.runpod_gpu_types.all }
```

일회성 조회라면 SDK 가 더 빠릅니다.

```bash
python -c "
import os, runpod
runpod.api_key = os.environ['RUNPOD_API_KEY']
for g in runpod.get_gpus(): print(g['id'])
"
```

사용 가능한 데이터소스: `gpu_types`, `data_centers`, `user`, `machine`, `machines`, `pod`, `template`, `container_registry_auths`, `billing_pod`, `billing_endpoint`, `billing_network_volume`.

### 인증

프로바이더가 환경변수 `RUNPOD_API_KEY` 를 직접 읽으므로 **어떤 `.tf` 나 `.tfvars` 파일에도 키가 들어가지 않습니다.**

```bash
set -a; . ../../.env; set +a     # 저장소 .env 로드
# 또는
export RUNPOD_API_KEY="..."
```

프로바이더 블록은 의도적으로 비어 있습니다.

```hcl
provider "runpod" {}
```

### 작업 흐름

```bash
cd terraform/01-endpoint
cp terraform.tfvars.example terraform.tfvars   # image_name 설정
set -a; . ../../.env; set +a

terraform init
terraform plan       # apply 전에 반드시 읽을 것
terraform apply
terraform output test_command

terraform destroy    # 끝나면
```

### 🔒 State 파일

`terraform.tfstate` 에는 프로바이더가 반환한 모든 값이 평문으로 기록됩니다. 저장소 `.gitignore` 는 `*.tfstate*`, `*.tfvars`, `.terraform/` 을 제외하고, `.terraform.lock.hcl` 은 의도적으로 남깁니다(프로바이더 해시를 고정하므로 버전 관리 대상이 맞습니다).

가상의 우려가 아닙니다. Runpod 공식 프로바이더 레포에는 `examples/pytorch/terraform.tfstate` 가 커밋돼 있습니다. 이 습관은 따라하지 마세요.

### 참조 리소스

| 리소스 | 비고 |
|---|---|
| [registry.terraform.io/providers/runpod/runpod](https://registry.terraform.io/providers/runpod/runpod) | 배포된 프로바이더. 최신 v1.0.9, 다운로드 약 2천 |
| [runpod/terraform-provider-runpod](https://github.com/runpod/terraform-provider-runpod) | 소스. 리소스 10개, 데이터소스 16개. 예제는 1.0.9 기준 |
| [runpod/pulumi-runpod](https://github.com/runpod/pulumi-runpod) | Pulumi 대안, 성숙도는 더 낮음 |
| [Runpod API reference](https://docs.runpod.io/api-reference) | 프로바이더가 감싸고 있는 대상 |

**사용 가능한 리소스:** `runpod_pod`, `runpod_endpoint`, `runpod_template`, `runpod_network_volume`, `runpod_container_registry_auth`, `runpod_machine`, `runpod_pod_action`, `runpod_endpoint_job`, `runpod_endpoint_worker`, `runpod_ecr_delegation`

**주요 데이터소스:** `gpu_types`, `data_centers`, `billing_pod`, `billing_endpoint`, `billing_network_volume`, `endpoint_jobs`, `endpoint_workers`, `user`

### 첫 Apply 에서 얻은 교훈

2026-10-11 `01-endpoint` 에서 `apply` → 요청 → `destroy` 를 실행하며 얻은 것:

| 교훈 | 근거 |
|---|---|
| **`plan` 이 통과해도 `apply` 가 통과한다는 보장은 없습니다.** `plan` 은 설정을 스키마와 대조할 뿐이고, API 가 돌려주는 값은 `apply` 에서야 보입니다 | `plan` 은 `2 to add` 였지만 `apply` 는 API 가 채운 값 때문에 두 번 실패했다 |
| **실패한 `apply` 도 실제 리소스를 만들 수 있습니다.** 오류 뒤에는 종료 코드만 보지 말고 `terraform state list` 와 계정을 확인하세요 | 템플릿이 계정에 생성됐고 state 에 `tainted` 로 남았다. 다음 `apply` 가 교체했고 `destroy` 가 지웠다 |
| **Optional 이면서 Computed 가 아닌 속성을 apply 전에 찾으세요.** `terraform providers schema -json` 으로 볼 수 있고, API 가 채우는 속성이면 API 가 돌려주는 값으로 명시합니다 | `readme`, `container_registry_auth_id`, `ports`, `network_volume_id` — 위의 수정 참조 |
| **`apply` 직후 drift 를 확인하세요.** `terraform plan -detailed-exitcode` 가 0 이면 설정과 실제 상태가 일치합니다 | 수정 후 0 을 반환했다 |
| **`destroy` 후 계정이 비었는지 확인하세요.** 템플릿·엔드포인트 목록과 `myself { currentSpendPerHr }` 를 봅니다 | `hol-*` 템플릿 없음, 추가 엔드포인트 없음, 비용 0 |
| **템플릿이 스스로 pull 할 수 있는 이미지를 쓰세요.** 콘솔 GitHub 빌드는 `registry.runpod.net` 에 올라가며, 이 레지스트리는 콘솔이 만든 템플릿에만 이미지를 내줍니다 | 모든 워커에서 `Failed to get Hub registry auth` |

### 솔직한 평가

핵심 기능은 동작하지만 아직 초기 단계입니다. 릴리스 9개, 다운로드 약 2,000회, 레지스트리 생성 문서 없음, 고정 버전과 맞지 않는 예제, 로드조차 되지 않는 최신 릴리스, 그리고 API 가 채우는 값을 거부하는 리소스 스키마 — 그래서 깨끗한 `plan` 도 `apply` 에서 실패할 수 있습니다. 버전을 정확히 고정하고, `terraform plan` 을 꼼꼼히 읽고, 스키마에서 Optional 이면서 Computed 가 아닌 속성을 확인하고, 속성이 이상하게 동작하면 Go 소스를 직접 확인할 각오가 필요합니다. 현시점에서 프로덕션 용도로는 콘솔이나 SDK 가 더 안전하며, 이 트랙의 목적은 IaC 모델을 이해하는 데 있습니다.
