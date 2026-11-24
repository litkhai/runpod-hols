variable "image_name" {
  type        = string
  description = <<-EOT
    Container image for the worker, e.g. "docker.io/<user>/hello-worker:v1.0.0".
    Build and push it first — see serverless/01-hello-worker.

    워커 컨테이너 이미지. 예: "docker.io/<사용자>/hello-worker:v1.0.0".
    먼저 빌드해서 푸시해야 한다 — serverless/01-hello-worker 참조.
  EOT
}

variable "template_name" {
  type        = string
  description = <<-EOT
    Template name shown in the console. If the endpoint create fails with
    "endpoint template names must be unique", pick a new name: on 2026-11-24
    the name used by the October runs was still refused, a fresh one was not.

    콘솔에 표시될 템플릿 이름. 엔드포인트 생성이 "endpoint template names must be
    unique" 로 실패하면 새 이름을 쓴다. 2026-11-24 에 10월 실행이 쓰던 이름은 계속
    거부됐고 새 이름은 받아들여졌다.
  EOT
  default     = "hol-hello-worker-v2"
}

variable "endpoint_name" {
  type        = string
  description = "Endpoint name shown in the console. / 콘솔에 표시될 엔드포인트 이름."
  default     = "hol-hello-worker"
}

variable "container_disk_in_gb" {
  type        = number
  description = "Container disk per worker. / 워커당 컨테이너 디스크 크기."
  default     = 5
}

variable "gpu_pools" {
  type        = list(string)
  description = <<-EOT
    Serverless GPU pools. Workers go to whichever listed pool has capacity;
    there is no order. ADA_24 holds the RTX 4090, AMPERE_16 the RTX A4000.
    List pools with the runpod_gpu_types data source (`pool`).

    Serverless GPU 풀. 워커는 여유가 있는 풀에 놓이며 순서는 없다.
    ADA_24 는 RTX 4090, AMPERE_16 은 RTX A4000 을 포함한다.
    풀 목록은 runpod_gpu_types 데이터소스의 `pool` 로 확인한다.
  EOT
  default     = ["ADA_24", "AMPERE_16"]
}

variable "workers_max" {
  type        = number
  description = "Scale-out ceiling. Keep small for labs. / 스케일아웃 상한. 실습에서는 작게 유지."
  default     = 2

  validation {
    condition     = var.workers_max >= 1 && var.workers_max <= 5
    error_message = "Keep workers_max between 1 and 5 for a lab. / 실습에서는 1~5 사이로 유지하세요."
  }
}

variable "idle_timeout" {
  type        = number
  description = "Seconds a worker idles before shutting down. / 워커가 종료되기까지 유휴 대기 시간(초)."
  default     = 5
}
