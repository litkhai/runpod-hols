output "endpoint_id" {
  description = "Endpoint ID — put this in .env as RUNPOD_ENDPOINT_ID. / .env 의 RUNPOD_ENDPOINT_ID 에 넣을 값."
  value       = runpod_endpoint.hello.id
}

output "template_id" {
  description = "Template backing the endpoint. / 엔드포인트가 사용하는 템플릿."
  value       = runpod_template.hello.id
}

output "runsync_url" {
  description = "Synchronous call URL. / 동기 호출 URL."
  value       = "https://api.runpod.ai/v2/${runpod_endpoint.hello.id}/runsync"
}

output "test_command" {
  description = "Ready-to-paste curl. Requires RUNPOD_API_KEY in your shell. / 바로 붙여넣을 수 있는 curl. 셸에 RUNPOD_API_KEY 필요."
  value       = <<-EOT
    curl -X POST "https://api.runpod.ai/v2/${runpod_endpoint.hello.id}/runsync" \
      -H "Authorization: Bearer $RUNPOD_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"input": {"name": "Terraform"}}'
  EOT
}

output "endpoint_summary" {
  description = "What was actually created. / 실제로 생성된 구성."
  value = {
    endpoint_name = runpod_endpoint.hello.name
    template_name = runpod_template.hello.name
    image_name    = runpod_template.hello.image_name
    gpu_type_ids  = runpod_endpoint.hello.gpu_type_ids
    workers_min   = runpod_endpoint.hello.workers_min
    workers_max   = runpod_endpoint.hello.workers_max
  }
}
