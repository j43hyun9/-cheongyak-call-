"""
SQLite CRUD

담당:
  - init_db / call_log / schedules : 임강
  - conversation / ipo_cache CRUD  : 김준서
"""
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite

DB_PATH = "colby.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS call_log (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                called_at          TEXT NOT NULL,
                session_id         TEXT NOT NULL,
                engine             TEXT NOT NULL,
                cache_hit          INTEGER NOT NULL DEFAULT 0,
                input_tokens       INTEGER NOT NULL DEFAULT 0,
                output_tokens      INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL    NOT NULL DEFAULT 0.0,
                elapsed_ms         INTEGER NOT NULL DEFAULT 0,
                user_message       TEXT,
                reply              TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversation (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ipo_cache (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at TEXT NOT NULL,
                data_json  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                dt         TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


# ── schedules CRUD ────────────────────────────────────────────

async def create_schedule(title: str, dt: str) -> dict:
    now = datetime.utcnow().isoformat()
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO schedules (title, dt, created_at) VALUES (?, ?, ?)",
            (title, dt, now),
        )
        await db.commit()
        return {"id": cur.lastrowid, "title": title, "datetime": dt}


async def get_schedules(date: str | None = None) -> list[dict]:
    async with get_db() as db:
        if date:
            cur = await db.execute(
                "SELECT id, title, dt FROM schedules WHERE dt LIKE ? ORDER BY dt",
                (f"{date}%",),
            )
        else:
            cur = await db.execute(
                "SELECT id, title, dt FROM schedules ORDER BY dt"
            )
        rows = await cur.fetchall()
        return [{"id": r["id"], "title": r["title"], "datetime": r["dt"]} for r in rows]


async def update_schedule(id_: int, title: str | None, dt: str | None) -> dict | None:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id, title, dt FROM schedules WHERE id = ?", (id_,)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        new_title = title if title is not None else row["title"]
        new_dt = dt if dt is not None else row["dt"]
        await db.execute(
            "UPDATE schedules SET title = ?, dt = ? WHERE id = ?",
            (new_title, new_dt, id_),
        )
        await db.commit()
        return {"id": id_, "title": new_title, "datetime": new_dt}


async def delete_schedule(id_: int) -> bool:
    async with get_db() as db:
        cur = await db.execute("DELETE FROM schedules WHERE id = ?", (id_,))
        await db.commit()
        return (cur.rowcount or 0) > 0


# ── call log ──────────────────────────────────────────────────

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
    cost_usd: float,
) -> None:
    now = datetime.utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO call_log
                (called_at, session_id, engine, cache_hit, input_tokens, output_tokens,
                 estimated_cost_usd, elapsed_ms, user_message, reply)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, session_id, engine, int(cache_hit), input_tokens, output_tokens,
             cost_usd, elapsed_ms, user_message, reply),
        )
        await db.commit()


# ── conversation CRUD (김준서) ────────────────────────────────

async def save_message(session_id: str, role: str, content: str) -> int:
    """대화 한 턴 저장. 저장된 row id 반환."""
    now = datetime.utcnow().isoformat()
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO conversation (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        await db.commit()
        return cur.lastrowid


async def load_history(session_id: str) -> list[dict]:
    """세션의 전체 대화 이력 반환. [{role, content}, ...]"""
    async with get_db() as db:
        cur = await db.execute(
            "SELECT role, content FROM conversation WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        rows = await cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]


# ── ipo_cache (김준서) ────────────────────────────────────────

async def save_ipo_cache(data_json: str) -> None:
    """공모주 크롤링 결과를 DB에 저장 (최신 1건만 유지)."""
    now = datetime.utcnow().isoformat()
    async with get_db() as db:
        await db.execute("DELETE FROM ipo_cache")
        await db.execute(
            "INSERT INTO ipo_cache (fetched_at, data_json) VALUES (?, ?)",
            (now, data_json),
        )
        await db.commit()


async def load_ipo_cache() -> dict | None:
    """저장된 공모주 캐시 반환. 없으면 None."""
    async with get_db() as db:
        cur = await db.execute(
            "SELECT fetched_at, data_json FROM ipo_cache ORDER BY id DESC LIMIT 1"
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return {"fetched_at": row[0], "data_json": row[1]}


# ── call log ──────────────────────────────────────────────────

async def get_call_summary() -> dict:
    async with get_db() as db:
        cur = await db.execute("""
            SELECT
                COUNT(*)                AS total_calls,
                SUM(cache_hit)          AS cache_hits,
                SUM(input_tokens)       AS total_input_tokens,
                SUM(output_tokens)      AS total_output_tokens,
                SUM(estimated_cost_usd) AS total_cost_usd,
                AVG(elapsed_ms)         AS avg_latency_ms
            FROM call_log
        """)
        row = await cur.fetchone()
        return {
            "total_calls": row[0] or 0,
            "cache_hits": row[1] or 0,
            "total_input_tokens": row[2] or 0,
            "total_output_tokens": row[3] or 0,
            "total_cost_usd": round(row[4] or 0.0, 8),
            "avg_latency_ms": round(row[5] or 0.0, 1),
        }


async def usage_summary() -> dict:
    """제출물 '호출 로그 요약' 용 — 한국어 키 반환."""
    raw = await get_call_summary()
    total_tokens = raw["total_input_tokens"] + raw["total_output_tokens"]
    avg_cost = (
        raw["total_cost_usd"] / raw["total_calls"] if raw["total_calls"] else 0.0
    )
    return {
        "총 호출수":         raw["total_calls"],
        "총 토큰":           total_tokens,
        "총 비용(USD)":      round(raw["total_cost_usd"], 6),
        "1콜 평균비용(USD)": round(avg_cost, 6),
    }
