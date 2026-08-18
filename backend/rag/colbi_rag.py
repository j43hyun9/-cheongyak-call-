"""
콜비 RAG 파이프라인 (F1·F2·F9 담당: 장두호)

흐름 (색인, 오프라인 1회):
  크롤러(fetch_all_ipo) + concepts.jsonl
    -> Document Loader -> Splitter(600/100) -> HuggingFaceEmbeddings(multilingual-MiniLM)
    -> FAISS Vector Store

흐름 (질의, 매 요청):
  질문 -> retriever(k=3) -> ipo_context 조립 -> colbi.build_messages(ipo_context=...)
    -> Ollama(colbi-qwen) -> answer_text + sources + state

backend/persona/colbi.py, backend/ipo_crawler.py를 그대로 import해서 쓴다
(페르소나 규칙·크롤러 로직 중복 금지).
"""

import asyncio
import json
import os
import time
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

from backend.persona import colbi
from backend import ipo_crawler

CONCEPTS_PATH = Path(__file__).parent / "concepts.jsonl"

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
RETRIEVE_K = 3

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "colbi-qwen")

NO_GUESS_RULE = "※ 아래 문서에 없는 내용은 추측하지 말고 '확인 안 됨'이라고 답해."

IPO_LISTING_URL = "http://www.38.co.kr/html/fund/?o=k"


# ── 1. 문서 로딩 (F1: 크롤러 / F2: 개념 문서) ──────────────────────────

def _load_schedule_documents(items: list[dict]) -> list[Document]:
    docs = []
    for item in items:
        text = (
            f"- {item['name']}: 청약기간 {item['start']}~{item['end']}, "
            f"공모가 {item['price']}, 주관사 {item['underwriter']}"
        )
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source_type": "schedule",
                    "title": item["name"],
                    "url": IPO_LISTING_URL,
                    "snippet": text,
                },
            )
        )
    return docs


def _load_concept_documents() -> list[Document]:
    docs = []
    with open(CONCEPTS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            snippet = row["text"][:80]
            docs.append(
                Document(
                    page_content=row["text"],
                    metadata={
                        "source_type": "concept",
                        "title": row["title"],
                        "url": f"internal://concepts/{row['id']}",
                        "snippet": snippet,
                    },
                )
            )
    return docs


def load_documents(schedule_items: list[dict]) -> list[Document]:
    return _load_schedule_documents(schedule_items) + _load_concept_documents()


# ── 2. 청킹 + 임베딩 + FAISS 인덱스 ────────────────────────────────────

def build_vectorstore(schedule_items: list[dict]) -> FAISS:
    raw_docs = load_documents(schedule_items)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    docs = splitter.split_documents(raw_docs)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    return FAISS.from_documents(docs, embedding=embeddings, distance_strategy=DistanceStrategy.COSINE)


_VECTORSTORE: FAISS | None = None


def _get_vectorstore() -> FAISS:
    """
    지연 로드 폴백. FastAPI 서버에서는 init_index()가 lifespan에서 미리 채워두므로
    이 경로를 안 타고, demo.py 같은 단발성 스크립트 컨텍스트에서만 여기서 로드한다.
    (asyncio.run은 이미 실행 중인 이벤트 루프 안에서는 못 쓰므로, 서버 요청 처리 중엔
    반드시 init_index()로 미리 채워둔 인덱스를 재사용해야 한다.)
    """
    global _VECTORSTORE
    if _VECTORSTORE is None:
        items = asyncio.run(ipo_crawler.fetch_all_ipo())
        _VECTORSTORE = build_vectorstore(items)
    return _VECTORSTORE


async def init_index() -> None:
    """앱 시작 시 1회 호출해 FAISS 인덱스를 미리 로드한다(backend/main.py의 lifespan에서 사용)."""
    global _VECTORSTORE
    items = await ipo_crawler.fetch_all_ipo()
    _VECTORSTORE = build_vectorstore(items)


# ── 3. 검색 ────────────────────────────────────────────────────────────

def _search_documents(query: str, k: int = RETRIEVE_K) -> list[Document]:
    retriever = _get_vectorstore().as_retriever(search_kwargs={"k": k})
    return retriever.invoke(query)


def retrieve(query: str, k: int = RETRIEVE_K) -> tuple[str, list[dict]]:
    """
    RAG 검색 전용 공개 API (LLM 호출 없음).

    /chat(backend/main.py)에서 build_messages(ipo_context=context)로 그대로 주입하고,
    sources는 응답 필드로 그대로 반환한다. 검색 결과가 없으면 context=""를 반환하며,
    이 경우 콜비는 "모른다"고 답한다(빈 ipo_context는 build_messages가 이미 그렇게 처리).
    """
    docs = _search_documents(query, k=k)
    return _format_ipo_context(docs), _to_sources(docs)


def _format_ipo_context(docs: list[Document]) -> str:
    if not docs:
        return ""
    body = "\n".join(d.page_content for d in docs)
    return f"{NO_GUESS_RULE}\n{body}"


def _to_sources(docs: list[Document]) -> list[dict]:
    return [
        {
            "title": d.metadata["title"],
            "snippet": d.metadata["snippet"],
            "type": d.metadata["source_type"],
            "url": d.metadata["url"],
        }
        for d in docs
    ]


# ── 4. 생성 + 응답 조립 ─────────────────────────────────────────────────

_client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    default_headers={"ngrok-skip-browser-warning": "true"},  # ngrok 터널 경유 시 경고 인터스티셜 우회, 로컬 직결 시엔 무해
)


def ask_colbi(message: str, history: list[dict] | None = None) -> dict:
    """
    /chat 계약 v1 중 내(장두호) 담당 필드만 채워서 반환한다.
    {answer_text, sources, state, usage, latency_ms} — audio_url은 TTS 담당 몫이라 비움.

    데모(demo.py)·페르소나 톤 검증 전용. 실제 backend/main.py의 /chat은
    retrieve()로 검색만 하고 LLM 호출은 backend/llm.py의 call_llm()로 하므로
    (Ollama 중복 호출 방지), 이 함수를 호출하지 않는다.
    """
    history = history or []
    t0 = time.monotonic()

    ipo_context, sources = retrieve(message, k=RETRIEVE_K)

    # project2/backend/main.py의 컨벤션과 동일: 파인튜닝된 colbi-qwen에만 slim(few-shot 생략) 적용.
    # 대체 모델로 테스트할 땐 few-shot을 살려서 콜비 말투(2차와 동일한 예시)를 최대한 따라가게 한다.
    slim = OLLAMA_MODEL == "colbi-qwen"
    messages = colbi.build_messages(history, message, ipo_context=ipo_context, slim=slim)

    response = _client.chat.completions.create(model=OLLAMA_MODEL, messages=messages)

    latency_ms = int((time.monotonic() - t0) * 1000)
    usage = response.usage

    return {
        "answer_text": response.choices[0].message.content,
        "sources": sources,
        "state": "speaking",
        "usage": {
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        },
        "latency_ms": latency_ms,
    }
