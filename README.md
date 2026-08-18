# 청약콜 — 콜비(Colbi) 🔍

> 공모주 안내 **페르소나 챗봇** — 사전학습 LLM(Qwen2.5-7B)에 "11살 꼬마 탐정 콜비"의 어투를 **QLoRA 파인튜닝**으로 학습시킨 AI 답변 시스템.
> ESTSOFT AI휴먼 5기 2차 팀 프로젝트 · Team C

공식 주제 **"거대 언어 모델을 활용한 PERSO AI 답변 기능 구현"** 의 구현 사례. 1차(공모주 음성비서) 도메인을 계승.

---

## ✨ 특징
- **페르소나 파인튜닝**: 공개 데이터에 없는 캐릭터 어투를 합성 데이터로 만들어 QLoRA 학습 (프롬프트가 아닌 모델 내재화)
- **가드레일**: 투자 권유·수익 보장·주가 예측 거절 → "최종 결정은 본인 몫이야! 💪"
- **할루시네이션 방지**: 없는 종목/일정은 지어내지 않고 "내 파일에 없어 🗂️" / 캘린더 유도
- **웹 챗 + 공모주 캘린더 + 일정 CRUD**

## 🏗️ 아키텍처
```
브라우저(React) → 백엔드(FastAPI /chat) → 파인튜닝 모델(Ollama, local 엔진) → 응답
                                   ├ 공모주 크롤러(38.co.kr) → /ipo/schedule (캘린더)
                                   └ SQLite (대화 이력·일정·호출 로그)
```

## 🧰 기술 스택
| 영역 | 스택 |
|------|------|
| 모델 | Qwen2.5-7B-Instruct · QLoRA(Unsloth) · GGUF(q8_0) · Ollama |
| 백엔드 | Python 3.11 · FastAPI · SQLite(aiosqlite) · BeautifulSoup4 |
| 프론트 | React · Vite · FullCalendar |
| 평가 | LLM-as-Judge(GPT-4o) · 5축 루브릭 |

## 📁 구조
```
backend/    FastAPI (main·llm·db·cache·ipo_crawler·persona/colbi)
frontend/   React 챗 UI + 캘린더
data/       colbi_sft.jsonl (어투 데이터 200건)
eval/       평가셋·루브릭·LLM-judge 하네스·리포트
notebooks/  colbi_qlora_finetune.ipynb (학습 파이프라인)
```

## 🚀 실행 (로컬)
**1) 모델 서빙 (Ollama)**
```bash
ollama create colbi-qwen -f Modelfile   # GGUF + Modelfile 준비 후
```
**2) 백엔드**
```bash
# .env: LLM_ENGINE=local, OLLAMA_MODEL=colbi-qwen
uvicorn backend.main:app --reload --port 8000
```
**3) 프론트**
```bash
cd frontend && npm install && npm run dev   # http://localhost:3000
```

## 🎓 파인튜닝 파이프라인
1. **데이터**: 콜비 어투 Q&A 200건 (few-shot·페르소나 시드 → LLM 증강 → 검수, held-out 30 분리)
2. **학습**: Qwen2.5-7B에 QLoRA(4bit), Unsloth, 3 epoch, assistant 응답만 학습 → `notebooks/colbi_qlora_finetune.ipynb`
3. **서빙**: 어댑터 병합 → GGUF(q8_0) → Ollama(temperature 0.4)
4. **평가**: `python eval/run_judge_eval.py`

## 📊 평가 결과 (held-out 30문항 × 5축, LLM-as-Judge)
| 페르소나 | 어투 | 가드레일 | 사실성 | 응답품질 | 종합 |
|:--:|:--:|:--:|:--:|:--:|:--:|
| 5.0 | 5.0 | 5.0 | 4.87 | 4.87 | **PASS 30/30** |

상세: [`eval/report.md`](eval/report.md)

## 👥 Team C
| 이름 | 역할 |
|------|------|
| 전재형 | 기획·데이터·학습·평가·총괄 |
| 장두호 | 어투 데이터셋·페르소나 |
| 임강 | 백엔드·서빙(Ollama 연동) |
| 김준서 | DB·세션·크롤러/일정 API |
| 백승옥 | 프론트(챗 UI·캘린더) |

## ⚠️ 범위·한계
- RAG(실시간 크롤링 주입)는 **프로젝트3 범위**로 분리 → 2차는 어투 파인튜닝에 집중
- 로컬 CPU 서빙 지연 · 단일 PC 데모(ngrok) → 상시 서비스는 클라우드 GPU 필요
