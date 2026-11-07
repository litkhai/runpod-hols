# CPU probe worker for labs 06-08; no GPU work, so a slim base.
# 실습 06-08 용 CPU 프로브 워커. GPU 연산이 없으므로 slim 이미지.
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY handler.py .
CMD ["python3", "-u", "handler.py"]
