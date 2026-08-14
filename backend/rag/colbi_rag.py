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

def _load_schedule_documents() -> list[Document]:
    items = asyncio.run(ipo_crawler.fetch_all_ipo())
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


def load_documents() -> list[Document]:
    return _load_schedule_documents() + _load_concept_documents()


# ── 2. 청킹 + 임베딩 + FAISS 인덱스 ────────────────────────────────────

def build_vectorstore() -> FAISS:
    raw_docs = load_documents()

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
    global _VECTORSTORE
    if _VECTORSTORE is None:
        _VECTORSTORE = build_vectorstore()
    return _VECTORSTORE


# ── 3. 검색 ────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = RETRIEVE_K) -> list[Document]:
    retriever = _get_vectorstore().as_retriever(search_kwargs={"k": k})
    return retriever.invoke(query)


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
    """
    history = history or []
    t0 = time.monotonic()

    docs = retrieve(message, k=RETRIEVE_K)
    ipo_context = _format_ipo_context(docs)

    # project2/backend/main.py의 컨벤션과 동일: 파인튜닝된 colbi-qwen에만 slim(few-shot 생략) 적용.
    # 대체 모델로 테스트할 땐 few-shot을 살려서 콜비 말투(2차와 동일한 예시)를 최대한 따라가게 한다.
    slim = OLLAMA_MODEL == "colbi-qwen"
    messages = colbi.build_messages(history, message, ipo_context=ipo_context, slim=slim)

    response = _client.chat.completions.create(model=OLLAMA_MODEL, messages=messages)

    latency_ms = int((time.monotonic() - t0) * 1000)
    usage = response.usage

    return {
        "answer_text": response.choices[0].message.content,
        "sources": _to_sources(docs),
        "state": "speaking",
        "usage": {
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        },
        "latency_ms": latency_ms,
    }
