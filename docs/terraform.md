---
layout: default
title: Terraform
permalink: /terraform/
---

# Terraform

<div class="lang" data-lang="en" markdown="1">

## English

Everything the Serverless and Pod tracks do by hand in the console, done declaratively instead.

| Lab | Creates | Cost while idle |
|---|---|---|
| [01-endpoint](https://github.com/litkhai/runpod-hols/tree/main/terraform/01-endpoint) | `runpod_template` + `runpod_endpoint` | **None** — `workers_min = 0` |
| [02-pod](https://github.com/litkhai/runpod-hols/tree/main/terraform/02-pod) | `runpod_pod` (+ optional `runpod_network_volume`) | **Billed per minute** |

### Read this first — two blocking issues

Both were found by actually running `init` and `validate`, not by reading documentation.

<div class="danger" markdown="1">
**1. Terraform 1.5.x cannot install this provider.**

```
error decoding signing key: openpgp: invalid data: armor invalid
```

You need **Terraform 1.6+**; verified on 1.15.8. Homebrew's `terraform` formula is frozen at 1.5.7 after the BUSL licence change, so `brew install terraform` gives you a version that will not work. Use `brew install hashicorp/tap/terraform`.
</div>

<div class="danger" markdown="1">
**2. Provider v1.0.9 is published but unusable.**

Its `endpoint_jobs` and `endpoint_workers` data sources declare an attribute with none of `Required`, `Optional` or `Computed` set, so Terraform cannot load the provider schema at all. Every command fails — `validate`, `plan` and `apply` alike:

```
Error converting data source schema: The schema for the data source
"runpod_endpoint_workers" couldn't be converted into a usable type.
AttributeName("workers"): must have Required, Optional, or Computed set..
```

These labs pin **exactly** `= 1.0.8`. A range like `~> 1.0.8` would silently resolve to 1.0.9 and break.
</div>

### The 1.0.8 vs 1.0.9 schema difference

This matters because the provider's own examples target 1.0.9 and will not work on 1.0.8:

| | v1.0.8 (used here) | v1.0.9 (broken) |
|---|---|---|
| `runpod_endpoint` image | via `template_id` → `runpod_template` | `image_name` directly |
| GPU selection | `gpu_type_ids` (list, priority order) | `gpu_type_id` (single string) |

On 1.0.8 an endpoint is a two-resource affair — register a template holding the image, then point an endpoint at it. That mirrors the console more faithfully, and one template can back several endpoints.

Also, the upstream `examples/network_volume/main.tf` sets `type = ...` on `runpod_network_volume`, but no such attribute exists in 1.0.8 (it has `storage_tier`). Treat the upstream examples as sketches, not working code.

### Verified against the live API

Checked with a real key using read-only calls and `terraform plan`. Nothing was created, so nothing cost anything.

| Check | Result |
|---|---|
| `terraform init` on 1.15.8 | Provider `= 1.0.8` installs cleanly |
| `terraform validate`, both labs | Success |
| `terraform plan` on `01-endpoint` | `Plan: 2 to add, 0 to change, 0 to destroy` |
| `gpu_type_ids` defaults | Both appear in the live catalogue of 48 GPU types |
| `data_center_id` default | `US-KS-2` exists among 49, `global_network = true` |

Reaching "2 to add" is the meaningful part: the provider authenticates, the schema matches, and nothing is rejected. Only `apply` creates resources.

**Not verified:** `apply`, and therefore whether the endpoint serves traffic, plus all of `02-pod` — those bill.

<div class="note" markdown="1">
Don't guess GPU or data-center IDs. Read them from `data "runpod_data_centers"` and `data "runpod_gpu_types"` — a data-source-only config creates nothing on `apply`.
</div>

### Authentication

The provider reads `RUNPOD_API_KEY` from the environment, so no key goes in any `.tf` or `.tfvars` file. The provider block is deliberately empty:

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

### State files

`terraform.tfstate` records everything the provider returned, in plaintext. The repo `.gitignore` covers `*.tfstate*`, `*.tfvars` and `.terraform/`, while deliberately keeping `.terraform.lock.hcl` — it pins provider hashes and belongs in version control.

<div class="warn" markdown="1">
Not a hypothetical concern: the official Runpod provider repo has `examples/pytorch/terraform.tfstate` committed. Do not copy that habit.
</div>

[Full track in the repo →](https://github.com/litkhai/runpod-hols/tree/main/terraform)

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

Serverless 와 Pod 트랙에서 콘솔로 직접 하던 작업을 선언적으로 처리합니다.

| 실습 | 생성 대상 | 유휴 시 비용 |
|---|---|---|
| [01-endpoint](https://github.com/litkhai/runpod-hols/tree/main/terraform/01-endpoint) | `runpod_template` + `runpod_endpoint` | **없음** — `workers_min = 0` |
| [02-pod](https://github.com/litkhai/runpod-hols/tree/main/terraform/02-pod) | `runpod_pod` (+ 선택적 `runpod_network_volume`) | **분 단위 과금** |

### 먼저 읽을 것 — 두 가지 차단 이슈

둘 다 문서를 읽어서가 아니라 실제로 `init` 과 `validate` 를 돌려서 확인한 내용입니다.

<div class="danger" markdown="1">
**1. Terraform 1.5.x 에서는 이 프로바이더를 설치할 수 없습니다.**

```
error decoding signing key: openpgp: invalid data: armor invalid
```

**Terraform 1.6 이상**이 필요하며 1.15.8 에서 확인했습니다. Homebrew 의 `terraform` 포뮬러는 BUSL 라이선스 변경 이후 1.5.7 에 멈춰 있어 `brew install terraform` 으로는 동작하지 않는 버전이 설치됩니다. `brew install hashicorp/tap/terraform` 을 사용하세요.
</div>

<div class="danger" markdown="1">
**2. 프로바이더 v1.0.9 는 배포돼 있지만 사용할 수 없습니다.**

`endpoint_jobs` 와 `endpoint_workers` 데이터소스의 속성에 `Required`, `Optional`, `Computed` 가 모두 설정돼 있지 않아 Terraform 이 프로바이더 스키마 자체를 로드하지 못합니다. `validate`, `plan`, `apply` 를 포함한 모든 명령이 실패합니다.

```
Error converting data source schema: The schema for the data source
"runpod_endpoint_workers" couldn't be converted into a usable type.
AttributeName("workers"): must have Required, Optional, or Computed set..
```

이 실습들은 **정확히** `= 1.0.8` 로 고정합니다. `~> 1.0.8` 같은 범위 지정은 조용히 1.0.9 로 해석되어 깨집니다.
</div>

### 1.0.8 과 1.0.9 의 스키마 차이

프로바이더 공식 예제가 1.0.9 기준이라 1.0.8 에서는 동작하지 않으므로 알아둘 필요가 있습니다.

| | v1.0.8 (여기서 사용) | v1.0.9 (깨짐) |
|---|---|---|
| `runpod_endpoint` 의 이미지 지정 | `template_id` → `runpod_template` 경유 | `image_name` 직접 지정 |
| GPU 선택 | `gpu_type_ids` (목록, 우선순위 순) | `gpu_type_id` (단일 문자열) |

1.0.8 에서 엔드포인트는 리소스 두 개로 구성됩니다. 이미지를 담은 템플릿을 먼저 등록하고 엔드포인트가 그것을 가리킵니다. 실제로는 이 쪽이 콘솔의 흐름을 더 충실히 반영하며, 하나의 템플릿으로 여러 엔드포인트를 만들 수 있습니다.

또한 공식 `examples/network_volume/main.tf` 는 `runpod_network_volume` 에 `type = ...` 을 설정하지만 1.0.8 에는 그런 속성이 없습니다(`storage_tier` 가 있음). 공식 예제는 동작하는 코드가 아니라 스케치로 취급하세요.

### 실제 API 로 검증한 항목

실제 키로 읽기 전용 호출과 `terraform plan` 만 사용해 확인했습니다. 생성한 것이 없으므로 비용도 없습니다.

| 확인 항목 | 결과 |
|---|---|
| 1.15.8 에서 `terraform init` | 프로바이더 `= 1.0.8` 정상 설치 |
| `terraform validate`, 두 실습 모두 | Success |
| `01-endpoint` 의 `terraform plan` | `Plan: 2 to add, 0 to change, 0 to destroy` |
| `gpu_type_ids` 기본값 | 둘 다 실제 카탈로그(48종)에 존재 |
| `data_center_id` 기본값 | `US-KS-2` 는 49개 중 실재, `global_network = true` |

"2 to add" 까지 도달했다는 것이 핵심입니다. 프로바이더 인증이 되고, 스키마가 맞고, 거부되는 항목이 없다는 뜻입니다. 리소스를 만드는 것은 `apply` 뿐입니다.

**미검증:** `apply`, 따라서 엔드포인트가 실제로 트래픽을 처리하는지, 그리고 `02-pod` 전체 — 과금되기 때문입니다.

<div class="note" markdown="1">
GPU 나 데이터센터 ID 를 추측하지 마세요. `data "runpod_data_centers"` 와 `data "runpod_gpu_types"` 로 읽으면 됩니다. 데이터소스만 있는 설정은 `apply` 해도 생성되는 것이 없습니다.
</div>

### 인증

프로바이더가 환경변수 `RUNPOD_API_KEY` 를 직접 읽으므로 어떤 `.tf` 나 `.tfvars` 파일에도 키가 들어가지 않습니다. 프로바이더 블록은 의도적으로 비어 있습니다.

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

### State 파일

`terraform.tfstate` 에는 프로바이더가 반환한 모든 값이 평문으로 기록됩니다. 저장소 `.gitignore` 는 `*.tfstate*`, `*.tfvars`, `.terraform/` 을 제외하고 `.terraform.lock.hcl` 은 의도적으로 남깁니다. 프로바이더 해시를 고정하므로 버전 관리 대상이 맞습니다.

<div class="warn" markdown="1">
가상의 우려가 아닙니다. Runpod 공식 프로바이더 레포에는 `examples/pytorch/terraform.tfstate` 가 커밋돼 있습니다. 이 습관은 따라하지 마세요.
</div>

[저장소에서 전체 트랙 보기 →](https://github.com/litkhai/runpod-hols/tree/main/terraform)

</div>
