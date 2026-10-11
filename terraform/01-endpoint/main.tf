# Provision the Lab 01 hello-worker as a Serverless endpoint.
# serverless/01-hello-worker 를 Serverless 엔드포인트로 프로비저닝한다.

# No api_key here on purpose. The provider reads RUNPOD_API_KEY from the
# environment, which keeps the secret out of .tf and .tfvars files entirely.
#   export RUNPOD_API_KEY="..."   (or: set -a; . ../../.env; set +a)
#
# api_key 를 의도적으로 적지 않았다. 프로바이더가 환경변수 RUNPOD_API_KEY 를 직접 읽으므로
# .tf 와 .tfvars 어디에도 비밀값이 남지 않는다.
provider "runpod" {}

# An endpoint does not take an image directly — it points at a template, and
# the template holds the image. This mirrors the console, where you register a
# template first and then attach endpoints to it. One template can back several
# endpoints with different scaling settings.
#
# 엔드포인트는 이미지를 직접 받지 않는다. 템플릿을 가리키고, 이미지는 템플릿이 갖는다.
# 콘솔에서 템플릿을 먼저 등록하고 엔드포인트를 붙이는 흐름과 동일하다.
# 하나의 템플릿으로 스케일링 설정이 다른 여러 엔드포인트를 만들 수 있다.
resource "runpod_template" "hello" {
  name       = var.template_name
  image_name = var.image_name

  # Marks this as a Serverless template rather than a Pod template.
  # Pod 템플릿이 아니라 Serverless 템플릿임을 표시한다.
  is_serverless = true

  container_disk_in_gb = var.container_disk_in_gb

  # Provider 1.0.8 declares these Optional but not Computed, while the API
  # fills them in on create. Left unset, apply fails with "Provider produced
  # inconsistent result after apply" and leaves the template tainted.
  # Set them to what the API returns. An empty ports list is not kept — the
  # API fills in its defaults — and Serverless workers do not use them.
  #
  # 프로바이더 1.0.8 은 이 속성들을 Optional 로만 선언했는데(Computed 아님),
  # API 는 생성 시 값을 채워 넣는다. 비워 두면 apply 가
  # "Provider produced inconsistent result after apply" 로 실패하고
  # 템플릿이 tainted 로 남는다. API 가 돌려주는 값으로 맞춘다. 빈 ports 목록은
  # 유지되지 않고 API 기본값으로 채워지며, Serverless 워커는 포트를 쓰지 않는다.
  readme                     = ""
  container_registry_auth_id = ""
  ports                      = ["8888/http", "22/tcp"]
}

resource "runpod_endpoint" "hello" {
  name        = var.endpoint_name
  template_id = runpod_template.hello.id

  # A priority-ordered list, not a single value. Runpod walks the list and
  # takes the first type with capacity, so a second entry is cheap insurance
  # against the first being unavailable.
  #
  # 단일 값이 아니라 우선순위 목록이다. Runpod 이 목록을 순서대로 확인해
  # 용량이 있는 첫 타입을 사용하므로, 두 번째 항목을 넣어두면 첫 타입이
  # 없을 때를 저렴하게 대비할 수 있다.
  gpu_type_ids = var.gpu_type_ids
  gpu_count    = 1

  # workers_min = 0 is what makes this lab nearly free: with no warm workers,
  # an idle endpoint costs nothing. Raising it bills continuously.
  #
  # workers_min = 0 이 이 실습을 사실상 무료로 만드는 지점이다. 워밍된 워커가 없으므로
  # 유휴 상태의 엔드포인트는 비용이 발생하지 않는다. 값을 올리면 상시 과금된다.
  workers_min = 0
  workers_max = var.workers_max

  # Seconds a worker stays alive after finishing a job, waiting for the next.
  # Higher = fewer cold starts, more cost.
  #
  # 작업을 마친 워커가 다음 요청을 기다리며 살아있는 시간(초).
  # 값이 클수록 콜드 스타트는 줄고 비용은 늘어난다.
  idle_timeout = var.idle_timeout

  # Same provider 1.0.8 gap as the template: the API returns "" here.
  # 템플릿과 같은 프로바이더 1.0.8 문제. API 가 "" 를 돌려준다.
  network_volume_id = ""
}
