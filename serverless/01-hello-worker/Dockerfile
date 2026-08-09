# A hello-world worker does no GPU work, so a slim base is enough.
# Builds to ~106MB in a few seconds, which also keeps emulated arm64 -> amd64 builds fast.
#
# 이 hello-world 워커는 GPU 연산이 없으므로 가벼운 slim 이미지로 충분하다.
# 약 106MB, 수 초 만에 빌드되며 arm64 -> amd64 에뮬레이션 빌드도 빠르다.
#
# When you add a real model, switch to the CUDA base used by the official template:
# 실제 모델을 올릴 때는 공식 템플릿과 동일한 CUDA 베이스로 교체한다:
#   FROM runpod/base:0.6.3-cuda11.8.0
# That image ships CUDA, several Python versions, uv and Jupyter, but is multiple GB.
# 해당 이미지는 CUDA / 여러 Python 버전 / uv / Jupyter 를 포함하지만 수 GB 다.
FROM python:3.11-slim

# The COPY paths below are relative to THIS directory, which keeps the lab
# self-contained and portable. Runpod defaults its build context to the repo
# root, so set the endpoint's **Build context** field to
#   /serverless/01-hello-worker
# Without it the build fails with: "/handler.py": not found
#
# 아래 COPY 경로는 이 디렉토리 기준이다. 그래야 실습이 자체 완결적이고
# 다른 곳으로 옮겨도 동작한다. Runpod 은 빌드 컨텍스트 기본값이 저장소 루트이므로
# 엔드포인트의 **Build context** 필드에 위 경로를 지정해야 한다.
# 지정하지 않으면 "/handler.py": not found 로 빌드가 실패한다.

WORKDIR /app

# Copy dependencies first so the pip layer is cached.
# Editing handler.py then does not reinstall packages.
#
# 의존성을 먼저 복사해 pip 레이어 캐시를 살린다.
# handler.py 만 고치면 패키지를 다시 설치하지 않는다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

# -u disables stdout buffering. Without it, Runpod console logs arrive late and in bursts.
# -u 는 stdout 버퍼링을 끈다. 없으면 Runpod 콘솔 로그가 늦게 몰려서 출력된다.
CMD ["python", "-u", "handler.py"]
