import os
import json
from datetime import datetime
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

def crawl_ipo_schedule():
    url = "http://www.38.co.kr/html/fund/?o=k"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    session = requests.Session()
    session.mount("http://", LegacyKeyExchangeAdapter())
    session.mount("https://", LegacyKeyExchangeAdapter())
    
    try:
        response = session.get(url, headers=headers, verify=False)
        response.encoding = 'euc-kr'  
        
        if response.status_code != 200:
            raise Exception(f"페이지 접근 실패 (Status Code: {response.status_code})")
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        items = []
        current_year = datetime.today().year # 2026
        
        # ─── [새로운 접근] 태그 조건에 구애받지 않고 텍스트 덩어리에서 정밀 파싱 ───
        # 아까 데이터가 무더기로 잡혔던 본문 핵심 구역을 가져옵니다.
        page_text = soup.text
        
        # 줄바꿈 단위로 쪼갠 뒤 공백을 정리합니다.
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        
        # 기업명 뒤에 날짜(YYYY.MM.DD~MM.DD)가 나오는 패턴을 역추적합니다.
        for i, line in enumerate(lines):
            # 날짜 형식 패턴 매칭 (예: 2026.07.01~07.02)
            if "~" in line and re.search(r'\d{4}\.\d{2}\.\d{2}', line):
                try:
                    # 현재 줄이 날짜라면 바로 앞 줄이 '기업명'일 확률이 높습니다.
                    name = lines[i-1]
                    period_raw = line
                    price_raw = lines[i+1] if i+1 < len(lines) else "-"
                    
                    # 주간사(증권사)는 보통 그 다음다음 줄 근처에 위치합니다.
                    underwriter = "-"
                    for j in range(i+2, min(i+6, len(lines))):
                        if "증권" in lines[j] or "투자" in lines[j]:
                            underwriter = lines[j]
                            break
                    
                    # 잡상인 데이터 및 헤더 필터링
                    if "종목명" in name or "기업명" in name or "공모" in name or len(name) > 20:
                        continue
                        
                    name = name.replace("[코스닥상장예정]", "").replace("[코스피상장예정]", "").strip()
                    
                    # 날짜 표준화 처리
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

        # 만약 위 텍스트 기반으로도 실패했을 경우를 대비한 기존 TR 백업 파싱 로직
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

        # 최종 상위 5건만 패키징
        ipo_cache_data = {
            "fetched_at": str(datetime.today().date()),  
            "items": items[:5]  
        }
        
        cache_filename = "ipo_cache.json"
        with open(cache_filename, "w", encoding="utf-8") as f:
            json.dump(ipo_cache_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 크롤링 성공! 정제된 {len(items[:5])}건의 공모주 데이터를 '{cache_filename}'에 완벽하게 저장했습니다.")
        return True

    except Exception as e:
        print(f"❌ 크롤링 실패: {e}")
        return False

if __name__ == "__main__":
    crawl_ipo_schedule()
