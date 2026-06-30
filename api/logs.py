from fastapi import APIRouter
from services.call_logger import get_summary
from services.cache import stats as cache_stats

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/summary")
async def summary():
    """
    호출 로그 집계 — 발표 보고서 '응답 엔진 호출 로그 요약' 항목용.

    반환:
      - total_calls, cache_hits, actual_llm_calls
      - total_input/output_tokens
      - total_cost_usd, avg_cost_per_call_usd
      - avg/max elapsed_ms
      - first_call, last_call 타임스탬프
      - cache 현황
    """
    log_data = await get_summary()
    log_data["cache"] = cache_stats()
    return log_data
