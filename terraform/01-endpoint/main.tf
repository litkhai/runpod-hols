# Provision the Lab 01 hello-worker as a Serverless endpoint.
# serverless/01-hello-worker 를 Serverless 엔드포인트로 프로비저닝한다.

# No api_key here on purpose. The provider reads RUNPOD_API_KEY from the
# environment, which keeps the secret out of .tf and .tfvars files entirely.
#   export RUNPOD_API_KEY="..."   (or: set -a; . ../../.env; set +a)
#
# api_key 를 의도적으로 적지 않았다. 프로바이더가 환경변수 RUNPOD_API_KEY 를 직접 읽으므로
# .tf 와 .tfvars 어디에도 비밀값이 남지 않는다.
provider "runpod" {}

# Provider 2.0.0 (REST v2) can give an endpoint its image directly, but a
# template still mirrors the console: register the image once, attach several
# endpoints with different scaling settings to it.
#
# 프로바이더 2.0.0 (REST v2) 은 엔드포인트에 이미지를 직접 줄 수도 있지만, 템플릿을 두면
# 콘솔의 흐름과 같다. 이미지를 한 번 등록하고 스케일링 설정이 다른 엔드포인트 여러 개를 붙인다.
resource "runpod_template" "hello" {
  name  = var.template_name
  image = var.image_name

  # A Serverless template rather than a Pod template.
  # Pod 템플릿이 아니라 Serverless 템플릿.
  serverless = true

  disk = var.container_disk_in_gb
}

resource "runpod_serverless_endpoint" "hello" {
  name        = var.endpoint_name
  template_id = runpod_template.hello.id

  # QUEUE (run / runsync) or LOAD_BALANCER. Changing it replaces the endpoint.
  # QUEUE (run / runsync) 또는 LOAD_BALANCER. 바꾸면 엔드포인트가 교체된다.
  endpoint_type = "QUEUE"

  # Serverless picks GPU pools, not types, and places workers on whichever
  # listed pool has capacity — there is no order. Pool ids come from the
  # `pool` field of the runpod_gpu_types data source.
  #
  # Serverless 는 GPU 종류가 아니라 풀을 고르고, 여유가 있는 풀에 워커를 놓는다 (순서 없음).
  # 풀 id 는 runpod_gpu_types 데이터소스의 `pool` 필드에서 얻는다.
  gpu_pools = var.gpu_pools
  gpu_count = 1

  # Required in 2.0.0. QUEUE_DELAY adds a worker when a request has waited
  # this many seconds.
  # 2.0.0 에서 필수. QUEUE_DELAY 는 요청이 이 초만큼 기다리면 워커를 더한다.
  scaling_type  = "QUEUE_DELAY"
  scaling_value = 4

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
}
