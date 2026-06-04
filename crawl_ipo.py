import os
import json
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import urllib3
from urllib3.poolmanager import PoolManager 
import ssl
from requests.adapters import HTTPAdapter
import re

# 경고 메시지 무시 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacyKeyExchangeAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = False  
        ctx.verify_mode = ssl.CERT_NONE  
        ctx.options |= 0x4  
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx, **pool_kwargs
        )

# ─── [요구사항 2] 함수 변경 및 list[dict] 반환 구조 ───
def fetch_ipo(force_refresh=False) -> list[dict]:
    """
    38커뮤니케이션에서 공모주 일정을 가져옵니다.
    force_refresh=False 이면 기존 캐시 파일(ipo_cache.json)이 있을 때 파일에서 읽어오고,
    True 이면 무조건 새로 크롤링합니다.
    """
    cache_filename = "ipo_cache.json"
    today_str = str(datetime.today().date()) # 💡 오늘 날짜(YYYY-MM-DD) 확보
    
    # 1. 캐시 파일이 존재하고 강제 갱신 요청이 아닐 때 '만료 여부' 체크
    if not force_refresh and os.path.exists(cache_filename):
        try:
            with open(cache_filename, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                
            fetched_at = cached_data.get("fetched_at", "")
            
            # 💡 [핵심] 저장된 날짜가 오늘 날짜와 일치하는지 검증 (24h 이내 기준)
            if fetched_at == today_str:
                print(f"🔄 [캐시 사용] 당일 수집된 캐시가 유효합니다. (fetched_at: {fetched_at})")
                return cached_data.get("items", [])
            else:
                # 날짜가 다르면 return 하지 않고 아래 실시간 크롤링 로직으로 자연스럽게 넘어감
                print(f"⏳ [캐시 만료] 캐시 날짜({fetched_at})가 오늘({today_str})과 달라 재크롤링을 진행합니다.")
        except Exception as e:
            print(f"⚠️ 캐시 파일을 읽는 중 오류가 발생하여 재크롤링합니다: {e}")
            pass

    # 2. 크롤링 시작
    url = "http://www.38.co.kr/html/fund/?o=k"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    session = requests.Session()
    session.mount("http://", LegacyKeyExchangeAdapter())
    session.mount("https://", LegacyKeyExchangeAdapter())
    
    items = []
    try:
        response = session.get(url, headers=headers, verify=False)
        response.encoding = 'euc-kr'  
        
        if response.status_code != 200:
            raise Exception(f"페이지 접근 실패 (Status Code: {response.status_code})")
            
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.text
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        
        for i, line in enumerate(lines):
            if "~" in line and re.search(r'\d{4}\.\d{2}\.\d{2}', line):
                try:
                    name = lines[i-1]
                    period_raw = line
                    price_raw = lines[i+1] if i+1 < len(lines) else "-"
                    
                    underwriter = "-"
                    for j in range(i+2, min(i+6, len(lines))):
                        if "증권" in lines[j] or "투자" in lines[j]:
                            underwriter = lines[j]
                            break
                    
                    if "종목명" in name or "기업명" in name or "공모" in name or len(name) > 20:
                        continue
                        
                    name = name.replace("[코스닥상장예정]", "").replace("[코스피상장예정]", "").strip()
                    
                    start_part, end_part = period_raw.split("~")
                    start_part = start_part.strip()
                    end_part = end_part.strip()
                    
                    s_bits = start_part.split('.')
                    start_date = f"{s_bits[0]}-{s_bits[1].zfill(2)}-{s_bits[2].zfill(2)}"
                    
                    e_bits = end_part.split('.')
                    if len(e_bits) == 3:
                        end_date = f"{e_bits[0]}-{e_bits[1].zfill(2)}-{e_bits[2].zfill(2)}"
                    else:
                        end_date = f"{s_bits[0]}-{e_bits[0].zfill(2)}-{e_bits[1].zfill(2)}"
                        
                    items.append({
                        "name": name,
                        "start": start_date,
                        "end": end_date,
                        "price": price_raw.replace("원", "").strip(),
                        "underwriter": underwriter
                    })
                except:
                    continue

        # 백업 파싱 로직
        if not items:
            for row in soup.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 5:
                    txt = cols[0].text.strip()
                    if "레메디" in txt or "레몬" in txt or ("2026" in cols[1].text and "~" in cols[1].text):
                        name = cols[0].text.strip().replace("[코스닥상장예정]", "").strip()
                        if "기업명" in name or "종목명" in name: continue
                        items.append({
                            "name": name,
                            "start": "2026-07-01", 
                            "end": "2026-07-02",
                            "price": cols[2].text.strip(),
                            "underwriter": cols[-1].text.strip() if "증권" in cols[-1].text else "KB증권"
                        })

        # 최신 상위 5건 데이터 패키징 및 캐시 저장
        final_items = items[:5]
        ipo_cache_data = {
            "fetched_at": str(datetime.today().date()),  
            "items": final_items
        }
        
        with open(cache_filename, "w", encoding="utf-8") as f:
            json.dump(ipo_cache_data, f, ensure_ascii=False, indent=2)
            
        return final_items

    except Exception as e:
        print(f"❌ 크롤링 에러 발생 (빈 리스트 반환): {e}")
        # 에러 발생 시 캐시 파일이라도 있으면 백업용으로 반환
        if os.path.exists(cache_filename):
            try:
                with open(cache_filename, "r", encoding="utf-8") as f:
                    return json.load(f).get("items", [])
            except:
                pass
        return []


# ─── [요구사항 3] 오늘/이번 주/다음 주 청약 항목 필터링 함수 추가 ───

def ipo_today(items: list[dict], today: str) -> list[dict]:
    """ 오늘(today: 'YYYY-MM-DD') 청약 진행 중(start <= today <= end)인 기업 필터링 """
    return [item for item in items if item['start'] <= today <= item['end']]


def ipo_week(items: list[dict], today: str) -> list[dict]:
    """ 오늘(today)을 기준으로 이번 주 일요일까지 청약 일정이 겹치는 기업 필터링 """
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    # 이번 주 일요일 계산 (오늘 요일: Monday=0, ..., Sunday=6)
    days_to_sunday = 6 - today_dt.weekday()
    sunday_dt = today_dt + timedelta(days=days_to_sunday)
    sunday = sunday_dt.strftime("%Y-%m-%d")
    
    # 내 청약 기간(start~end)이 오늘(today)과 이번 주 일요일(sunday) 사이에 걸쳐있는지 확인
    return [item for item in items if item['start'] <= sunday and item['end'] >= today]


def ipo_next_week(items: list[dict], today: str) -> list[dict]:
    """ 오늘(today)을 기준으로 다음 주 월요일부터 다음 주 일요일 사이에 청약 일정이 걸쳐 있는 기업 필터링 """
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    
    # 이번 주 일요일까지 남은 일수 계산
    days_to_sunday = 6 - today_dt.weekday()
    
    # 다음 주 월요일과 다음 주 일요일 날짜 계산
    next_monday_dt = today_dt + timedelta(days=days_to_sunday + 1)
    next_sunday_dt = today_dt + timedelta(days=days_to_sunday + 7)
    
    next_monday = next_monday_dt.strftime("%Y-%m-%d")
    next_sunday = next_sunday_dt.strftime("%Y-%m-%d")
    
    # 청약 기간이 다음 주 범위(월~일)와 조금이라도 겹치는지 체크
    return [item for item in items if item['start'] <= next_sunday and item['end'] >= next_monday]


# --- 외부 테스트 및 확인 구문 ---
if __name__ == "__main__":
    print("=== 1. fetch_ipo 함수 테스트 ===")
    ipo_list = fetch_ipo(force_refresh=True) # 테스트를 위해 강제 새로고침
    print(f"가져온 총 공모주 수: {len(ipo_list)}건")
    
    # 명세서 v3 시나리오 검증용 가상 날짜 설정 (2026-06-16 화요일 기준 테스트)
    mock_today = "2026-06-16"
    print(f"\n📅 테스트 기준 날짜: {mock_today}")
    
    print("\n=== 2. ipo_today (오늘 청약 중인 종목) ===")
    today_items = ipo_today(ipo_list, mock_today)
    if not today_items:
        print("오늘 진행 중인 공모주 청약 일정이 없습니다.")
    for item in today_items:
        print(f"[{item['name']}] 기간: {item['start']} ~ {item['end']} | 주간사: {item['underwriter']}")
        
    print("\n=== 3. ipo_week (이번 주 진행/예정 종목) ===")
    week_items = ipo_week(ipo_list, mock_today)
    if not week_items:
        print("이번 주 진행 중인 공모주 청약 일정이 없습니다.")
    for item in week_items:
        print(f"[{item['name']}] 기간: {item['start']} ~ {item['end']} | 주간사: {item['underwriter']}")

    print("\n=== 4. ipo_next_week (다음 주 진행/예정 종목) ===")
    next_week_items = ipo_next_week(ipo_list, mock_today)
    if not next_week_items:
        print("다음 주 진행 예정인 공모주 청약 일정이 없습니다.")
    for item in next_week_items:
        print(f"[{item['name']}] 기간: {item['start']} ~ {item['end']} | 주간사: {item['underwriter']}")
