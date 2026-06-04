# ==================================================
# 금융 비서 M1 통합 Mock 버전
# ==================================================

import re
from datetime import datetime, timedelta

# ==================================================
# Intent
# ==================================================

INTENT_IPO = "공모주조회"
INTENT_ADD = "일정등록"
INTENT_VIEW = "일정조회"
INTENT_UNKNOWN = "모름"

# ==================================================
# Mock DB
# ==================================================

schedule_db = []

ipo_db = [
    {
        "name": "ABC바이오",
        "start": "2026-06-10",
        "end": "2026-06-11",
        "price": "18,000원",
        "broker": "미래에셋증권"
    },
    {
        "name": "뉴테크",
        "start": "2026-06-12",
        "end": "2026-06-13",
        "price": "22,000원",
        "broker": "NH투자증권"
    }
]

# ==================================================
# Intent 분류
# ==================================================

def classify_intent(text):

    text = text.strip()

    if any(k in text for k in ["공모주", "ipo", "청약"]):
        return INTENT_IPO

    if any(k in text for k in ["등록", "추가", "예약", "저장"]):
        return INTENT_ADD

    if any(k in text for k in [
        "일정",
        "조회",
        "확인",
        "스케줄",
        "캘린더"
    ]):
        return INTENT_VIEW

    return INTENT_UNKNOWN

# ==================================================
# W-01
# ==================================================

def detect_ambiguous_command(text):

    has_ipo = any(
        k in text
        for k in ["공모주", "ipo", "청약"]
    )

    has_add = any(
        k in text
        for k in ["등록", "추가", "예약"]
    )

    return has_ipo and has_add

# ==================================================
# 시간 체크
# ==================================================

def has_time(text):

    return bool(
        re.search(
            r'(\d{1,2})시',
            text
        )
    )

# ==================================================
# 날짜 파싱
# ==================================================

def parse_kr_datetime(text, now=None):

    if now is None:
        now = datetime.now()

    target_date = now

    if "내일" in text:
        target_date += timedelta(days=1)

    elif "모레" in text:
        target_date += timedelta(days=2)

    elif "다음주" in text:
        target_date += timedelta(days=7)

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

    hour = 0
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

    if "오후" in text and hour < 12:
        hour += 12

    if "저녁" in text and hour < 12:
        hour += 12

    if "밤" in text and hour < 12:
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

        "등록",
        "추가",
        "예약",
        "저장",

        "일정",
        "조회",
        "확인"
    ]

    for word in remove_words:
        title = title.replace(word, "")

    title = re.sub(r'\d+월', '', title)
    title = re.sub(r'\d+일', '', title)
    title = re.sub(r'\d+시', '', title)
    title = re.sub(r'\d+분', '', title)

    return title.strip()

# ==================================================
# 제목 존재
# ==================================================

def has_title(text):

    return len(
        extract_title(text)
    ) >= 2

# ==================================================
# 일정 검증
# ==================================================

def validate_schedule(text):

    if detect_ambiguous_command(text):

        return (
            False,
            "공모주 조회인지 일정 등록인지 명확히 입력해주세요."
        )

    if not has_time(text) and not has_title(text):

        return (
            False,
            "시간과 일정 제목을 입력해주세요."
        )

    if not has_time(text):

        return (
            False,
            "시간을 입력해주세요."
        )

    if not has_title(text):

        return (
            False,
            "일정 제목을 입력해주세요."
        )

    return (
        True,
        "OK"
    )

# ==================================================
# 일정 등록
# ==================================================

def add_schedule(text):

    valid, msg = validate_schedule(text)

    if not valid:

        return msg

    title = extract_title(text)

    dt = parse_kr_datetime(text)

    schedule_db.append(
        {
            "title": title,
            "datetime": dt
        }
    )

    return (
        f"{dt.strftime('%Y-%m-%d %H:%M')}에 "
        f"{title} 저장했습니다."
    )

# ==================================================
# 일정 조회
# ==================================================

def view_schedule(text):

    now = datetime.now()

    if "오늘" in text:

        today = now.date()

        result = [

            s for s in schedule_db

            if s["datetime"].date() == today
        ]

        if len(result) == 0:

            return "오늘 일정이 없습니다."

        message = (
            f"오늘 일정 {len(result)}건\n\n"
        )

        for i, item in enumerate(result):

            message += (
                f"{i+1}. "
                f"{item['title']} "
                f"({item['datetime'].strftime('%H:%M')})\n"
            )

        return message

    return "조회 날짜를 말씀해주세요."

# ==================================================
# 공모주 조회
# ==================================================

def get_ipo_info(text):

    if "오늘" in text:

        return (
            "오늘 진행중인 공모주가 없습니다."
        )

    if "이번주" in text:

        result = "[이번주 공모주]\n\n"

        for i, ipo in enumerate(ipo_db):

            result += (
                f"{i+1}. {ipo['name']}\n"
                f"청약기간: {ipo['start']} ~ {ipo['end']}\n"
                f"공모가: {ipo['price']}\n"
                f"주관사: {ipo['broker']}\n\n"
            )

        return result

    result = "[공모주 목록]\n\n"

    for i, ipo in enumerate(ipo_db):

        result += (
            f"{i+1}. {ipo['name']}\n"
            f"청약기간: {ipo['start']} ~ {ipo['end']}\n"
            f"공모가: {ipo['price']}\n"
            f"주관사: {ipo['broker']}\n\n"
        )

    return result

# ==================================================
# F4
# ==================================================

def handle_unknown():

    return (
        "아직 지원하지 않는 명령이에요."
    )

# ==================================================
# STT 실패
# ==================================================

def handle_stt_failure():

    return (
        "다시 말씀해 주세요."
    )

# ==================================================
# 최종 처리
# ==================================================

def process_user_command(text):

    if text is None:

        return handle_stt_failure()

    if len(text.strip()) == 0:

        return handle_stt_failure()

    intent = classify_intent(text)

    if intent == INTENT_IPO:

        return get_ipo_info(text)

    if intent == INTENT_ADD:

        return add_schedule(text)

    if intent == INTENT_VIEW:

        return view_schedule(text)

    return handle_unknown()

# ==================================================
# 테스트
# ==================================================

tests = [

    "공모주 일정 등록해줘",

    "팀회의 등록",

    "내일 3시 등록",

    "이번주 공모주 알려줘",

    "오늘 공모주 청약 뭐 있어",

    "내일 오후 3시 팀회의 등록",

    "오늘 일정 알려줘",

    "오늘 날씨 어때",

    ""
]

for t in tests:

    print("=" * 60)

    print("입력:", t)

    print(
        process_user_command(t)
    )

    print()
