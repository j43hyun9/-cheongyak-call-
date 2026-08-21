"""
backend/persona/sanitize.py

콜비(Colbi) 응답 후처리.
colbi-qwen(로컬 파인튜닝 모델)이 시스템 프롬프트에서 이모지를 금지해도
계속 이모지·정형화된 오프닝/클로징을 출력하는 것을 실측으로 확인했다
(2026-08-21). 프롬프트만으로는 억제되지 않으므로, 이 모듈이 answer_text에
대한 최종 방어선이다 — /chat이 응답을 반환·캐시·기록하기 직전에 항상
거쳐야 한다.
"""

from __future__ import annotations

import re

# 이모지 유니코드 블록 + 결합용 불가시 문자(VS16, ZWJ).
# 한글·영문·숫자·일반 문장부호(마침표·쉼표·물음표·가운뎃점 등)는 이 범위 밖이라
# 영향받지 않는다.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE0F"
    "\U0000200D"
    "]+"
)

# v6 파인튜닝 데이터셋에 박힌 고정 오프닝/클로징(docs/페르소나_카드.md에 문서화된
# 5종 + 실측에서 확인된 변형). 원래 설계상 "단서 발견!"·"수사 개시!" 등은
# 오프닝, "사건 해결!"·"진실은 하나야!"는 클로징 전용이지만, colbi-qwen은
# 실제로 이 구분을 지키지 않고 아무 위치에나 섞어 쓴다(예: "수사 개시!"가
# 문미 클로징으로 나온 사례 실측 확인, 2026-08-21) — 그래서 오프닝/클로징을
# 구분하지 않고 문두·문미 양쪽에서 전부 검사한다. 문장 "중간"에서 자연스럽게
# 쓰이는 단서·사건·수사·증거는 건드리지 않도록, 문두/문미에 정확히 그
# 문구로 시작·끝날 때만 제거한다(앵커링).
_FIXED_PHRASES = [
    "단서 발견!",
    "내 파일에 없어...",
    "내 파일에 없어…",
    "그 단서는 못 줘.",
    "수사 개시!",
    "사건 해결!",
    "진실은 하나야!",
]

_HSPACE_RE = re.compile(r"[ \t]+")


def strip_persona_artifacts(text: str) -> str:
    """이모지와 파인튜닝 고정 멘트를 제거하고 공백을 정리해 반환한다.

    문단 구분(빈 줄)은 보존하고, 이모지 제거로 생기는 연속 공백만 한 칸으로
    줄인다. 고정 멘트는 문두/문미에 정확히 일치할 때만 제거하며(앵커링),
    한쪽 끝에 여러 개가 연달아 붙어 나오는 경우까지 대비해 더 이상 안
    빠질 때까지 반복 제거한다.
    """
    if not text:
        return text

    cleaned = _EMOJI_RE.sub("", text).strip()

    changed = True
    while changed:
        changed = False
        for phrase in _FIXED_PHRASES:
            if cleaned.startswith(phrase):
                cleaned = cleaned[len(phrase):].lstrip()
                changed = True
                break

    changed = True
    while changed:
        changed = False
        for phrase in _FIXED_PHRASES:
            if cleaned.endswith(phrase):
                cleaned = cleaned[: -len(phrase)].rstrip()
                changed = True
                break

    cleaned = _HSPACE_RE.sub(" ", cleaned)
    return cleaned.strip()
