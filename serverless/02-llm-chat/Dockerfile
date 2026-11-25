# Unlike Lab 01, this worker needs CUDA and torch, so a slim base will not do.
# Starting from an official PyTorch runtime image means torch is already
# present and CUDA-matched — pip-installing it instead would add gigabytes to
# the build and invite a version mismatch.
#
# Lab 01 과 달리 이 워커는 CUDA 와 torch 가 필요하므로 slim 베이스로는 안 된다.
# 공식 PyTorch runtime 이미지를 쓰면 torch 가 이미 들어 있고 CUDA 버전도 맞다.
# pip 로 따로 설치하면 이미지가 수 GB 커지고 버전 불일치 위험도 생긴다.
#
# PyTorch 2.15 on CUDA 13.2 (2026-11-26, #143). torch 2.9.1 on CUDA 12.8 before.
# History: CUDA 12.6 failed on the RTX PRO 6000 Blackwell MIG slices (sm_120) in
# the 16/24 GB pools with "no kernel image is available for execution on the
# device" (#10, 2026-10-11). On 2026-11-26 every GPU with Serverless capacity in
# those pools reported CUDA 13.2 only, and this image ran on an RTX A4500.
# Set the endpoint's CUDA version to 13.2 or newer so hosts can run it.
# Tag verified to exist on Docker Hub. Runpod rejects image
# references that do not resolve, so do not invent a tag here.
#
# CUDA 13.2 의 PyTorch 2.15 (2026-11-26, #143). 그전에는 CUDA 12.8 의 torch 2.9.1.
# 경위: CUDA 12.6 은 16/24 GB 풀의 RTX PRO 6000 Blackwell MIG 조각(sm_120)에서
# "no kernel image is available for execution on the device" 로 실패했다
# (#10, 2026-10-11). 2026-11-26 에는 이 풀들에서 Serverless 여유가 있는 GPU 가
# 모두 CUDA 13.2 만 보고했고, 이 이미지는 RTX A4500 에서 돌았다.
# 엔드포인트의 CUDA 버전을 13.2 이상으로 지정해야 호스트가 실행할 수 있다.
# Docker Hub 에 실재하는 태그로 확인했다. Runpod 은 해석되지 않는
# 이미지 참조를 거부하므로 태그를 임의로 적지 말 것.
FROM pytorch/pytorch:2.15.0-cuda13.2-cudnn9-runtime

# COPY paths are relative to THIS directory, keeping the lab self-contained.
# Runpod defaults its build context to the repo root, so set the endpoint's
# **Build context** field to
#   /serverless/02-llm-chat
# Without it the build fails with: "/handler.py": not found
#
# COPY 경로는 이 디렉토리 기준이며, 그래야 실습이 자체 완결적이다.
# Runpod 은 빌드 컨텍스트 기본값이 저장소 루트이므로 엔드포인트의
# **Build context** 필드에 위 경로를 지정해야 한다.
# 지정하지 않으면 "/handler.py": not found 로 빌드가 실패한다.

WORKDIR /app

# Dependencies first so the pip layer survives handler edits.
# 의존성을 먼저 복사해 handler 수정 시에도 pip 레이어가 재사용되게 한다.
COPY requirements.txt .
# PyTorch 2.15 images use the system Python, marked externally managed (PEP 668).
# PyTorch 2.15 이미지는 시스템 Python 을 쓰며, 외부 관리 환경(PEP 668)으로 표시돼 있다.
ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN pip install --no-cache-dir -r requirements.txt

# No model weights are copied in. With Runpod's cached models the weights live
# on the host at /runpod-volume/huggingface-cache, which keeps this image small
# and means model download time is not billed.
#
# 모델 가중치는 이미지에 넣지 않는다. Runpod 의 모델 캐싱을 쓰면 가중치가
# 호스트의 /runpod-volume/huggingface-cache 에 있으므로 이미지가 작게 유지되고
# 모델 다운로드 시간도 과금되지 않는다.
COPY model_cache.py handler.py ./

# -u disables stdout buffering so the console shows logs as they happen.
# -u 는 stdout 버퍼링을 꺼서 콘솔에 로그가 제때 보이게 한다.
CMD ["python", "-u", "handler.py"]
