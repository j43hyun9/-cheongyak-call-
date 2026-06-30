from contextlib import asynccontextmanager
from fastapi import FastAPI
from db.database import init_db
from api.chat import router as chat_router
from api.logs import router as logs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="콜비(Colby) AI 백엔드",
    description="공모주 투자 길잡이 콜비 — 팀C 2차 프로젝트",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat_router)
app.include_router(logs_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
