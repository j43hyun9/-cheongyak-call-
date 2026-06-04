#★★★★★★ 최종본 (UI수정중) ★★★★★★
# env파일 별도 필요

# =========================================================
# 📌 필요한 라이브러리 설치
# =========================================================
# pip install gradio gtts openai python-dotenv requests beautifulsoup4 urllib3

import gradio as gr
from gtts import gTTS
from openai import OpenAI
from dotenv import load_dotenv
import os


# 김준서

from datetime import datetime
from tts import synthesize
from schedule import save_schedule, load_schedule
import json

# 장두호
import re
from datetime import datetime, timedelta

#임강
import requests
from bs4 import BeautifulSoup
import urllib3
from urllib3.poolmanager import PoolManager 
import ssl
from requests.adapters import HTTPAdapter



# =========================================================
# 🔐 OpenAI API KEY 로드
# =========================================================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(
    api_key=OPENAI_API_KEY
)

# =========================================================
# 🔊 시작 음성 테스트
# =========================================================
welcome_text = "안녕하세요, 공모주일정비서 청 약 콜 입니다.녹음 버튼을 눌러 음성으로 질문해보세요"

tts = gTTS(text=welcome_text, lang='ko')
tts.save("welcome.mp3")

welcome_text2 = "새로운 질문을 말씀해 주세요. 바로 확인해 드리겠습니다."
tts2 = gTTS(text=welcome_text2, lang='ko')
tts2.save("welcome_again.mp3")

# =========================================================
# app / 김준서
# =========================================================

# --- TTS ---

def tts_handler(text: str):
    if not text.strip():
        return None
    path = synthesize(text)
    return path


# --- 일정 저장 ---

def add_schedule_handler(title: str, date_str: str, time_str: str):
    if not title.strip() or not date_str or not time_str:
        return "제목, 날짜, 시간을 모두 입력해 주세요."
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "날짜/시간 형식을 확인해 주세요. (날짜: YYYY-MM-DD, 시간: HH:MM)"
    entry = save_schedule(title, dt)
    return f"저장됨: {entry['title']} @ {entry['datetime']}"


# --- 일정 조회 ---

def view_schedule_handler(date_str: str):
    if not date_str:
        return "날짜를 입력해 주세요."
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "날짜 형식을 확인해 주세요. (YYYY-MM-DD)"
    items = load_schedule(dt)
    if not items:
        return "해당 날짜에 일정이 없습니다."
    return "\n".join(f"- {i['title']}  ({i['datetime'][11:16]})" for i in items)


# =========================================================
# 🔊 TTS 함수 / 김준서
# =========================================================
def speak(text):
    tts = gTTS(text=text, lang='ko')
    output_file = "response.mp3"
    tts.save(output_file)
    return output_file


if __name__ == "__main__":
    speak("안녕하세요, AI 투자 일정 비서입니다.")
    speak("공모주 청약 일정을 알려드리겠습니다.")

# =========================================================
# ✅ schedule.py 김준서
# =========================================================

SCHEDULE_FILE = "schedule.json"


def _load_all() -> list:
    if not os.path.exists(SCHEDULE_FILE):
        return []
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: list) -> None:
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_schedule(title: str, dt: datetime) -> dict:
    data = _load_all()
    entry = {"title": title, "datetime": dt.isoformat()}
    data.append(entry)
    _save_all(data)
    return entry


def load_schedule(target_date: datetime) -> list:
    data = _load_all()
    target_str = target_date.date().isoformat()
    return [
        item for item in data
        if item["datetime"].startswith(target_str)
    ]


if __name__ == "__main__":
    save_schedule("팀 회의", datetime(2026, 6, 5, 18, 0))
    save_schedule("조깅", datetime(2026, 6, 5, 9, 0))

    results = load_schedule(datetime(2026, 6, 5))
    for r in results:
        print(r)

# =========================================================
# ☑️ LL M 로직 / 장두호
# =========================================================

# =========================================================
# ✅ intent 장두호
# =========================================================

# ==================================================
# Intent 상수
# ==================================================

INTENT_IPO = "공모주조회"
INTENT_ADD = "일정등록"
INTENT_VIEW = "일정조회"
INTENT_UNKNOWN = "모름"


# ==================================================
# Intent 분류
# ==================================================

def classify_intent(text):

    text = text.strip()

    ipo_keywords = [
        "공모주",
        "ipo",
        "청약",
        "상장예정"
    ]

    add_keywords = [
        "등록",
        "추가",
        "예약",
        "넣어줘",
        "저장",
        "잡아줘"
    ]

    view_keywords = [
        "일정",
        "스케줄",
        "캘린더",
        "조회",
        "확인",
        "뭐있어",
        "알려줘",
        "보여줘"
    ]

    if any(k in text for k in ipo_keywords):

        return {
            "intent": INTENT_IPO,
            "confidence": 0.99
        }

    if any(k in text for k in add_keywords):

        return {
            "intent": INTENT_ADD,
            "confidence": 0.95
        }

    if any(k in text for k in view_keywords):

        return {
            "intent": INTENT_VIEW,
            "confidence": 0.90
        }

    return {
        "intent": INTENT_UNKNOWN,
        "confidence": 0.50
    }


# ==================================================
# 날짜 파싱
# ==================================================

def parse_kr_datetime(text, now=None):

    if now is None:
        now = datetime.now()

    target_date = now

    # -------------------------
    # 상대 날짜
    # -------------------------

    if "오늘" in text:

        target_date = now

    elif "내일" in text:

        target_date = now + timedelta(days=1)

    elif "모레" in text:

        target_date = now + timedelta(days=2)

    elif "다음주" in text:

        target_date = now + timedelta(days=7)

    # -------------------------
    # 절대 날짜
    # ex) 6월 10일
    # -------------------------

    month_day = re.search(
        r'(\d{1,2})월\s*(\d{1,2})일',
        text
    )

    if month_day:

        month = int(month_day.group(1))
        day = int(month_day.group(2))

        target_date = datetime(
            now.year,
            month,
            day
        )

    # -------------------------
    # 시간
    # -------------------------

    hour = 9
    minute = 0

    hour_match = re.search(
        r'(\d{1,2})시',
        text
    )

    if hour_match:

        hour = int(hour_match.group(1))

    minute_match = re.search(
        r'(\d{1,2})분',
        text
    )

    if minute_match:

        minute = int(minute_match.group(1))

    # 오전

    if "오전" in text:

        if hour == 12:

            hour = 0

    # 오후

    if "오후" in text:

        if hour < 12:

            hour += 12

    # 저녁

    if "저녁" in text:

        if hour < 12:

            hour += 12

    # 밤

    if "밤" in text:

        if hour < 12:

            hour += 12

    return target_date.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )


# ==================================================
# 제목 추출
# ==================================================

def extract_title(text):

    title = text

    remove_words = [

        "오늘",
        "내일",
        "모레",
        "다음주",

        "오전",
        "오후",
        "저녁",
        "밤",

        "일정",
        "등록",
        "추가",
        "예약",
        "잡아줘",
        "넣어줘",
        "저장",

        "조회",
        "확인",
        "알려줘",
        "보여줘"
    ]

    for word in remove_words:

        title = title.replace(word, "")

    title = re.sub(r'\d+월', '', title)
    title = re.sub(r'\d+일', '', title)

    title = re.sub(r'\d+시', '', title)
    title = re.sub(r'\d+분', '', title)

    title = title.strip()

    if not title:

        title = "일정"

    return title


# ==================================================
# 일정 등록 정보 추출
# ==================================================

def parse_schedule_args(text, now=None):

    dt = parse_kr_datetime(text, now)

    title = extract_title(text)

    intent_result = classify_intent(text)

    return {

        "intent":
            intent_result["intent"],

        "title":
            title,

        "datetime":
            dt,

        "confidence":
            intent_result["confidence"]
    }


# ==================================================
# 테스트
# ==================================================

if __name__ == "__main__":

    now = datetime(
        2026,
        6,
        1,
        10,
        0
    )

    samples = [

        "공모주 일정 알려줘",

        "내일 오후 3시 팀회의 등록",

        "모레 오전 10시 프로젝트 미팅 추가",

        "다음주 일정 조회",

        "6월 10일 오전 9시 캡스톤 디자인 발표 등록"
    ]

    for text in samples:

        print("=" * 60)

        print("입력:", text)

        intent = classify_intent(text)

        print("Intent:", intent)

        result = parse_schedule_args(
            text,
            now
        )

        print("결과:")

        print(result)

        print()

# =========================================================
# 🎤 Whisper STT 함수 / 임강
# =========================================================
def convert_speech_to_text_whisper(audio_path, api_key=None):
    """
    [OpenAI Whisper API 버전]
    오디오 파일 경로를 받아 Whisper-1 모델을 통해 텍스트로 변환합니다.
    """
    # ─── [피드백 반영] 에러 발생 시 다운스트림 오해 방지를 위해 빈 문자열("") 반환 ───
    if not audio_path or not os.path.exists(audio_path): 
        print("⚠️ 오디오 파일이 유효하지 않거나 존재하지 않습니다.")
        return ""
        
    final_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not final_api_key:
        print("❌ OpenAI API Key가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
        return ""

    try:
        client = OpenAI(api_key=final_api_key)
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                language="ko",
                # 기획서 시나리오 맞춤형 힌트 단어 (소음 환각 방지)
                prompt="공모주, 청약, 등록, 일정, 회의 관련 명령입니다." 
            )
        return transcript.text.strip()
    except Exception as e:
        print(f"❌ Whisper STT 에러 발생: {e}")
        return ""


# ─── [피드백 반영] 기획자 요청 별칭(Alias) 함수 추가 ───
def transcribe(audio_path) -> str:
    """
    STT 모듈의 통합용 메인 함수 인터페이스입니다.
    Gradio UI 및 타 모듈에서 import 할 때 이 함수를 호출합니다.
    """
    return convert_speech_to_text_whisper(audio_path)


# --- 단독 실행 및 테스트 구문 ---
if __name__ == "__main__":
    # 테스트할 파일명을 적어주세요 (Gradio 결합 시에는 이 구문이 실행되지 않습니다)
    test_file = "test1.wav" 
    
    print("=== OpenAI Whisper STT 단독 테스트 (transcribe 호출) ===")
    if os.path.exists(test_file):
        print(f"🔄 [{test_file}] 파일 변환 중...")
        result = transcribe(test_file)
        print(f"👉 결과: \"{result}\"")
    else:
        print(f"ℹ️ 테스트할 [{test_file}] 파일이 로컬에 없습니다. 파일명을 확인해 주세요.")

# =========================================================
# ✅ crawler.py 임강
# =========================================================

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
    
# =========================================================
# 🤖 메인 음성 비서 함수 / 백승옥
# =========================================================
def process_text_command(recognized_text):

    intent_result = classify_intent(recognized_text)
    intent = intent_result["intent"]

    if intent == INTENT_IPO:
        items = fetch_ipo()

        if not items:
            answer = "공모주 일정을 가져오지 못했습니다."
        else:
            answer = "📈 공모주 일정입니다.\n\n"

            for item in items:
                answer += (
                    f"기업명 : {item['name']}\n"
                    f"청약기간 : {item['start']} ~ {item['end']}\n"
                    f"주간사 : {item['underwriter']}\n\n"
                )

    elif intent == INTENT_ADD:
        result = parse_schedule_args(recognized_text)

        entry = save_schedule(
            result["title"],
            result["datetime"]
        )

        answer = (
            f"{entry['title']} 일정이 등록되었습니다.\n"
            f"{entry['datetime']}"
        )

    elif intent == INTENT_VIEW:
        target_date = parse_kr_datetime(recognized_text)
        schedules = load_schedule(target_date)

        if not schedules:
            answer = "등록된 일정이 없습니다."
        else:
            answer = "등록된 일정입니다.\n\n"

            for s in schedules:
                dt = datetime.fromisoformat(s["datetime"])
                answer += f"- {dt.strftime('%H:%M')} {s['title']}\n"

    else:
        answer = "죄송해요. 공모주 일정 조회 또는 일정 등록만 가능합니다."

    return answer

def unified_assistant(audio, text):

    try:
        # 1) 텍스트 입력이 있으면 텍스트 우선 사용
        if text and text.strip():
            recognized_text = text.strip()

        # 2) 텍스트가 없고 음성이 있으면 STT 사용
        elif audio is not None:
            if not os.getenv("OPENAI_API_KEY"):
                msg = "OPENAI_API_KEY 설정을 확인해 주세요."
                return "", msg, speak(msg)

            recognized_text = transcribe(audio)

            if not recognized_text:
                msg = "음성을 인식하지 못했습니다. 다시 말씀해 주세요."
                return "", msg, speak(msg)

        # 3) 둘 다 없으면 안내
        else:
            msg = "음성으로 질문하거나 텍스트를 입력해 주세요."
            return "", msg, speak(msg)

        # 4) 기존 AI 처리 로직 사용
        answer = process_text_command(recognized_text)
        response_audio = speak(answer)

        return recognized_text, answer, response_audio

    except Exception as e:
        print("❌ unified_assistant 오류:", e)
        return "", f"오류가 발생했습니다. ({str(e)})", None
    
def ipo_assistant(audio):

    try:

        # =========================
        # 1. 녹음 안 된 경우
        # =========================
        if audio is None:
            msg = "녹음이 안 됐어요. 다시 시도해 주세요."
            return (
                "",
                msg,
                speak(msg)   # 🔊 추가 (음성 출력)
            )

        # =========================
        # 2. STT
        # =========================
        if not os.getenv("OPENAI_API_KEY"):
            msg = "OPENAI_API_KEY 설정을 확인해 주세요."
            return (
                "",
                msg,
                speak(msg)
            )
        recognized_text = transcribe(audio)

        print("📝 인식된 텍스트:", recognized_text)
        
        # STT 실패
        if not recognized_text:
            msg = "음성을 인식하지 못했습니다. 다시 말씀해 주세요."
            return (
                "",
                msg,
                speak(msg)   
            )

        intent_result = classify_intent(recognized_text)   
        intent = intent_result["intent"]
        print("Intent :", intent)

        # =========================
        # 3. 기존 답변 로직
        # =========================
        

        if intent == INTENT_IPO:

            items = fetch_ipo()

            if not items:
                answer = "공모주 일정을 가져오지 못했습니다."

            else:

                answer = "📈 공모주 일정입니다.\n\n"

                for item in items:

                    answer += (
                        f"기업명 : {item['name']}\n"
                        f"청약기간 : {item['start']} ~ {item['end']}\n"
                        f"주간사 : {item['underwriter']}\n\n"
                    )

        elif intent == INTENT_ADD:

            result = parse_schedule_args(recognized_text)

            save_schedule(
               result["title"],
                result["datetime"]
             )

            answer = (
                f"{result['title']} 일정이 등록되었습니다.\n"
                f"{result['datetime']}"
            )

        elif intent == INTENT_VIEW:

            target_date = parse_kr_datetime(recognized_text)
            schedules = load_schedule(target_date)

            if not schedules:
                answer = "등록된 일정이 없습니다."

            else:

                answer = "등록된 일정입니다.\n\n"

                for s in schedules:

                    dt = datetime.fromisoformat(
                        s["datetime"]
                    )

                    answer += (
                        f"- {dt.strftime('%H:%M')} "
                        f"{s['title']}\n"
                        )

        else:

            answer = (
                "죄송해요. "
                "공모주 일정 또는 일정 등록만 가능합니다."
            )

        response_audio = speak(answer)

        return (
            recognized_text,
            answer,
            response_audio
        )

    except Exception as e:

        print("❌ ipo_assistant 오류:", e)

        return (
            "",
            f"오류가 발생했습니다. ({str(e)})",
            None
        )
# =========================================================
# 🔄 초기화 함수 / 백승옥
# =========================================================
def reset_ui(count):

    count += 1

    if count == 1:
        audio_file = "welcome.mp3"
    else:
        audio_file = "welcome_again.mp3"

    return (
        None,
        "",
        "",
        "",
        audio_file,
        count
    )

# =========================================================
# 🎨 CSS / 백승옥
# =========================================================
custom_css = """
.gradio-container {
    max-width: 1200px !important;
    width: 90vw !important;
    margin: auto;
    font-family: Arial;
}

h1 {
    text-align: center;
    font-size: 30px;
}

.center-box {
    text-align: center;
    margin: 15px 0;
}

.left-buttons {
    display: flex !important;
    justify-content: flex-start !important;
    gap: 10px;
    margin-top: 10px;
}

/* 입력 텍스트 */
textarea {
    font-size: 15px !important;
}

/* 오디오 영역 */
.gradio-container audio {
    width: 100% !important;
    max-width: 800px;
    margin: auto;
    display: block;
}
"""

# =========================================================
# 🎨 Gradio UI / 백승옥
# =========================================================
with gr.Blocks(theme="soft", css=custom_css) as demo:

    # 상태값
    reset_count = gr.State(0)

    # =========================
    # 제목
    # =========================
    gr.Markdown("""
# 📈 공모주 일정 AI 비서 <청약콜>
""")

    # =========================
    # 안내 영역
    # =========================
    with gr.Column(elem_classes="center-box"):
        gr.Markdown(""" """)

    # =========================
    # 입력 영역
    # =========================
    audio_input = gr.Audio(
        sources=["microphone"],
        type="filepath",
        label="🎤 음성으로 질문하세요"
    )

    text_input = gr.Textbox(
        label="⌨️ 텍스트로 질문하세요",
        placeholder="예: 이번주 공모주 알려줘 / 내일 오후 3시 팀회의 등록해줘",
        lines=2
    )

    # =========================
    # 버튼 영역
    # =========================
    with gr.Row(elem_classes="left-buttons"):
        ask_btn = gr.Button("🎤 질문하기")
        reset_btn = gr.Button("👉시작하기")  

    # =========================
    # 설명
    # =========================
    gr.Markdown("""
💡 예시  
- "이번주 공모주 알려줘"  
- "내일 오후 3시 팀회의 등록해줘"
""")

    # =========================
    # 출력 영역
    # =========================
    stt_box = gr.Textbox(
        label="📝 인식된 음성",
        lines=2
    )

    answer_box = gr.Textbox(
        label="📅 AI 답변",
        lines=8
    )

    audio_output = gr.Audio(
        label="🔊 AI 음성 응답",
        autoplay=True
    )

    gr.Markdown("# 📅 등록된 일정 확인")

    with gr.Tab("일정 조회"):
        gr.Markdown("### 📆 날짜별 일정 조회")

        view_date = gr.Textbox(
            label="📅 조회할 날짜",
            placeholder="예: 2026-06-05"
        )

        view_btn = gr.Button("📆 일정 조회")
        
        view_result = gr.Textbox(
            label="📋 조회 결과",
            interactive=False,
            lines=7,
            placeholder="조회한 날짜의 일정이 시간순으로 표시됩니다."
        )

        view_btn.click(
            fn=view_schedule_handler,
            inputs=view_date,
            outputs=view_result
        )
    # =========================
    # 이벤트 연결
    # =========================
    ask_btn.click(
        fn=unified_assistant,
        inputs=[audio_input, text_input],
        outputs=[stt_box, answer_box, audio_output]
    )

    reset_btn.click(
        fn=reset_ui,
        inputs=[reset_count],
        outputs=[audio_input, text_input, stt_box, answer_box, audio_output, reset_count]
    )
# =========================================================
# 🚀 실행
# =========================================================

demo.launch(share=True)
