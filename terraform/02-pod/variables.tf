variable "pod_name" {
  type        = string
  description = "Pod name shown in the console. / 콘솔에 표시될 Pod 이름."
  default     = "hol-lab-pod"
}

variable "image_name" {
  type        = string
  description = <<-EOT
    Pod image. Official templates live in runpod/containers.
    Pod 이미지. 공식 템플릿은 runpod/containers 에 있다.
  EOT
  default     = "runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404"
}

variable "gpu_type_id" {
  type        = string
  description = <<-EOT
    GPU type for the Pod. Check availability and pricing before applying —
    this one bills per minute.

    Pod 에 할당할 GPU 타입. 분 단위로 과금되므로 apply 전에 가용성과 단가를 확인할 것.
  EOT
  default     = "NVIDIA GeForce RTX 4090"
}

variable "gpu_count" {
  type        = number
  description = "GPUs attached to the Pod. / Pod 에 할당할 GPU 개수."
  default     = 1

  validation {
    condition     = var.gpu_count >= 1 && var.gpu_count <= 2
    error_message = "Keep gpu_count at 1-2 for a lab — cost scales linearly. / 실습에서는 1~2 로 유지하세요. 비용이 선형으로 증가합니다."
  }
}

variable "container_disk_in_gb" {
  type        = number
  description = "Scratch disk, destroyed with the Pod. / Pod 와 함께 소멸하는 임시 디스크."
  default     = 20
}

variable "volume_in_gb" {
  type        = number
  description = "Volume disk mounted at /workspace. / /workspace 에 마운트되는 볼륨 디스크 크기."
  default     = 20
}

variable "start_jupyter" {
  type        = bool
  description = "Start JupyterLab on boot. SSH is always enabled. / 부팅 시 JupyterLab 시작. SSH 는 항상 활성화."
  default     = true
}

# --- Network volume (optional) / 네트워크 볼륨 (선택) ---------------------

variable "create_network_volume" {
  type        = bool
  description = <<-EOT
    Create and attach a Network Volume. Off by default — a volume keeps
    incurring storage charges even after the Pod is destroyed.

    Network Volume 을 생성해 연결할지 여부. 기본값은 false.
    볼륨은 Pod 를 삭제한 뒤에도 스토리지 비용이 계속 발생한다.
  EOT
  default     = false
}

variable "volume_name" {
  type        = string
  description = "Network volume name. / 네트워크 볼륨 이름."
  default     = "hol-shared-workspace"
}

variable "volume_size_gb" {
  type        = number
  description = "Network volume size in GB. / 네트워크 볼륨 크기(GB)."
  default     = 20
}

variable "data_center_id" {
  type        = string
  description = <<-EOT
    Data center for the network volume. A Pod can only mount a volume in the
    same data center, so this constrains where the Pod can land.
    List valid IDs with the data_centers data source.

    네트워크 볼륨을 생성할 데이터센터. Pod 는 같은 데이터센터의 볼륨만 마운트할 수 있으므로
    Pod 가 배치될 위치도 여기에 제약된다.
    유효한 ID 는 data_centers 데이터소스로 확인한다.
  EOT
  default     = "US-KS-2"
}
