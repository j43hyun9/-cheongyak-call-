#공모주 조회 및 미지원 출력 테스트용 코드 (6/4, I-01,02 확인 / 6/5, N-02,03,05 확인)
#공모주 조회에서 미지원 문구 처리 추가 및 출력 테스트 진행
#같은 폴더내에 crawl_ipo.py 필수 

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

    # 일정등록 우선
    if any(k in text for k in [
        "등록",
        "추가",
        "예약",
        "저장"
    ]):
        return INTENT_ADD

    # 공모주 조회
    if any(k in text for k in [
        "공모주",
        "ipo",
        "청약"
    ]):
        return INTENT_IPO

    # 일정 조회
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

# 1. 코드 맨 상단에 질문자님이 만든 크롤러 파일에서 함수들을 가져옵니다.
from crawl_ipo import fetch_ipo, ipo_today, ipo_week, ipo_next_week

# ... (중간 어댑터나 일정 등록 코드는 그대로 유지) ...

# 2. 기존의 가짜 하드코딩 함수를 진짜 필터 함수와 연동하도록 수정합니다.
def get_ipo_info(text):

    # 🚨 [바뀐 부분] N-05 알림 및 구독 미구현 기능 요청 시 시스템 공통 미지원 문구로 리턴
    if any(k in text for k in ["알림", "구독", "설정"]):
        return handle_unknown()  # "아직 지원하지 않는 명령이에요." 리턴
    
    # 1. 크롤러를 통해 실시간 데이터(또는 캐시) 확보
    ipo_list = fetch_ipo(force_refresh=False)
    
    # 2. 기획서 시나리오 테스트용 당일 기준 날짜 세팅 
    # (실제 서비스 시에는 datetime.today().strftime("%Y-%m-%d") 사용)
    mock_today = "2026-06-16" 

    # ──────────────────────────────────────────────────
    # [시나리오 1] "오늘" 공모주 청약 요청 시
    # ──────────────────────────────────────────────────
    if "오늘" in text:
        today_items = ipo_today(ipo_list, mock_today)
        if not today_items:
            return "오늘 진행중인 공모주가 없습니다."
            
        result = "[오늘 공모주 청약 일정]\n\n"
        for i, ipo in enumerate(today_items):
            result += (
                f"{i+1}. {ipo['name']}\n"
                f"청약기간: {ipo['start']} ~ {ipo['end']}\n"
                f"공모가: {ipo['price']}원\n"
                f"주관사: {ipo['underwriter']}\n\n"
            )
        return result

    # ──────────────────────────────────────────────────
    # [시나리오 2] "다음주" 공모주 청약 요청 시 (★순서 중요: '이번주'보다 먼저 체크해야 함)
    # ──────────────────────────────────────────────────
    if "다음주" in text or "다음 주" in text:
        next_week_items = ipo_next_week(ipo_list, mock_today)
        if not next_week_items:
            return "다음 주 진행 예정인 공모주 청약 일정이 없습니다."
            
        result = "[다음주 공모주 예정 일정]\n\n"
        for i, ipo in enumerate(next_week_items):
            result += (
                f"{i+1}. {ipo['name']}\n"
                f"청약기간: {ipo['start']} ~ {ipo['end']}\n"
                f"공모가: {ipo['price']}원\n"
                f"주관사: {ipo['underwriter']}\n\n"
            )
        return result

    # ──────────────────────────────────────────────────
    # [시나리오 3] "이번주" 공모주 청약 요청 시
    # ──────────────────────────────────────────────────
    if "이번주" in text or "이번 주" in text:
        week_items = ipo_week(ipo_list, mock_today)
        if not week_items:
            return "이번 주 진행 중인 공모주 청약 일정이 없습니다."
            
        result = "[이번주 공모주 진행 일정]\n\n"
        for i, ipo in enumerate(week_items):
            result += (
                f"{i+1}. {ipo['name']}\n"
                f"청약기간: {ipo['start']} ~ {ipo['end']}\n"
                f"공모가: {ipo['price']}원\n"
                f"주관사: {ipo['underwriter']}\n\n"
            )
        return result

    # ──────────────────────────────────────────────────
    # [기본값] 그 외 일반 공모주 전체 요청 시
    # ──────────────────────────────────────────────────
    result = "[공모주 전체 목록]\n\n"
    for i, ipo in enumerate(ipo_list):
        result += (
            f"{i+1}. {ipo['name']}\n"
            f"청약기간: {ipo['start']} ~ {ipo['end']}\n"
            f"공모가: {ipo['price']}원\n"
            f"주관사: {ipo['underwriter']}\n\n"
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

    "다음주 공모주 알려줘",

    "내일 오후 3시 팀회의 등록",

    "오늘 일정 알려줘",

    "오늘 날씨 어때",

    # 테스트 문구 추가 (N-02,03,05 확인용)
    "내일 팀회의 삭제해줘",

    "팀회의 4시로 변경",

    "레메디 청약 알림 설정",

    ""
]

for t in tests:

    print("=" * 60)

    print("입력:", t)

    print(
        process_user_command(t)
    )

    print()
