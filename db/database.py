"""
SQLite 초기화 + 연결 헬퍼

담당:
  - 테이블 정의·init_db() : 임강
  - conversation 테이블 CRUD : 김준서 (대화 이력 저장)
  - ipo_cache 테이블 CRUD   : 김준서 (크롤러 연계)
"""

from contextlib import asynccontextmanager
import aiosqlite

DB_PATH = "colby.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        # ── 호출 로그 (임강 담당) ───────────────────────────
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS call_log (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                called_at          TEXT    NOT NULL,
                session_id         TEXT    NOT NULL,
                engine             TEXT    NOT NULL,
                cache_hit          INTEGER NOT NULL DEFAULT 0,
                input_tokens       INTEGER NOT NULL DEFAULT 0,
                output_tokens      INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL    NOT NULL DEFAULT 0.0,
                elapsed_ms         INTEGER NOT NULL DEFAULT 0,
                user_message       TEXT,
                reply              TEXT
            )
            """
        )

        # ── 대화 이력 (김준서 담당) ─────────────────────────
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # ── 공모주 캐시 (김준서 담당) ────────────────────────
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ipo_cache (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at TEXT    NOT NULL,
                data_json  TEXT    NOT NULL
            )
            """
        )

        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
