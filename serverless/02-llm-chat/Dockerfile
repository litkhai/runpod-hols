# Unlike Lab 01, this worker needs CUDA and torch, so a slim base will not do.
# Starting from an official PyTorch runtime image means torch is already
# present and CUDA-matched — pip-installing it instead would add gigabytes to
# the build and invite a version mismatch.
#
# Lab 01 과 달리 이 워커는 CUDA 와 torch 가 필요하므로 slim 베이스로는 안 된다.
# 공식 PyTorch runtime 이미지를 쓰면 torch 가 이미 들어 있고 CUDA 버전도 맞다.
# pip 로 따로 설치하면 이미지가 수 GB 커지고 버전 불일치 위험도 생긴다.
#
# CUDA 12.8, not 12.6: the cu126 build of torch 2.9.1 supports sm_50–sm_90
# only. Runpod's 16/24 GB pools include RTX PRO 6000 Blackwell MIG slices
# (sm_120), where the cu126 image failed the SDK's CUDA fitness check with
# "no kernel image is available for execution on the device" (#10, 2026-10-11).
# Set the endpoint's minimum CUDA version to 12.8 so hosts can run it.
# Tag verified to exist on Docker Hub (4.45GB). Runpod rejects image
# references that do not resolve, so do not invent a tag here.
#
# CUDA 12.6 이 아니라 12.8 이다. torch 2.9.1 의 cu126 빌드는 sm_50–sm_90 만
# 지원한다. Runpod 의 16/24 GB 풀에는 RTX PRO 6000 Blackwell MIG 조각(sm_120)이
# 섞여 있고, cu126 이미지는 그곳에서 SDK 의 CUDA 점검을 "no kernel image is
# available for execution on the device" 로 통과하지 못했다 (#10, 2026-10-11).
# 엔드포인트의 최소 CUDA 버전을 12.8 로 지정해야 호스트가 실행할 수 있다.
# Docker Hub 에 실재하는 태그로 확인했다 (4.45GB). Runpod 은 해석되지 않는
# 이미지 참조를 거부하므로 태그를 임의로 적지 말 것.
FROM pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime

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
