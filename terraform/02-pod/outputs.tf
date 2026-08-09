output "pod_id" {
  description = "Pod ID. / Pod ID."
  value       = runpod_pod.lab.id
}

output "pod_status" {
  description = "Current status. / 현재 상태."
  value       = runpod_pod.lab.status
}

output "cost_per_hr" {
  description = "What this Pod costs every hour it stays up. / 이 Pod 가 켜져 있는 동안 시간당 발생하는 비용."
  value       = runpod_pod.lab.cost_per_hr
}

output "network_volume_id" {
  description = "Attached network volume, if any. / 연결된 네트워크 볼륨 (있는 경우)."
  value       = var.create_network_volume ? runpod_network_volume.workspace[0].id : null
}

output "connect_hint" {
  description = "How to reach the Pod. / Pod 접속 방법."
  value       = <<-EOT
    Open the Pod in the console for its SSH command and Jupyter link:
    콘솔에서 Pod 를 열면 SSH 명령과 Jupyter 링크를 확인할 수 있다:
      https://console.runpod.io/pods

    Or / 또는: runpodctl get pod ${runpod_pod.lab.id}
  EOT
}

output "cost_reminder" {
  description = "Read this. / 반드시 읽을 것."
  value       = "This Pod is billing per minute right now. Run `terraform destroy` when done. / 이 Pod 는 지금 분 단위로 과금되고 있습니다. 끝나면 `terraform destroy` 를 실행하세요."
}
