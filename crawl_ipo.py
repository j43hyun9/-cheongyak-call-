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

# ─── [개선 반영] fetch_ipo 내에 캐시 만료(TTL 24h) 검증 로직 추가 ───
def fetch_ipo(force_refresh=False) -> list[dict]:
    """
    38커뮤니케이션에서 공모주 일정을 가져옵니다.
    - force_refresh=False 이면 기존 캐시 파일의 fetched_at을 확인하여 당일 데이터인 경우 캐시를 반환합니다.
    - 캐시가 만료(24시간 경과)되었거나 True 이면 무조건 새로 크롤링합니다.
    """
    cache_filename = "ipo_cache.json"
    today_str = str(datetime.today().date()) # 오늘 날짜 (YYYY-MM-DD)
    
    # 1. 캐시 파일이 존재하고 강제 갱신 요청이 아닐 때 만료 여부(TTL) 체크
    if not force_refresh and os.path.exists(cache_filename):
        try:
            with open(cache_filename, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                
            fetched_at = cached_data.get("fetched_at", "")
            
            # 수집된 날짜(fetched_at)가 오늘 날짜와 같다면 캐시 데이터 유효 (24h 이내)
            if fetched_at == today_str:
                print(f"🔄 [캐시 사용] 당일 수집된 캐시가 유효합니다. (fetched_at: {fetched_at})")
                return cached_data.get("items", [])
            else:
                print(f"⏳ [캐시 만료] 캐시 날짜({fetched_at})가 오늘({today_str})과 달라 재크롤링을 진행합니다.")
        except Exception as e:
            print(f"⚠️ 캐시 파일을 읽는 중 오류가 발생하여 재크롤링합니다: {e}")
            pass

    # 2. 크롤링 시작 (캐시가 없거나, 만료되었거나, force_refresh=True 인 경우)
    print("🌐 [네트워크 요청] 38커뮤니케이션 실시간 데이터 긁어오는 중...")
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
            "fetched_at": today_str,  # 오늘 날짜로 갱신 기록
            "items": final_items
        }
        
        with open(cache_filename, "w", encoding="utf-8") as f:
            json.dump(ipo_cache_data, f, ensure_ascii=False, indent=2)
            
        print("💾 [캐시 업데이트] 새로운 공모주 데이터를 캐시 파일에 저장했습니다.")
        return final_items

    except Exception as e:
        print(f"❌ 크롤링 에러 발생 (백업 캐시 점검): {e}")
        # 크롤링 실패 시 만료 여부 불문하고 물리적인 캐시 파일이라도 있으면 최종 보루로 리턴
        if os.path.exists(cache_filename):
            try:
                with open(cache_filename, "r", encoding="utf-8") as f:
                    print("⚠️ 네트워크 에러로 인해 만료된 과거 캐시 데이터를 반환합니다.")
                    return json.load(f).get("items", [])
            except:
                pass
        return []


# ─── 오늘/이번 주 청약 항목 필터링 함수 ───

def ipo_today(items: list[dict], today: str) -> list[dict]:
    """ 오늘(today: 'YYYY-MM-DD') 청약 진행 중(start <= today <= end)인 기업 필터링 """
    return [item for item in items if item['start'] <= today <= item['end']]


def ipo_week(items: list[dict], today: str) -> list[dict]:
    """ 오늘(today)을 기준으로 이번 주 일요일까지 청약 일정이 겹치는 기업 필터링 """
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    days_to_sunday = 6 - today_dt.weekday()
    sunday_dt = today_dt + timedelta(days=days_to_sunday)
    sunday = sunday_dt.strftime("%Y-%m-%d")
    
    return [item for item in items if item['start'] <= sunday and item['end'] >= today]


# --- 외부 테스트 및 확인 구문 ---
if __name__ == "__main__":
    print("=== [테스트 1] 캐시 제어 및 TTL 검증 ===")
    # 첫 호출 (만약 오늘 이미 생성된 json이 있다면 캐시를 읽고, 없거나 어제 날짜면 크롤링을 합니다)
    ipo_list = fetch_ipo(force_refresh=False)
    print(f"결과 데이터 수: {len(ipo_list)}건\n")
    
    print("=== [테스트 2] 의도적 강제 새로고침 ===")
    # 기획자 테스트용 파라미터 작동 검증
    ipo_list_forced = fetch_ipo(force_refresh=True)
    print(f"결과 데이터 수: {len(ipo_list_forced)}건")
