terraform {
  # 1.5.x cannot install this provider — it fails with
  #   "error decoding signing key: openpgp: invalid data: armor invalid"
  # Verified working on 1.15.8. Homebrew's `terraform` formula is frozen at
  # 1.5.7, so install from the HashiCorp tap: brew install hashicorp/tap/terraform
  #
  # 1.5.x 에서는 이 프로바이더를 설치할 수 없다. 다음 오류가 발생한다:
  #   "error decoding signing key: openpgp: invalid data: armor invalid"
  # 1.15.8 에서 동작을 확인했다. Homebrew 의 `terraform` 포뮬러는 1.5.7 에 멈춰 있으므로
  # HashiCorp tap 에서 설치할 것: brew install hashicorp/tap/terraform
  required_version = ">= 1.6.0"

  required_providers {
    runpod = {
      source = "runpod/runpod"

      # Pinned exactly, NOT "~> 1.0.8".
      #
      # v1.0.9 is published but unusable: its endpoint_jobs / endpoint_workers
      # data sources declare an attribute with none of Required, Optional or
      # Computed set, so Terraform cannot load the provider schema at all.
      # Every command fails, including plan and validate:
      #   "Error converting data source schema ... must have Required,
      #    Optional, or Computed set"
      # A range like ~> 1.0.8 would silently resolve to 1.0.9 and break.
      #
      # "~> 1.0.8" 이 아니라 정확한 버전으로 고정했다.
      #
      # v1.0.9 는 배포돼 있지만 사용할 수 없다. endpoint_jobs / endpoint_workers
      # 데이터소스의 속성에 Required·Optional·Computed 가 모두 설정돼 있지 않아
      # Terraform 이 프로바이더 스키마 자체를 로드하지 못한다.
      # plan 과 validate 를 포함한 모든 명령이 실패한다.
      # ~> 1.0.8 같은 범위 지정은 조용히 1.0.9 로 해석되어 깨진다.
      version = "= 1.0.8"
    }
  }
}
