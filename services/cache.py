import hashlib
import time
from core.config import settings

# {cache_key: {"reply": str, "expires_at": float}}
_store: dict[str, dict] = {}


def _make_key(message: str) -> str:
    return hashlib.sha256(message.strip().encode()).hexdigest()


def get(message: str) -> str | None:
    key = _make_key(message)
    entry = _store.get(key)
    if entry and time.time() < entry["expires_at"]:
        return entry["reply"]
    if entry:
        del _store[key]
    return None


def set(message: str, reply: str) -> None:
    key = _make_key(message)
    _store[key] = {
        "reply": reply,
        "expires_at": time.time() + settings.cache_ttl_seconds,
    }


def stats() -> dict:
    now = time.time()
    alive = sum(1 for e in _store.values() if now < e["expires_at"])
    return {"total_entries": len(_store), "alive": alive}
