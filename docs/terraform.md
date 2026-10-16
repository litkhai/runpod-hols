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

The provider's own examples target 1.0.9 and will not work on 1.0.8:

| | v1.0.8 (used here) | v1.0.9 (broken) |
|---|---|---|
| `runpod_endpoint` image | via `template_id` → `runpod_template` | `image_name` directly |
| GPU selection | `gpu_type_ids` (list, priority order) | `gpu_type_id` (single string) |

On 1.0.8 an endpoint is a two-resource affair — register a template holding the image, then point an endpoint at it. That mirrors the console more faithfully, and one template can back several endpoints.

Also, the upstream `examples/network_volume/main.tf` sets `type = ...` on `runpod_network_volume`, but no such attribute exists in 1.0.8 (it has `storage_tier`). Treat the upstream examples as sketches, not working code.

### Verified against the live API

Read-only calls and `terraform plan` against a real key — nothing created, nothing billed:

| Check | Result |
|---|---|
| `terraform init` on 1.15.8 | Provider `= 1.0.8` installs cleanly |
| `terraform validate`, both labs | Success |
| `terraform plan` on `01-endpoint` | `Plan: 2 to add, 0 to change, 0 to destroy` |
| `gpu_type_ids` defaults | Both appear in the live catalogue of 48 GPU types |
| `data_center_id` default | `US-KS-2` exists among 49, `global_network = true` |

Reaching "2 to add" is the meaningful part: the provider authenticates, the schema matches, and nothing is rejected. Only `apply` creates resources.

**`apply` and `destroy` on `01-endpoint`, 2026-10-11** (Terraform 1.16.4, provider 1.0.8): both resources created, `plan` straight after showed no changes, `destroy` left the account empty. It needed two workarounds:

| What happened | Fix in `main.tf` |
|---|---|
| `Provider produced inconsistent result after apply` on `runpod_template` — `.readme`, `.container_registry_auth_id`, `.ports` came back filled in; the template was left tainted | `readme = ""`, `container_registry_auth_id = ""`, `ports = ["8888/http", "22/tcp"]` (`[]` is not kept) |
| Same on `runpod_endpoint` for `.network_volume_id` | `network_volume_id = ""` |

The image must be one the template can pull on its own: a console-built `registry.runpod.net` image fails with `Failed to get Hub registry auth`.

**Not verified:** the endpoint serving a request (needs a pushed image), and all of `02-pod`.

<div class="note" markdown="1">
Don't guess GPU or data-center IDs. Read them from `data "runpod_data_centers"` and `data "runpod_gpu_types"` — a data-source-only config creates nothing on `apply`.
</div>

### Lessons from the first apply

From running `apply` → request → `destroy` on `01-endpoint`, 2026-10-11:

| Lesson | What showed it |
|---|---|
| **`plan` passing does not mean `apply` will.** `plan` validates the config against the schema; only `apply` sees what the API sends back | `plan` said `2 to add`; `apply` then failed twice on values the API filled in |
| **A failed `apply` can still create a real resource.** After the error, check `terraform state list` and the account, not just the exit code | The template existed in the account and sat in state as `tainted`; the next `apply` replaced it and `destroy` removed it |
| **Find Optional-but-not-Computed attributes before applying.** `terraform providers schema -json` lists them; if the API fills one in, set it explicitly to the value the API returns | `readme`, `container_registry_auth_id`, `ports`, `network_volume_id` |
| **Check for drift right after `apply`.** `terraform plan -detailed-exitcode` returns 0 when config and live state agree | Returned 0 after the fixes |
| **Confirm the account is empty after `destroy`.** List templates and endpoints, and read `myself { currentSpendPerHr }` | No `hol-*` template, no extra endpoint, spend 0 |
| **Use an image the template can pull on its own.** Console GitHub builds land in `registry.runpod.net`, which only serves the templates the console created | `Failed to get Hub registry auth` on every worker |

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

프로바이더 공식 예제는 1.0.9 기준이라 1.0.8 에서는 동작하지 않습니다.

| | v1.0.8 (여기서 사용) | v1.0.9 (깨짐) |
|---|---|---|
| `runpod_endpoint` 의 이미지 지정 | `template_id` → `runpod_template` 경유 | `image_name` 직접 지정 |
| GPU 선택 | `gpu_type_ids` (목록, 우선순위 순) | `gpu_type_id` (단일 문자열) |

1.0.8 에서 엔드포인트는 리소스 두 개로 구성됩니다. 이미지를 담은 템플릿을 먼저 등록하고 엔드포인트가 그것을 가리킵니다. 실제로는 이 쪽이 콘솔의 흐름을 더 충실히 반영하며, 하나의 템플릿으로 여러 엔드포인트를 만들 수 있습니다.

또한 공식 `examples/network_volume/main.tf` 는 `runpod_network_volume` 에 `type = ...` 을 설정하지만 1.0.8 에는 그런 속성이 없습니다(`storage_tier` 가 있음). 공식 예제는 동작하는 코드가 아니라 스케치로 취급하세요.

### 실제 API 로 검증한 항목

실제 키로 읽기 전용 호출과 `terraform plan` 만 실행한 항목 — 생성한 것 없음, 과금 없음:

| 확인 항목 | 결과 |
|---|---|
| 1.15.8 에서 `terraform init` | 프로바이더 `= 1.0.8` 정상 설치 |
| `terraform validate`, 두 실습 모두 | Success |
| `01-endpoint` 의 `terraform plan` | `Plan: 2 to add, 0 to change, 0 to destroy` |
| `gpu_type_ids` 기본값 | 둘 다 실제 카탈로그(48종)에 존재 |
| `data_center_id` 기본값 | `US-KS-2` 는 49개 중 실재, `global_network = true` |

"2 to add" 까지 도달했다는 것이 핵심입니다. 프로바이더 인증이 되고, 스키마가 맞고, 거부되는 항목이 없다는 뜻입니다. 리소스를 만드는 것은 `apply` 뿐입니다.

**`01-endpoint` 의 `apply` 와 `destroy`, 2026-10-11** (Terraform 1.16.4, 프로바이더 1.0.8): 두 리소스가 생성됐고, 직후의 `plan` 은 변경 없음, `destroy` 후 계정에 남은 것이 없었습니다. 우회 두 가지가 필요했습니다:

| 일어난 일 | `main.tf` 의 수정 |
|---|---|
| `runpod_template` 에서 `Provider produced inconsistent result after apply` — `.readme`, `.container_registry_auth_id`, `.ports` 가 채워져 돌아옴. 템플릿은 tainted 로 남음 | `readme = ""`, `container_registry_auth_id = ""`, `ports = ["8888/http", "22/tcp"]` (`[]` 는 유지되지 않음) |
| `runpod_endpoint` 에서 `.network_volume_id` 로 같은 오류 | `network_volume_id = ""` |

이미지는 템플릿이 스스로 pull 할 수 있어야 합니다. 콘솔이 빌드한 `registry.runpod.net` 이미지는 `Failed to get Hub registry auth` 로 실패합니다.

**미검증:** 엔드포인트의 요청 처리(푸시한 이미지 필요), 그리고 `02-pod` 전체.

<div class="note" markdown="1">
GPU 나 데이터센터 ID 를 추측하지 마세요. `data "runpod_data_centers"` 와 `data "runpod_gpu_types"` 로 읽으면 됩니다. 데이터소스만 있는 설정은 `apply` 해도 생성되는 것이 없습니다.
</div>

### 첫 apply 에서 얻은 교훈

2026-10-11 `01-endpoint` 에서 `apply` → 요청 → `destroy` 를 실행하며 얻은 것:

| 교훈 | 근거 |
|---|---|
| **`plan` 이 통과해도 `apply` 가 통과한다는 보장은 없습니다.** `plan` 은 설정을 스키마와 대조할 뿐이고, API 가 돌려주는 값은 `apply` 에서야 보입니다 | `plan` 은 `2 to add` 였지만 `apply` 는 API 가 채운 값 때문에 두 번 실패했다 |
| **실패한 `apply` 도 실제 리소스를 만들 수 있습니다.** 오류 뒤에는 종료 코드만 보지 말고 `terraform state list` 와 계정을 확인하세요 | 템플릿이 계정에 생성됐고 state 에 `tainted` 로 남았다. 다음 `apply` 가 교체했고 `destroy` 가 지웠다 |
| **Optional 이면서 Computed 가 아닌 속성을 apply 전에 찾으세요.** `terraform providers schema -json` 으로 볼 수 있고, API 가 채우는 속성이면 API 가 돌려주는 값으로 명시합니다 | `readme`, `container_registry_auth_id`, `ports`, `network_volume_id` |
| **`apply` 직후 drift 를 확인하세요.** `terraform plan -detailed-exitcode` 가 0 이면 설정과 실제 상태가 일치합니다 | 수정 후 0 을 반환했다 |
| **`destroy` 후 계정이 비었는지 확인하세요.** 템플릿·엔드포인트 목록과 `myself { currentSpendPerHr }` 를 봅니다 | `hol-*` 템플릿 없음, 추가 엔드포인트 없음, 비용 0 |
| **템플릿이 스스로 pull 할 수 있는 이미지를 쓰세요.** 콘솔 GitHub 빌드는 `registry.runpod.net` 에 올라가며, 이 레지스트리는 콘솔이 만든 템플릿에만 이미지를 내줍니다 | 모든 워커에서 `Failed to get Hub registry auth` |

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
