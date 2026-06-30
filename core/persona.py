# ──────────────────────────────────────────────────────────
# 콜비(Colby) 페르소나 시스템 프롬프트
# 담당: 장두호 (AI 엔지니어)
#
# 이 파일은 장두호가 채워 넣는 인계점입니다.
# 임강은 get_system_prompt() 반환값을 LLM 호출에 그대로 사용하면 됩니다.
# ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
당신은 공모주 투자 길잡이 콜비(Colby)입니다.
[TODO: 장두호가 페르소나 카드 완성 후 채워 넣을 것]
"""

# RAG 주입 슬롯 — 크롤러 데이터를 받아 프롬프트에 붙이는 지점
# 장두호가 ipo_context 포맷을 확정하면 이 함수에서 처리
def get_system_prompt(ipo_context: str = "") -> str:
    if ipo_context:
        return _SYSTEM_PROMPT + f"\n\n[최신 공모주 정보]\n{ipo_context}"
    return _SYSTEM_PROMPT
