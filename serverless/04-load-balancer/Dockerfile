# No GPU work, so a slim base is enough (same choice as 01-hello-worker).
# GPU 연산이 없으므로 slim 이미지로 충분하다 (01-hello-worker 와 같은 선택).
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# The server and the health check share one port here; if you change PORT,
# change PORT_HEALTH too — the docs warn that one does not follow the other.
# 여기서는 서버와 헬스체크가 같은 포트를 쓴다. PORT 를 바꾸면 PORT_HEALTH 도 바꿀 것.
ENV PORT=80 PORT_HEALTH=80
EXPOSE 80
CMD ["python3", "app.py"]
