#!/usr/bin/env python3
"""Talk to the vLLM endpoint through the OpenAI SDK — only base_url and api_key change.

OpenAI SDK 로 vLLM 엔드포인트와 대화한다. 바뀌는 것은 base_url 과 api_key 뿐이다.

    python chat.py                       # models, one completion, one streamed completion
    python chat.py "your prompt"

The first request after a quiet period waits for a cold start (minutes, not
seconds), so the client timeout is generous.
한동안 요청이 없었다면 첫 요청은 콜드 스타트를 기다린다 (초가 아니라 분 단위).
그래서 클라이언트 타임아웃을 넉넉하게 둔다.
"""

import sys
import time

from common import api_key, load_state


def main() -> int:
    state = load_state()
    if not state.get("endpoint_id"):
        print("No endpoint recorded. Run deploy.py first. / 기록된 엔드포인트가 없습니다. deploy.py 먼저.")
        return 1
    try:
        from openai import InternalServerError, OpenAI
    except ImportError:
        sys.exit("pip install -r requirements.txt  (openai)")

    client = OpenAI(
        base_url=f"https://api.runpod.ai/v2/{state['endpoint_id']}/openai/v1",
        api_key=api_key(),
        timeout=900,
        max_retries=0,
    )
    prompt = " ".join(sys.argv[1:]) or "In one sentence, what is a serverless GPU?"

    # On 2026-11-05 the first request of a cold endpoint came back as HTTP 520
    # after 7 min 12 s while the worker was still starting; the job stayed queued
    # and a retry was answered once the container was up. Retry server errors.
    # 2026-11-05, 콜드 엔드포인트의 첫 요청이 워커 기동 중 7분 12초 만에 HTTP 520
    # 으로 돌아왔다. 작업은 큐에 남았고, 재시도는 컨테이너가 뜬 뒤 응답됐다.
    t = time.time()
    for attempt in range(1, 4):
        try:
            models = [m.id for m in client.models.list().data]
            break
        except InternalServerError as e:
            print(f"models  attempt {attempt}: HTTP {e.status_code} after {time.time() - t:.0f}s — retrying")
    else:
        print("No answer after three attempts. / 세 번 시도했지만 응답이 없습니다.")
        return 1
    print(f"models  {models}  ({time.time() - t:.1f}s — includes any cold start / 콜드 스타트 포함)")

    t = time.time()
    r = client.chat.completions.create(
        model=state["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=128,
        temperature=0,
    )
    print(f"\nchat    ({time.time() - t:.1f}s, {r.usage.prompt_tokens}+{r.usage.completion_tokens} tokens)")
    print("        " + r.choices[0].message.content.strip())

    t = time.time()
    first = None
    print("\nstream  ", end="", flush=True)
    for chunk in client.chat.completions.create(
        model=state["model"],
        messages=[{"role": "user", "content": "Count from 1 to 10, separated by spaces."}],
        max_tokens=64,
        temperature=0,
        stream=True,
    ):
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            first = first or time.time() - t
            print(delta, end="", flush=True)
    print(f"\n        first token {first:.2f}s, total {time.time() - t:.2f}s" if first else "\n        (no content)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
