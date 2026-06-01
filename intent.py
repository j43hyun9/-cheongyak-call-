# ==================================================
# intent.py (고급 버전 - One Cell)
# ==================================================

import re
from datetime import datetime, timedelta

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