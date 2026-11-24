terraform {
  # 1.5.x cannot install this provider — it fails with
  #   "error decoding signing key: openpgp: invalid data: armor invalid"
  # Verified working on 1.15.8 and 1.17.2. Homebrew's `terraform` formula is frozen at
  # 1.5.7, so install from the HashiCorp tap: brew install hashicorp/tap/terraform
  #
  # 1.5.x 에서는 이 프로바이더를 설치할 수 없다. 다음 오류가 발생한다:
  #   "error decoding signing key: openpgp: invalid data: armor invalid"
  # 1.15.8 과 1.17.2 에서 동작을 확인했다. Homebrew 의 `terraform` 포뮬러는 1.5.7 에 멈춰 있으므로
  # HashiCorp tap 에서 설치할 것: brew install hashicorp/tap/terraform
  required_version = ">= 1.6.0"

  required_providers {
    runpod = {
      source = "runpod/runpod"

      # 2.0.0 (2026-10-27) is a rebuild on REST v2; REST v1, which 1.0.8
      # used, was retired 2026-11-15. Pinned exactly so a later 2.x cannot
      # change the schema under the lab (#115).
      #
      # 2.0.0 (2026-10-27) 은 REST v2 기반으로 새로 만든 버전이다. 1.0.8 이 쓰던
      # REST v1 은 2026-11-15 에 폐기됐다. 이후 2.x 가 실습 중에 스키마를 바꾸지
      # 않도록 정확히 고정한다 (#115).
      version = "= 2.0.0"
    }
  }
}
