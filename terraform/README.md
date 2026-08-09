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
| `data_center_id` default | `US-KS-2` exists among 49 data centers, and reports `global_network = true` |

`terraform plan` reaching "2 to add" is the meaningful one: it proves the provider authenticates, the schema matches, and nothing in the config is rejected. Only `apply` would create anything.

**Not yet verified:** `apply`, and therefore everything downstream of it — whether the endpoint actually serves traffic, and the whole of `02-pod`. Those create billable resources.

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

### Honest Assessment

The provider works for the core cases, but it is young — 9 releases, ~2,000 downloads, no generated registry documentation, examples that do not match the pinned version, and a latest release that does not load. Pin exactly, read `terraform plan` carefully, and expect to consult the Go source when an attribute behaves oddly. For production use today, the console or SDK is the safer path; this track is about understanding the IaC model.

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
| `data_center_id` 기본값 | `US-KS-2` 는 49개 데이터센터 중 실재하며 `global_network = true` |

`terraform plan` 이 "2 to add" 까지 도달했다는 점이 핵심입니다. 프로바이더 인증이 되고, 스키마가 맞고, 설정 중 거부되는 항목이 없다는 뜻입니다. 실제로 무언가를 생성하는 것은 `apply` 뿐입니다.

**아직 검증하지 않은 것:** `apply`, 그리고 그 이후의 모든 것 — 엔드포인트가 실제로 트래픽을 처리하는지, 그리고 `02-pod` 전체. 과금되는 리소스를 만들기 때문입니다.

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

### 솔직한 평가

핵심 기능은 동작하지만 아직 초기 단계입니다. 릴리스 9개, 다운로드 약 2,000회, 레지스트리 생성 문서 없음, 고정 버전과 맞지 않는 예제, 그리고 로드조차 되지 않는 최신 릴리스. 버전을 정확히 고정하고, `terraform plan` 을 꼼꼼히 읽고, 속성이 이상하게 동작하면 Go 소스를 직접 확인할 각오가 필요합니다. 현시점에서 프로덕션 용도로는 콘솔이나 SDK 가 더 안전하며, 이 트랙의 목적은 IaC 모델을 이해하는 데 있습니다.
