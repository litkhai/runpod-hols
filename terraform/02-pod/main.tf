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

  name           = var.volume_name
  size           = var.volume_size_gb
  data_center_id = var.data_center_id
}

resource "runpod_pod" "lab" {
  name        = var.pod_name
  image_name  = var.image_name
  gpu_type_id = var.gpu_type_id
  gpu_count   = var.gpu_count

  # Container disk is scratch space — destroyed with the Pod.
  # 컨테이너 디스크는 임시 공간이다. Pod 와 함께 소멸한다.
  container_disk_in_gb = var.container_disk_in_gb

  # Volume disk mounted at /workspace. Survives a stop, dies on terminate.
  # Anything you want to keep goes here, not on the container disk.
  #
  # /workspace 에 마운트되는 볼륨 디스크. 중지해도 유지되고 삭제 시 소멸한다.
  # 보존할 것은 컨테이너 디스크가 아니라 여기에 둔다.
  volume_in_gb      = var.volume_in_gb
  volume_mount_path = "/workspace"

  start_ssh     = true
  start_jupyter = var.start_jupyter

  # Attach the network volume only when one was created.
  # 네트워크 볼륨을 생성한 경우에만 연결한다.
  network_volume_id = var.create_network_volume ? runpod_network_volume.workspace[0].id : null
}
