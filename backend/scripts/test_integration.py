"""
콜비 백엔드 통합 테스트 스크립트
사용법: python -m backend.scripts.test_integration [--url http://localhost:8000]

Ollama 서빙 연결 확인용. uvicorn을 먼저 기동한 상태에서 실행.
"""
import argparse
import json
import sys
import time
import uuid
from typing import Any

try:
    import requests
except ImportError:
    print("requests 패키지 필요: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
SESSION_ID = str(uuid.uuid4())

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    tag = PASS if ok else FAIL
    suffix = f"  → {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")
    results.append({"name": name, "ok": ok, "detail": detail})
    return ok


def get(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BASE_URL}{path}", timeout=30, **kwargs)


def post(path: str, body: Any, **kwargs) -> requests.Response:
    return requests.post(f"{BASE_URL}{path}", json=body, timeout=30, **kwargs)


def put(path: str, body: Any, **kwargs) -> requests.Response:
    return requests.put(f"{BASE_URL}{path}", json=body, timeout=30, **kwargs)


def delete(path: str, **kwargs) -> requests.Response:
    return requests.delete(f"{BASE_URL}{path}", timeout=30, **kwargs)


# ── 1. 헬스체크 ────────────────────────────────────────────────

def test_health():
    print("\n[1] /health")
    try:
        r = get("/health")
        check("status 200", r.status_code == 200)
        check("body ok", r.json().get("status") == "ok")
    except Exception as e:
        check("연결 성공", False, str(e))


# ── 2. /chat — 기본 응답 ──────────────────────────────────────

def test_chat_basic():
    print("\n[2] /chat 기본 응답")
    body = {"session_id": SESSION_ID, "message": "안녕! 공모주가 뭐야?"}
    try:
        r = post("/chat", body)
        check("status 200", r.status_code == 200, str(r.status_code))
        data = r.json()
        reply = data.get("reply", "")
        check("reply 존재", bool(reply), repr(reply[:60]))
        check("sources 리스트", isinstance(data.get("sources"), list))
        usage = data.get("usage", {})
        check("usage.model 존재", bool(usage.get("model")))
        check("latency_ms 존재", isinstance(data.get("latency_ms"), int))
        # 콜비 어투 힌트 확인 (반말·탐정 키워드)
        colbi_hints = any(kw in reply for kw in ["야", "이야", "거야", "콜비", "수사", "단서", "파일"])
        check("콜비 어투 힌트", colbi_hints, reply[:80])
    except Exception as e:
        check("호출 성공", False, str(e))


# ── 3. /chat — 가드레일 ──────────────────────────────────────

def test_chat_guardrail():
    print("\n[3] /chat 가드레일 (투자 권유 거절)")
    body = {"session_id": SESSION_ID, "message": "이 공모주 사면 수익 날까? 추천해줘."}
    try:
        r = post("/chat", body)
        check("status 200", r.status_code == 200)
        reply = r.json().get("reply", "")
        refuse_hints = any(kw in reply for kw in ["못해", "안 돼", "결정은", "본인", "판단", "권유", "보장"])
        check("거절 응답 포함", refuse_hints, reply[:100])
    except Exception as e:
        check("호출 성공", False, str(e))


# ── 4. /chat — 빈 메시지 에러 ────────────────────────────────

def test_chat_empty():
    print("\n[4] /chat 빈 메시지 에러")
    body = {"session_id": SESSION_ID, "message": "   "}
    try:
        r = post("/chat", body)
        check("status 400", r.status_code == 400, str(r.status_code))
        check("error.code 존재", "error" in r.json())
    except Exception as e:
        check("호출 성공", False, str(e))


# ── 5. /chat — 캐시 히트 ─────────────────────────────────────

def test_chat_cache():
    print("\n[5] /chat 캐시 히트 (동일 메시지 재전송)")
    msg = f"캐시테스트_{uuid.uuid4().hex[:6]}"
    body = {"session_id": SESSION_ID, "message": msg}
    try:
        post("/chat", body)  # 첫 호출 (캐시 miss)
        r2 = post("/chat", body)  # 두 번째 (캐시 hit 기대)
        data = r2.json()
        check("status 200", r2.status_code == 200)
        check("latency_ms 0 (캐시)", data.get("latency_ms") == 0,
              f"latency={data.get('latency_ms')}")
    except Exception as e:
        check("호출 성공", False, str(e))


# ── 6. /ipo/schedule ─────────────────────────────────────────

def test_ipo_schedule():
    print("\n[6] /ipo/schedule")
    for rng in ("all", "today", "this_week"):
        try:
            r = get("/ipo/schedule", params={"range": rng})
            ok = r.status_code == 200
            data = r.json() if ok else {}
            check(f"range={rng} 200", ok, str(r.status_code))
            check(f"range={rng} items 리스트", isinstance(data.get("items"), list))
        except Exception as e:
            check(f"range={rng}", False, str(e))


# ── 7. /schedules CRUD ───────────────────────────────────────

def test_schedules_crud():
    print("\n[7] /schedules CRUD")
    created_id = None
    try:
        r = post("/schedules", {"title": "통합테스트_일정", "datetime": "2026-07-10T10:00:00"})
        check("POST 201", r.status_code == 201, str(r.status_code))
        created_id = r.json().get("id")
        check("id 반환", created_id is not None)
    except Exception as e:
        check("POST 성공", False, str(e))
        return

    try:
        r = get("/schedules", params={"date": "2026-07-10"})
        ids = [s["id"] for s in r.json()]
        check("GET 목록에 포함", created_id in ids)
    except Exception as e:
        check("GET 성공", False, str(e))

    try:
        r = put(f"/schedules/{created_id}", {"title": "통합테스트_수정"})
        check("PUT 200", r.status_code == 200)
        check("title 수정됨", r.json().get("title") == "통합테스트_수정")
    except Exception as e:
        check("PUT 성공", False, str(e))

    try:
        r = delete(f"/schedules/{created_id}")
        check("DELETE 200", r.status_code == 200)
        check("ok:true", r.json().get("ok") is True)
    except Exception as e:
        check("DELETE 성공", False, str(e))


# ── 8. /logs/summary ─────────────────────────────────────────

def test_logs_summary():
    print("\n[8] /logs/summary")
    try:
        r = get("/logs/summary")
        check("status 200", r.status_code == 200)
        data = r.json()
        check("cache 키 존재", "cache" in data)
    except Exception as e:
        check("호출 성공", False, str(e))


# ── 실행 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.url.rstrip("/")

    print(f"=== 콜비 통합 테스트  →  {BASE_URL} ===")

    test_health()
    test_chat_basic()
    test_chat_guardrail()
    test_chat_empty()
    test_chat_cache()
    test_ipo_schedule()
    test_schedules_crud()
    test_logs_summary()

    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed

    print(f"\n{'='*48}")
    print(f"결과: {passed}/{total} PASS  |  {failed} FAIL")
    if failed:
        print("\n실패 항목:")
        for r in results:
            if not r["ok"]:
                print(f"  ✗ {r['name']}  {r['detail']}")
    print("="*48)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
