"""
IPO 크롤러 — 38커뮤니케이션 기반 (1차 프로젝트 crawl_ipo.py 재활용)
동기 크롤링을 asyncio.to_thread 로 래핑해 FastAPI에서 사용.
"""
import asyncio
import re
import ssl
import time
from datetime import datetime, timedelta

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 모듈 레벨 인메모리 캐시 (15분 TTL)
_cache: tuple[list[dict], float] | None = None
_CACHE_TTL = 15 * 60


class _LegacySSLAdapter(HTTPAdapter):
    """38커뮤니케이션 구형 SSL 우회 어댑터"""
    def init_poolmanager(self, connections, maxsize, block=False, **kw):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx, **kw
        )


def _fetch_sync() -> list[dict]:
    global _cache
    now = time.time()
    if _cache and (now - _cache[1]) < _CACHE_TTL:
        return _cache[0]

    url = "http://www.38.co.kr/html/fund/?o=k"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    session = requests.Session()
    session.mount("http://", _LegacySSLAdapter())
    session.mount("https://", _LegacySSLAdapter())

    items: list[dict] = []
    try:
        resp = session.get(url, headers=headers, verify=False, timeout=10)
        resp.encoding = "euc-kr"
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")

        soup = BeautifulSoup(resp.text, "html.parser")
        lines = [l.strip() for l in soup.text.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            if "~" not in line or not re.search(r"\d{4}\.\d{2}\.\d{2}", line):
                continue
            try:
                name = lines[i - 1]
                if any(x in name for x in ("종목명", "기업명", "공모")) or len(name) > 20:
                    continue
                name = (
                    name.replace("[코스닥상장예정]", "")
                    .replace("[코스피상장예정]", "")
                    .strip()
                )
                price_raw = lines[i + 1] if i + 1 < len(lines) else "-"

                underwriter = "-"
                for j in range(i + 2, min(i + 6, len(lines))):
                    if "증권" in lines[j] or "투자" in lines[j]:
                        underwriter = lines[j]
                        break

                start_s, end_s = line.split("~")
                start_s, end_s = start_s.strip(), end_s.strip()
                sb = start_s.split(".")
                start_date = f"{sb[0]}-{sb[1].zfill(2)}-{sb[2].zfill(2)}"
                eb = end_s.split(".")
                if len(eb) == 3:
                    end_date = f"{eb[0]}-{eb[1].zfill(2)}-{eb[2].zfill(2)}"
                else:
                    end_date = f"{sb[0]}-{eb[0].zfill(2)}-{eb[1].zfill(2)}"

                items.append({
                    "name": name,
                    "start": start_date,
                    "end": end_date,
                    "price": price_raw.replace("원", "").strip(),
                    "underwriter": underwriter,
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[ipo_crawler] 크롤링 에러: {e}")

    _cache = (items, time.time())
    return items


async def fetch_all_ipo() -> list[dict]:
    """38커뮤니케이션에서 전체 공모주 목록을 가져옵니다 (15분 캐시)."""
    return await asyncio.to_thread(_fetch_sync)


# ── 날짜 필터 ──────────────────────────────────────────────────

def ipo_today(items: list[dict]) -> list[dict]:
    today = datetime.today().strftime("%Y-%m-%d")
    return [it for it in items if it["start"] <= today <= it["end"]]


def ipo_this_week(items: list[dict]) -> list[dict]:
    today_dt = datetime.today()
    today = today_dt.strftime("%Y-%m-%d")
    sunday = (today_dt + timedelta(days=6 - today_dt.weekday())).strftime("%Y-%m-%d")
    return [it for it in items if it["start"] <= sunday and it["end"] >= today]


def ipo_next_week(items: list[dict]) -> list[dict]:
    today_dt = datetime.today()
    gap = 6 - today_dt.weekday()
    next_monday = (today_dt + timedelta(days=gap + 1)).strftime("%Y-%m-%d")
    next_sunday = (today_dt + timedelta(days=gap + 7)).strftime("%Y-%m-%d")
    return [it for it in items if it["start"] <= next_sunday and it["end"] >= next_monday]


def filter_ipo(items: list[dict], range_: str) -> list[dict]:
    if range_ == "today":
        return ipo_today(items)
    if range_ == "this_week":
        return ipo_this_week(items)
    if range_ == "next_week":
        return ipo_next_week(items)
    return items  # "all"
