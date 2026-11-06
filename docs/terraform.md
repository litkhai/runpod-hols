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
| `data_center_id` default (then `US-KS-2`) | `US-KS-2` exists among 49, `global_network = true`; now `EU-RO-1`, see below |

Reaching "2 to add" is the meaningful part: the provider authenticates, the schema matches, and nothing is rejected. Only `apply` creates resources.

**`apply` and `destroy` on `01-endpoint`, 2026-10-11** (Terraform 1.16.4, provider 1.0.8): both resources created, `plan` straight after showed no changes, `destroy` left the account empty. It needed two workarounds:

| What happened | Fix in `main.tf` |
|---|---|
| `Provider produced inconsistent result after apply` on `runpod_template` — `.readme`, `.container_registry_auth_id`, `.ports` came back filled in; the template was left tainted | `readme = ""`, `container_registry_auth_id = ""`, `ports = ["8888/http", "22/tcp"]` (`[]` is not kept) |
| Same on `runpod_endpoint` for `.network_volume_id` | `network_volume_id = ""` |

The image must be one the template can pull on its own: a console-built `registry.runpod.net` image fails with `Failed to get Hub registry auth`.

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

**Not verified:** Jupyter on the `02-pod` Pod.

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
| `data_center_id` 기본값 (당시 `US-KS-2`) | `US-KS-2` 는 49개 중 실재, `global_network = true`; 현재 `EU-RO-1`, 아래 참조 |

"2 to add" 까지 도달했다는 것이 핵심입니다. 프로바이더 인증이 되고, 스키마가 맞고, 거부되는 항목이 없다는 뜻입니다. 리소스를 만드는 것은 `apply` 뿐입니다.

**`01-endpoint` 의 `apply` 와 `destroy`, 2026-10-11** (Terraform 1.16.4, 프로바이더 1.0.8): 두 리소스가 생성됐고, 직후의 `plan` 은 변경 없음, `destroy` 후 계정에 남은 것이 없었습니다. 우회 두 가지가 필요했습니다:

| 일어난 일 | `main.tf` 의 수정 |
|---|---|
| `runpod_template` 에서 `Provider produced inconsistent result after apply` — `.readme`, `.container_registry_auth_id`, `.ports` 가 채워져 돌아옴. 템플릿은 tainted 로 남음 | `readme = ""`, `container_registry_auth_id = ""`, `ports = ["8888/http", "22/tcp"]` (`[]` 는 유지되지 않음) |
| `runpod_endpoint` 에서 `.network_volume_id` 로 같은 오류 | `network_volume_id = ""` |

이미지는 템플릿이 스스로 pull 할 수 있어야 합니다. 콘솔이 빌드한 `registry.runpod.net` 이미지는 `Failed to get Hub registry auth` 로 실패합니다.

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

**미검증:** `02-pod` Pod 의 Jupyter.

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

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

把 Serverless 和 Pod 路线在控制台中手动完成的所有操作，改为以声明式方式完成。

| 实验 | 创建的资源 | 空闲时的费用 |
|---|---|---|
| [01-endpoint](https://github.com/litkhai/runpod-hols/tree/main/terraform/01-endpoint) | `runpod_template` + `runpod_endpoint` | **无**——`workers_min = 0` |
| [02-pod](https://github.com/litkhai/runpod-hols/tree/main/terraform/02-pod) | `runpod_pod`（+ 可选的 `runpod_network_volume`） | **按分钟计费** |

### 请先阅读——两个阻断性问题

<div class="danger" markdown="1">
**1. Terraform 1.5.x 无法安装这个 provider。**

```
error decoding signing key: openpgp: invalid data: armor invalid
```

需要 **Terraform 1.6+**；已在 1.15.8 上验证。BUSL 许可证变更之后，Homebrew 的 `terraform` formula 被冻结在 1.5.7，所以 `brew install terraform` 安装的版本无法使用。请使用 `brew install hashicorp/tap/terraform`。
</div>

<div class="danger" markdown="1">
**2. Provider v1.0.9 已发布但无法使用。**

它的 `endpoint_jobs` 和 `endpoint_workers` data source 声明了一个 `Required`、`Optional`、`Computed` 都没有设置的属性，因此 Terraform 根本无法加载 provider schema。所有命令都会失败——`validate`、`plan` 和 `apply` 无一例外：

```
Error converting data source schema: The schema for the data source
"runpod_endpoint_workers" couldn't be converted into a usable type.
AttributeName("workers"): must have Required, Optional, or Computed set..
```

这些实验**精确**固定为 `= 1.0.8`。像 `~> 1.0.8` 这样的范围会悄无声息地解析为 1.0.9 并导致失败。
</div>

### 1.0.8 与 1.0.9 的 schema 差异

provider 自带的示例针对的是 1.0.9，在 1.0.8 上无法运行：

| | v1.0.8（本文使用） | v1.0.9（已损坏） |
|---|---|---|
| `runpod_endpoint` 的镜像 | 通过 `template_id` → `runpod_template` | 直接使用 `image_name` |
| GPU 选择 | `gpu_type_ids`（列表，按优先级排序） | `gpu_type_id`（单个字符串） |

在 1.0.8 上，一个 endpoint 由两个资源组成——先注册一个包含镜像的 template，再让 endpoint 指向它。这更忠实地反映了控制台的结构，而且一个 template 可以支撑多个 endpoint。

另外，上游的 `examples/network_volume/main.tf` 在 `runpod_network_volume` 上设置了 `type = ...`，但 1.0.8 中并不存在这个属性（它有的是 `storage_tier`）。请把上游示例当作草图，而不是可运行的代码。

### 针对真实 API 的验证

使用真实密钥进行只读调用和 `terraform plan`——没有创建任何资源，也没有产生任何费用：

| 检查项 | 结果 |
|---|---|
| 在 1.15.8 上执行 `terraform init` | Provider `= 1.0.8` 顺利安装 |
| 两个实验的 `terraform validate` | 成功 |
| 在 `01-endpoint` 上执行 `terraform plan` | `Plan: 2 to add, 0 to change, 0 to destroy` |
| `gpu_type_ids` 的默认值 | 两者都出现在包含 48 种 GPU 类型的实时目录中 |
| `data_center_id` 默认值（当时为 `US-KS-2`） | `US-KS-2` 存在于 49 个之中，`global_network = true`；现在为 `EU-RO-1`，见下文 |

走到 "2 to add" 才是有意义的部分：provider 完成认证、schema 匹配，并且没有任何内容被拒绝。只有 `apply` 才会创建资源。

**2026-10-11 在 `01-endpoint` 上执行 `apply` 和 `destroy`**（Terraform 1.16.4，provider 1.0.8）：两个资源都已创建，紧接着的 `plan` 显示没有变更，`destroy` 之后账号被清空。这需要两个变通办法：

| 发生了什么 | `main.tf` 中的修复 |
|---|---|
| `runpod_template` 上出现 `Provider produced inconsistent result after apply`——`.readme`、`.container_registry_auth_id`、`.ports` 返回时被填入了值；template 被标记为 tainted | `readme = ""`、`container_registry_auth_id = ""`、`ports = ["8888/http", "22/tcp"]`（`[]` 不会被保留） |
| `runpod_endpoint` 的 `.network_volume_id` 出现同样的问题 | `network_volume_id = ""` |

镜像必须是 template 能够自行拉取的：在控制台构建的 `registry.runpod.net` 镜像会以 `Failed to get Hub registry auth` 失败。

**2026-10-20 在 `01-endpoint` 上处理请求**（相同的 Terraform 和 provider，镜像 `docker.io/litkhai/hello-worker:v1.0.0`，由 Lab 01 以 `--platform linux/amd64` 构建并推送到 Docker Hub）：`apply` 创建两个资源各用时 1 s。一次带 `{"input": {"name": "Terraform"}}` 的 `/run` 返回 `COMPLETED` 以及 `{"greeting": "Hello, Terraform!"}`，`delayTime` 6,280 ms，`executionTime` 57 ms，运行在 RTX 4090 上——即 `gpu_type_ids` 中的第一项。worker 日志显示按 digest 拉取、SDK 1.12.0 的全部七项 fitness 检查通过，随后是该 job 的 `Started.` 和 `Finished.`。`destroy` 删除了两者；不再有名为 `hol-hello-worker` 的 template 或 endpoint，`currentSpendPerHr` 为 0。

**2026-10-16 在 `02-pod` 上执行 `apply` 和 `destroy`**（Terraform 1.16.4，provider 1.0.8，镜像 `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404`）：共运行三次，全部已销毁，账号中没有留下 Pod，没有 network volume，`currentSpendPerHr` 为 0。

| 运行 | 结果 |
|---|---|
| 不带 network volume | 2 s 内 `Apply complete`；约 3 分钟后 SSH 端口公开；`ssh root@<ip> -p <port>` 可用，`nvidia-smi` 正常，`torch.cuda.is_available()` 为 True；`destroy` 干净 |
| 带 `EU-RO-1` 中 20 GB 的 network volume | volume 和 Pod 均已创建；Pod 落在 `EU-RO-1`，volume 挂载于 `/workspace`（网络文件系统），写入文件并成功读回；`destroy` 删除了两者 |
| 带 `lifecycle { ignore_changes = [machine_id] }` | `apply` 之后紧接着的 `plan` 没有显示资源变更，只有 output 值 |

它揭示了：

| 发现 | 后果 |
|---|---|
| **`gpu_type_id` 不会被发送。** provider 的创建请求中不带任何 GPU 字段，所以 Runpod 按可用性挑选（`gpuTypePriority` 默认为 `availability`） | 请求的是 RTX A4500（$0.25/hr）；每个 Pod 实际都是 RTX 4090，$0.89/hr，而 state 中仍写着 A4500。`apply` 之后请读取 `cost_per_hr` |
| **`machine_id` 会漂移。** Read 会记录 Pod 落在的机器；该属性是 Optional 而非 Computed | 如果没有上面的 `ignore_changes`，`apply` 之后的每次 `plan` 都会提议一次原地更新 |
| **`start_ssh` / `start_jupyter` 也不会被发送** | SSH 照样能用——镜像默认暴露 22 端口。Jupyter 未检查 |
| **volume 所在的数据中心必须支持存储。** 之前的默认值 `US-KS-2` 报告 `storageSupport = false` | 默认值已改为 `EU-RO-1`。apply 之前请检查 `dataCenters { id storageSupport }` |

**未验证：** `02-pod` 的 Pod 上的 Jupyter。

<div class="note" markdown="1">
不要猜测 GPU 或数据中心的 ID。请从 `data "runpod_data_centers"` 和 `data "runpod_gpu_types"` 中读取——只包含 data source 的配置在 `apply` 时不会创建任何东西。
</div>

### 第一次 apply 的教训

来自 2026-10-11 在 `01-endpoint` 上执行 `apply` → 请求 → `destroy` 的过程：

| 教训 | 依据 |
|---|---|
| **`plan` 通过不代表 `apply` 会成功。** `plan` 只依据 schema 校验配置；只有 `apply` 才能看到 API 返回的内容 | `plan` 显示 `2 to add`；随后 `apply` 因 API 填入的值失败了两次 |
| **失败的 `apply` 仍可能创建真实资源。** 出错后请检查 `terraform state list` 和账号，而不只是看退出码 | template 存在于账号中，并在 state 中处于 `tainted` 状态；下一次 `apply` 替换了它，`destroy` 删除了它 |
| **在 apply 之前找出 Optional 但非 Computed 的属性。** `terraform providers schema -json` 会列出它们；如果 API 会填入其中某个属性，就显式设置为 API 返回的值 | `readme`、`container_registry_auth_id`、`ports`、`network_volume_id` |
| **`apply` 之后立即检查漂移。** 当配置与实际状态一致时，`terraform plan -detailed-exitcode` 返回 0 | 修复之后返回 0 |
| **`destroy` 之后确认账号已清空。** 列出 template 和 endpoint，并读取 `myself { currentSpendPerHr }` | 没有 `hol-*` template，没有多余的 endpoint，支出为 0 |
| **使用 template 能自行拉取的镜像。** 控制台的 GitHub 构建产物位于 `registry.runpod.net`，它只为控制台创建的 template 提供服务 | 每个 worker 上都出现 `Failed to get Hub registry auth` |

### 认证

provider 从环境变量中读取 `RUNPOD_API_KEY`，所以任何 `.tf` 或 `.tfvars` 文件中都不放密钥。provider 块是刻意留空的：

```hcl
provider "runpod" {}
```

### 工作流程

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

### State 文件

`terraform.tfstate` 以明文记录 provider 返回的一切。仓库的 `.gitignore` 覆盖了 `*.tfstate*`、`*.tfvars` 和 `.terraform/`，同时刻意保留 `.terraform.lock.hcl`——它固定了 provider 的哈希，应当纳入版本控制。

<div class="warn" markdown="1">
这并非假设性的担忧：Runpod 官方 provider 仓库中就提交了 `examples/pytorch/terraform.tfstate`。不要沿袭这种习惯。
</div>

[仓库中的完整路线 →](https://github.com/litkhai/runpod-hols/tree/main/terraform)

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

Serverless と Pod のトラックでコンソールから手作業で行うことを、すべて宣言的に行います。

| ラボ | 作成するもの | アイドル時のコスト |
|---|---|---|
| [01-endpoint](https://github.com/litkhai/runpod-hols/tree/main/terraform/01-endpoint) | `runpod_template` + `runpod_endpoint` | **なし**（`workers_min = 0`） |
| [02-pod](https://github.com/litkhai/runpod-hols/tree/main/terraform/02-pod) | `runpod_pod`（+ 任意で `runpod_network_volume`） | **分単位で課金** |

### 最初に読んでください：2 つのブロッキング問題

<div class="danger" markdown="1">
**1. Terraform 1.5.x ではこの provider をインストールできません。**

```
error decoding signing key: openpgp: invalid data: armor invalid
```

**Terraform 1.6 以上**が必要です。1.15.8 で確認しました。BUSL ライセンス変更の後、Homebrew の `terraform` formula は 1.5.7 で凍結されているため、`brew install terraform` では動かないバージョンが入ります。`brew install hashicorp/tap/terraform` を使ってください。
</div>

<div class="danger" markdown="1">
**2. Provider v1.0.9 は公開されていますが使えません。**

`endpoint_jobs` と `endpoint_workers` の data source が、`Required`、`Optional`、`Computed` のいずれも設定されていない属性を宣言しているため、Terraform は provider の schema をまったく読み込めません。`validate`、`plan`、`apply` のいずれも、すべてのコマンドが失敗します。

```
Error converting data source schema: The schema for the data source
"runpod_endpoint_workers" couldn't be converted into a usable type.
AttributeName("workers"): must have Required, Optional, or Computed set..
```

これらのラボは**厳密に** `= 1.0.8` に固定しています。`~> 1.0.8` のような範囲指定は黙って 1.0.9 に解決され、壊れます。
</div>

### 1.0.8 と 1.0.9 の schema の違い

provider 自体のサンプルは 1.0.9 向けで、1.0.8 では動きません。

| | v1.0.8（ここで使用） | v1.0.9（壊れている） |
|---|---|---|
| `runpod_endpoint` のイメージ | `template_id` → `runpod_template` 経由 | `image_name` を直接指定 |
| GPU の選択 | `gpu_type_ids`（リスト、優先順） | `gpu_type_id`（単一の文字列） |

1.0.8 では endpoint は 2 つのリソースで構成されます。イメージを持つ template を登録し、endpoint がそれを指すようにします。このほうがコンソールの構造に忠実で、1 つの template で複数の endpoint を支えられます。

また、上流の `examples/network_volume/main.tf` は `runpod_network_volume` に `type = ...` を設定していますが、1.0.8 にはそのような属性はありません（あるのは `storage_tier` です）。上流のサンプルは動くコードではなく、スケッチとして扱ってください。

### 実際の API に対する検証

本物のキーで読み取り専用の呼び出しと `terraform plan` を実行しました。何も作成しておらず、課金もありません。

| チェック | 結果 |
|---|---|
| 1.15.8 での `terraform init` | Provider `= 1.0.8` が問題なくインストールされる |
| 両ラボの `terraform validate` | 成功 |
| `01-endpoint` での `terraform plan` | `Plan: 2 to add, 0 to change, 0 to destroy` |
| `gpu_type_ids` のデフォルト | どちらも 48 種類の GPU タイプを含むライブカタログに存在 |
| `data_center_id` のデフォルト（当時は `US-KS-2`） | `US-KS-2` は 49 件の中に存在し、`global_network = true`。現在は `EU-RO-1`、後述 |

"2 to add" までたどり着けたことに意味があります。provider が認証され、schema が一致し、何も拒否されていません。リソースを作成するのは `apply` だけです。

**2026-10-11、`01-endpoint` での `apply` と `destroy`**（Terraform 1.16.4、provider 1.0.8）：両方のリソースが作成され、直後の `plan` は変更なしを示し、`destroy` 後にアカウントは空になりました。2 つの回避策が必要でした。

| 何が起きたか | `main.tf` での修正 |
|---|---|
| `runpod_template` で `Provider produced inconsistent result after apply`。`.readme`、`.container_registry_auth_id`、`.ports` に値が入って返ってきた。template は tainted のまま残った | `readme = ""`、`container_registry_auth_id = ""`、`ports = ["8888/http", "22/tcp"]`（`[]` は保持されない） |
| `runpod_endpoint` の `.network_volume_id` でも同じ | `network_volume_id = ""` |

イメージは template が単独で pull できるものでなければなりません。コンソールでビルドした `registry.runpod.net` のイメージは `Failed to get Hub registry auth` で失敗します。

**2026-10-20、`01-endpoint` でのリクエスト処理**（同じ Terraform と provider、イメージは Lab 01 から `--platform linux/amd64` でビルドして Docker Hub に push した `docker.io/litkhai/hello-worker:v1.0.0`）：`apply` は両リソースをそれぞれ 1 s で作成しました。`{"input": {"name": "Terraform"}}` を付けた 1 回の `/run` は `COMPLETED` と `{"greeting": "Hello, Terraform!"}` を返し、`delayTime` 6,280 ms、`executionTime` 57 ms で、`gpu_type_ids` の最初の項目である RTX 4090 上で動きました。worker のログには digest による pull、SDK 1.12.0 の 7 つの fitness チェックすべての通過、そして job の `Started.` と `Finished.` が記録されていました。`destroy` で両方が削除され、`hol-hello-worker` という名前の template も endpoint も残らず、`currentSpendPerHr` は 0 でした。

**2026-10-16、`02-pod` での `apply` と `destroy`**（Terraform 1.16.4、provider 1.0.8、イメージ `runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404`）：3 回実行し、すべて削除しました。アカウントには Pod も network volume も残らず、`currentSpendPerHr` は 0 でした。

| 実行 | 結果 |
|---|---|
| network volume なし | 2 s で `Apply complete`。約 3 分後に SSH ポートが公開。`ssh root@<ip> -p <port>` が動作し、`nvidia-smi` と `torch.cuda.is_available()` は True。`destroy` もきれいに完了 |
| `EU-RO-1` の 20 GB network volume あり | volume と Pod が作成された。Pod は `EU-RO-1` に配置され、volume は `/workspace` にマウント（ネットワークファイルシステム）。ファイルを書き込んで読み戻せた。`destroy` で両方が削除された |
| `lifecycle { ignore_changes = [machine_id] }` あり | `apply` 直後の `plan` はリソースの変更を示さず、output の値だけを表示 |

わかったこと：

| 発見 | 影響 |
|---|---|
| **`gpu_type_id` は送信されません。** provider の作成リクエストには GPU のフィールドがないため、Runpod は空き状況で選びます（`gpuTypePriority` のデフォルトは `availability`） | RTX A4500（$0.25/hr）を指定したのに、どの Pod も $0.89/hr の RTX 4090 で立ち上がり、state には A4500 と書かれたままだった。`apply` の後は `cost_per_hr` を確認すること |
| **`machine_id` がドリフトします。** Read は Pod が配置されたマシンを保存しますが、この属性は Optional であって Computed ではありません | 上記の `ignore_changes` がないと、`apply` 後の毎回の `plan` が in-place の更新を提案する |
| **`start_ssh` / `start_jupyter` も送信されません** | それでも SSH は動いた。イメージがデフォルトで 22 番ポートを公開しているため。Jupyter は未確認 |
| **volume のデータセンターはストレージに対応している必要があります。** 以前のデフォルトの `US-KS-2` は `storageSupport = false` を返した | デフォルトを `EU-RO-1` に変更。apply の前に `dataCenters { id storageSupport }` を確認すること |

**未検証：** `02-pod` の Pod 上の Jupyter。

<div class="note" markdown="1">
GPU やデータセンターの ID を推測しないでください。`data "runpod_data_centers"` と `data "runpod_gpu_types"` から読み取ってください。data source だけの設定は `apply` しても何も作成しません。
</div>

### 最初の apply から得た教訓

2026-10-11 に `01-endpoint` で `apply` → リクエスト → `destroy` を実行した結果から：

| 教訓 | 根拠 |
|---|---|
| **`plan` が通っても `apply` が通るとは限りません。** `plan` は schema に対して設定を検証するだけで、API が返すものを見るのは `apply` だけです | `plan` は `2 to add` だったが、その後 `apply` は API が埋めた値のせいで 2 回失敗した |
| **失敗した `apply` でも実際のリソースが作られることがあります。** エラーの後は終了コードだけでなく、`terraform state list` とアカウントを確認してください | template はアカウントに存在し、state では `tainted` になっていた。次の `apply` で置き換えられ、`destroy` で削除された |
| **apply の前に Optional だが Computed ではない属性を洗い出してください。** `terraform providers schema -json` で一覧できます。API が値を埋めるものは、API が返す値を明示的に設定します | `readme`、`container_registry_auth_id`、`ports`、`network_volume_id` |
| **`apply` の直後にドリフトを確認してください。** 設定と実際の状態が一致していれば `terraform plan -detailed-exitcode` は 0 を返します | 修正後は 0 を返した |
| **`destroy` の後にアカウントが空であることを確認してください。** template と endpoint を一覧し、`myself { currentSpendPerHr }` を読みます | `hol-*` の template なし、余分な endpoint なし、支出 0 |
| **template が単独で pull できるイメージを使ってください。** コンソールの GitHub ビルドは `registry.runpod.net` に置かれ、そこはコンソールが作成した template にしか提供しません | すべての worker で `Failed to get Hub registry auth` |

### 認証

provider は環境変数から `RUNPOD_API_KEY` を読み取るため、`.tf` や `.tfvars` ファイルにキーを書くことはありません。provider ブロックは意図的に空にしています。

```hcl
provider "runpod" {}
```

### ワークフロー

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

### State ファイル

`terraform.tfstate` には provider が返したものすべてが平文で記録されます。リポジトリの `.gitignore` は `*.tfstate*`、`*.tfvars`、`.terraform/` を対象にしつつ、`.terraform.lock.hcl` は意図的に残しています。これは provider のハッシュを固定するもので、バージョン管理に含めるべきものです。

<div class="warn" markdown="1">
仮定の話ではありません。Runpod の公式 provider リポジトリには `examples/pytorch/terraform.tfstate` がコミットされています。この習慣を真似しないでください。
</div>

[リポジトリのトラック全体 →](https://github.com/litkhai/runpod-hols/tree/main/terraform)

</div>
