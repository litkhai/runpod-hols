# Provision a GPU Pod, optionally backed by a Network Volume.
# GPU Pod 를 프로비저닝한다. 선택적으로 Network Volume 을 붙인다.
#
# ⚠️ UNLIKE THE ENDPOINT LAB, THIS BILLS IMMEDIATELY.
#    A Pod is charged per minute from the moment it starts, idle or not.
#    Run `terraform destroy` the moment you are done.
#
# ⚠️ 엔드포인트 실습과 달리 이 구성은 즉시 과금된다.
#    Pod 는 기동 시점부터 유휴 여부와 무관하게 분 단위로 과금된다.
#    끝나는 즉시 `terraform destroy` 를 실행할 것.

provider "runpod" {}

# A Network Volume outlives any single Pod, so weights and datasets downloaded
# once can be reused. Created only when var.create_network_volume is true —
# the volume keeps costing storage even with no Pod attached.
#
# Network Volume 은 개별 Pod 보다 오래 살아남으므로, 한 번 받아둔 가중치와 데이터셋을
# 재사용할 수 있다. 볼륨은 Pod 가 붙어있지 않아도 스토리지 비용이 계속 발생하므로
# var.create_network_volume 이 true 일 때만 생성한다.
resource "runpod_network_volume" "workspace" {
  count = var.create_network_volume ? 1 : 0

  name        = var.volume_name
  size        = var.volume_size_gb
  data_center = var.data_center_id
}

resource "runpod_pod" "lab" {
  name        = var.pod_name
  image       = var.image_name
  cloud       = "SECURE"
  gpu_type_id = var.gpu_type_id
  gpu_count   = var.gpu_count

  # Container disk is scratch space — destroyed with the Pod.
  # 컨테이너 디스크는 임시 공간이다. Pod 와 함께 소멸한다.
  disk = var.container_disk_in_gb

  # Create-time flags. REST v2 sets up SSH only when asked.
  # 생성 시에만 쓰이는 값. REST v2 는 요청할 때만 SSH 를 설정한다.
  start_ssh     = true
  start_jupyter = var.start_jupyter
  ports         = ["8888/http", "22/tcp"]

  # A Pod has a Pod volume OR network volumes at /workspace, not both
  # (REST v2 rejects the pair with a 400).
  #   Pod volume: survives a stop, dies on terminate.
  #   Network volume: outlives the Pod; it pins the Pod to its data center.
  #
  # Pod 은 /workspace 에 Pod 볼륨 또는 네트워크 볼륨을 가진다. 둘 다는 아니다
  # (REST v2 는 둘을 함께 주면 400).
  #   Pod 볼륨: 중지해도 유지, 삭제하면 소멸.
  #   네트워크 볼륨: Pod 보다 오래 남고, Pod 을 그 데이터센터에 묶는다.
  persistent_volume = var.create_network_volume ? null : {
    size = var.volume_in_gb
    path = "/workspace"
  }

  network_volumes = var.create_network_volume ? [{
    volume_id = runpod_network_volume.workspace[0].id
    path      = "/workspace"
  }] : null

  data_center_ids = var.create_network_volume ? [var.data_center_id] : null
}
