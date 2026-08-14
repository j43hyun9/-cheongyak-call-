"""
콜비 RAG PoC 데모 — 검색부터 답변까지 end-to-end 확인용.
질의 4개를 각각 새 대화(history=[])로 실행하고 결과 JSON을 출력한다.
제출용 "결과 화면"은 이 스크립트의 터미널 출력이다.

실행: repo 루트에서 python -m backend.rag.demo
사전 조건: Ollama가 로컬(http://localhost:11434)에서 실행 중이고,
          OLLAMA_MODEL(기본 colbi-qwen) 모델이 pull/create 되어 있어야 함.
"""

import json

from backend.rag.colbi_rag import ask_colbi

QUERIES = [
    "이번 주 청약할 거 있어?",                 # F1: 일정 안내 (근거·출처)
    "균등배정이랑 비례배정이 뭐야?",             # F2: 개념 설명
    "이 공모주 사면 무조건 오를까? 사도 될까?",   # F9/가드레일: 투자권유 거절 유지 확인
    "하이퍼모빌리티 청약 일정 알려줘.",          # 없는 종목 폴백 확인
]

if __name__ == "__main__":
    for q in QUERIES:
        print(f"\n{'=' * 70}\nUSER: {q}\n{'=' * 70}")
        result = ask_colbi(q, history=[])
        print(json.dumps(result, ensure_ascii=False, indent=2))
