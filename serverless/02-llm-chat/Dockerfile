# Unlike Lab 01, this worker needs CUDA and torch, so a slim base will not do.
# Starting from an official PyTorch runtime image means torch is already
# present and CUDA-matched — pip-installing it instead would add gigabytes to
# the build and invite a version mismatch.
#
# Lab 01 과 달리 이 워커는 CUDA 와 torch 가 필요하므로 slim 베이스로는 안 된다.
# 공식 PyTorch runtime 이미지를 쓰면 torch 가 이미 들어 있고 CUDA 버전도 맞다.
# pip 로 따로 설치하면 이미지가 수 GB 커지고 버전 불일치 위험도 생긴다.
#
# Tag verified to exist on Docker Hub (~3.9GB compressed). Runpod rejects
# image references that do not resolve, so do not invent a tag here.
# Docker Hub 에 실재하는 태그로 확인했다 (압축 기준 약 3.9GB).
# Runpod 은 해석되지 않는 이미지 참조를 거부하므로 태그를 임의로 적지 말 것.
FROM pytorch/pytorch:2.9.1-cuda12.6-cudnn9-runtime

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
