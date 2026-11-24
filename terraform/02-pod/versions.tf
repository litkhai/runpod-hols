terraform {
  # 1.5.x cannot install this provider (openpgp armor error). Verified on 1.15.8 and 1.17.2.
  # Homebrew's `terraform` is frozen at 1.5.7 — use brew install hashicorp/tap/terraform
  #
  # 1.5.x 에서는 이 프로바이더 설치가 실패한다(openpgp armor 오류). 1.15.8 과 1.17.2 에서 확인.
  # Homebrew 의 `terraform` 은 1.5.7 에 멈춰 있으므로 brew install hashicorp/tap/terraform 사용.
  required_version = ">= 1.6.0"

  required_providers {
    runpod = {
      source = "runpod/runpod"

      # 2.0.0 is the REST v2 rebuild (REST v1, used by 1.0.8, was retired
      # 2026-11-15). Exact pin; see terraform/README.md (#115).
      #
      # 2.0.0 은 REST v2 기반 재작성판이다 (1.0.8 이 쓰던 REST v1 은 2026-11-15 폐기).
      # 정확한 버전 고정. 자세한 내용은 terraform/README.md 참조 (#115).
      version = "= 2.0.0"
    }
  }
}
