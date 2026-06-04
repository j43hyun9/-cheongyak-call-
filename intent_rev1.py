from openai import OpenAI
from datetime import datetime
import json

# ==========================================
# OpenAI API Key (API 키 필요)
# ==========================================

client = OpenAI(
    api_key="YOUR_OPENAI_API_KEY"
)

# ==========================================
# 일정 저장소
# ==========================================

schedule_db = []

# ==========================================
# GPT 의도분석 + 정보추출
# ==========================================

def analyze_user_text(text):

    system_prompt = """
너는 금융 비서 NLU 엔진이다.

반드시 JSON만 출력한다.

intent는 아래 중 하나:

공모주조회
일정등록
일정조회
모름

출력 형식:

{
  "intent":"일정등록",
  "title":"팀회의",
  "datetime":"2026-06-02 15:00"
}

규칙:

1. 제목이 없으면 null
2. 시간이 없으면 null
3. 알 수 없는 명령이면 intent=모름
4. JSON 외 다른 문장 출력 금지
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role":"system",
                "content":system_prompt
            },
            {
                "role":"user",
                "content":text
            }
        ],
        temperature=0
    )

    result = response.choices[0].message.content

    return json.loads(result)

# ==========================================
# 일정 등록
# ==========================================

def add_schedule(parsed):

    title = parsed.get("title")
    dt = parsed.get("datetime")

    if not dt:

        return "시간을 입력해주세요."

    if not title:

        return "일정 제목을 입력해주세요."

    schedule_db.append(
        {
            "title":title,
            "datetime":dt
        }
    )

    return f"{dt}에 {title} 저장했습니다."

# ==========================================
# 일정 조회
# ==========================================

def view_schedule():

    if len(schedule_db) == 0:

        return "등록된 일정이 없습니다."

    result = "등록된 일정\n\n"

    for i,s in enumerate(schedule_db):

        result += (
            f"{i+1}. "
            f"{s['title']} "
            f"({s['datetime']})\n"
        )

    return result

# ==========================================
# 공모주 Mock
# ==========================================

def get_ipo_info():

    return """
[이번주 공모주]

1. ABC바이오
공모가: 18,000원
주관사: 미래에셋

2. 뉴테크
공모가: 22,000원
주관사: NH투자증권
"""

# ==========================================
# 최종 처리
# ==========================================

def process_user_command(text):

    if text is None or len(text.strip()) == 0:

        return "다시 말씀해 주세요."

    parsed = analyze_user_text(text)

    intent = parsed["intent"]

    # W-01

    if (
        "공모주" in text
        and "등록" in text
    ):

        return (
            "공모주 조회인지 "
            "일정 등록인지 "
            "명확히 입력해주세요."
        )

    if intent == "공모주조회":

        return get_ipo_info()

    if intent == "일정등록":

        return add_schedule(parsed)

    if intent == "일정조회":

        return view_schedule()

    return "아직 지원하지 않는 명령이에요."

# ==========================================
# 테스트
# ==========================================

tests = [

    "공모주 일정 등록해줘",

    "팀회의 등록",

    "내일 3시 등록",

    "내일 오후 3시 팀회의 등록",

    "오늘 일정 알려줘",

    "이번주 공모주 알려줘",

    "오늘 날씨 어때"
]

for t in tests:

    print("="*60)

    print("입력:", t)

    print(
        process_user_command(t)
    )

    print()