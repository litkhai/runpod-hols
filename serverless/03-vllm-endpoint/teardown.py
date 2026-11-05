#!/usr/bin/env python3
"""Delete the endpoint and template deploy.py created.

deploy.py 가 만든 엔드포인트와 템플릿을 삭제한다.

    python teardown.py

The endpoint goes at once. The template can stay locked for a while: on
2026-11-05 the API refused with "Template is still held by deleted endpoint …
It can be deleted once that endpoint's last worker has been billed, within
about 90 minutes of the endpoint delete." An unused template costs nothing;
rerun this script later to remove it.
엔드포인트는 바로 지워진다. 템플릿은 한동안 잠길 수 있다. 2026-11-05 에 API 가
"삭제된 엔드포인트가 아직 잡고 있으며, 마지막 워커 과금이 끝나면 (삭제 후 약
90분 이내) 지울 수 있다" 며 거부했다. 쓰지 않는 템플릿은 비용이 없으니 나중에
이 스크립트를 다시 실행하면 된다.
"""

import sys

from common import STATE_FILE, RestError, load_state, rest, save_state


def main() -> int:
    state = load_state()
    if not state:
        print("Nothing recorded in .endpoint.json. / .endpoint.json 에 기록된 것이 없습니다.")
        return 0
    if state.get("endpoint_id"):
        rest("DELETE", f"/endpoints/{state['endpoint_id']}")
        print(f"deleted endpoint  {state['endpoint_id']}")
        state.pop("endpoint_id")
        save_state(state)
    if state.get("template_id"):
        try:
            rest("DELETE", f"/templates/{state['template_id']}")
        except RestError as e:
            if "still held by deleted endpoint" not in e.text:
                raise
            print(f"template {state['template_id']} is still held by the deleted endpoint.")
            print("No cost. Rerun teardown.py later — it took 92 to 116 minutes on 2026-11-05.")
            print("삭제된 엔드포인트가 템플릿을 아직 잡고 있습니다. 비용은 없습니다. 나중에 다시 실행하세요 (2026-11-05 에는 92–116분).")
            return 0
        print(f"deleted template  {state['template_id']}")
    STATE_FILE.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
