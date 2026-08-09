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
  description = "Template name shown in the console. / 콘솔에 표시될 템플릿 이름."
  default     = "hol-hello-worker-template"
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

variable "gpu_type_ids" {
  type        = list(string)
  description = <<-EOT
    GPU types in priority order. Runpod uses the first one with capacity.
    List valid IDs with `runpodctl get cloud` or the gpu_types data source.

    우선순위 순서의 GPU 타입 목록. Runpod 이 용량이 있는 첫 타입을 사용한다.
    유효한 ID 는 `runpodctl get cloud` 또는 gpu_types 데이터소스로 확인한다.
  EOT
  default     = ["NVIDIA GeForce RTX 4090", "NVIDIA RTX A4000"]
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
