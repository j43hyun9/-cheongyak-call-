# TODO 장두호: 아래 SYSTEM_PROMPT를 페르소나 카드 완성 후 채워 넣을 것
SYSTEM_PROMPT = """\
당신은 공모주 투자 길잡이 콜비(Colby)입니다.
11살 어린이처럼 밝고 친근하게 설명하되, 코난처럼 날카로운 분석을 제공합니다.
공모주 청약 일정, 공모가, 주관사 정보 등을 알기 쉽게 안내합니다.
투자 권유나 수익 보장은 절대 하지 않으며, 정보 제공에만 집중합니다.
답변은 항상 한국어로 해주세요.
"""

_MAX_TURNS = 10  # 유지할 최대 대화 턴 수


def build_messages(
    history: list[dict],
    user_message: str,
    ipo_context: str = "",
) -> list[dict]:
    """
    Args:
        history: [{"role": "user"|"assistant", "content": str}, ...]
        user_message: 현재 사용자 메시지
        ipo_context: 크롤러에서 가져온 공모주 정보 문자열 (RAG 주입)

    Returns:
        OpenAI messages 형식 리스트
    """
    system = SYSTEM_PROMPT
    if ipo_context:
        system += f"\n\n[최신 공모주 정보]\n{ipo_context}"

    trimmed = history[-(_MAX_TURNS * 2):]  # user/assistant 쌍이므로 ×2
    return [
        {"role": "system", "content": system},
        *trimmed,
        {"role": "user", "content": user_message},
    ]
