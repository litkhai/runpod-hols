"""Runpod Serverless hello-world handler. / Runpod Serverless hello-world 핸들러.

Local testing / 로컬 테스트:
    python handler.py                 # run test_input.json once and exit
                                      # test_input.json 을 한 번 실행하고 종료
    python handler.py --rp_serve_api  # serve a local API at http://localhost:8000
                                      # http://localhost:8000 에 로컬 API 서버 기동
"""

import os

import runpod

# If this worker uses a model, load it here at module scope.
# Module scope runs once per worker (cold start); the handler runs once per request.
# Loading inside the handler would re-read the model on every single request.
#
# 모델을 사용하는 워커라면 여기(모듈 스코프)에서 로드한다.
# 모듈 스코프는 워커당 1회(콜드 스타트), handler 는 요청당 1회 실행된다.
# handler 안에서 로드하면 요청이 올 때마다 모델을 다시 읽게 된다.


def handler(job):
    """Process one job. The caller's payload arrives in job["input"].

    작업 1건을 처리한다. 호출자가 보낸 payload 는 job["input"] 에 들어온다.
    """
    job_input = job["input"]

    name = job_input.get("name", "World")

    return {
        "greeting": f"Hello, {name}!",
        # Which worker handled this — useful for observing cold starts and scale-out.
        # Not set when running locally, so it prints "local".
        #
        # 어떤 워커가 처리했는지 확인용. 콜드 스타트와 스케일아웃 관찰에 유용하다.
        # 로컬 실행 시에는 이 환경변수가 없으므로 "local" 이 찍힌다.
        "worker_id": os.environ.get("RUNPOD_POD_ID", "local"),
    }


runpod.serverless.start({"handler": handler})
