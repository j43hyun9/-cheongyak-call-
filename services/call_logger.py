from datetime import datetime, timezone
from db.database import get_db
from core.config import settings


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens / 1000) * settings.cost_per_1k_input
    cost += (output_tokens / 1000) * settings.cost_per_1k_output
    return round(cost, 8)


async def log_call(
    *,
    session_id: str,
    user_message: str,
    reply: str,
    input_tokens: int,
    output_tokens: int,
    elapsed_ms: int,
    engine: str,
    cache_hit: bool,
) -> None:
    """매 LLM 호출마다 call_log 테이블에 기록합니다."""
    estimated_cost = _estimate_cost(input_tokens, output_tokens)
    called_at = datetime.now(timezone.utc).isoformat()

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO call_log
                (called_at, session_id, engine, cache_hit,
                 input_tokens, output_tokens, estimated_cost_usd, elapsed_ms,
                 user_message, reply)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                called_at, session_id, engine, int(cache_hit),
                input_tokens, output_tokens, estimated_cost, elapsed_ms,
                user_message[:500],   # DB 용량 절약
                reply[:1000],
            ),
        )
        await db.commit()


async def get_summary() -> dict:
    """호출 로그 집계 — 발표 보고서용."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                COUNT(*)                        AS total_calls,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
                SUM(input_tokens)               AS total_input_tokens,
                SUM(output_tokens)              AS total_output_tokens,
                SUM(estimated_cost_usd)         AS total_cost_usd,
                AVG(elapsed_ms)                 AS avg_elapsed_ms,
                MAX(elapsed_ms)                 AS max_elapsed_ms,
                MIN(called_at)                  AS first_call,
                MAX(called_at)                  AS last_call
            FROM call_log
            WHERE cache_hit = 0
            """
        )
        row = await cursor.fetchone()

    total_calls = row[0] or 0
    cache_hits = row[1] or 0
    total_input = row[2] or 0
    total_output = row[3] or 0
    total_cost = row[4] or 0.0
    avg_ms = row[5] or 0.0
    max_ms = row[6] or 0
    first_call = row[7]
    last_call = row[8]

    actual_calls = total_calls - cache_hits
    avg_cost_per_call = (total_cost / actual_calls) if actual_calls > 0 else 0.0

    return {
        "total_calls": total_calls,
        "cache_hits": cache_hits,
        "actual_llm_calls": actual_calls,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_per_call_usd": round(avg_cost_per_call, 6),
        "avg_elapsed_ms": round(avg_ms, 1),
        "max_elapsed_ms": max_ms,
        "first_call": first_call,
        "last_call": last_call,
    }
