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
  default     = "runpod/pytorch:2.2.0-cu1281-torch291-ubuntu2404"
}

variable "gpu_type_id" {
  type        = string
  description = <<-EOT
    GPU type for the Pod. Check availability and pricing before applying —
    this one bills per minute. Changing it replaces the Pod.
    Stock: data "runpod_gpu_types" or GET /v2/catalog/gpus?include=AVAILABILITY&product=POD.

    Pod 에 할당할 GPU 타입. 분 단위로 과금되므로 apply 전에 가용성과 단가를 확인할 것.
    바꾸면 Pod 이 교체된다.
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
  description = "Pod volume at /workspace, used when no network volume is attached. / 네트워크 볼륨을 붙이지 않을 때 /workspace 에 쓰는 Pod 볼륨 크기."
  default     = 20
}

variable "start_jupyter" {
  type        = bool
  description = "Start JupyterLab on boot (create-time). SSH is always requested. / 부팅 시 JupyterLab 시작 (생성 시에만). SSH 는 항상 요청."
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
    Data center for the network volume. Per the docs, location does not affect
    price, but it "will determine which GPU types your network volume can be
    used with" — so picking a small data center can quietly limit your GPU
    choices later.

    EU-RO-1 is the default because a Pod with a network volume there was
    created, mounted at /workspace and destroyed on 2026-10-16. Check before
    applying: GET /v2/catalog/datacenters lists each data center's
    networkVolumeTypes.

    List the current set with the data_centers data source:
      data "runpod_data_centers" "all" {}
      output "dcs" { value = data.runpod_data_centers.all }

    네트워크 볼륨을 생성할 데이터센터. 문서에 따르면 위치가 가격에 영향을 주지는 않지만,
    "볼륨을 어떤 GPU 타입과 함께 쓸 수 있는지를 결정"한다. 작은 데이터센터를 고르면
    나중에 GPU 선택지가 조용히 좁아질 수 있다.

    EU-RO-1 을 기본값으로 둔 이유는, 2026-10-16 이곳에서 네트워크 볼륨을 붙인 Pod 을
    생성해 /workspace 에 마운트하고 삭제까지 확인했기 때문이다. apply 전에
    GET /v2/catalog/datacenters 의 networkVolumeTypes 로 확인할 것.

    현재 목록은 data_centers 데이터소스로 확인한다.
  EOT
  default     = "EU-RO-1"
}
