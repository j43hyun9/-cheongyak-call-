import hashlib
import time
from backend.config import settings

_store: dict[str, dict] = {}


def _key(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()


def get(text: str) -> str | None:
    k = _key(text)
    entry = _store.get(k)
    if entry and time.time() < entry["exp"]:
        return entry["v"]
    if entry:
        del _store[k]
    return None


def set(text: str, value: str, ttl: int | None = None) -> None:
    k = _key(text)
    _store[k] = {"v": value, "exp": time.time() + (ttl or settings.cache_ttl_seconds)}


def stats() -> dict:
    now = time.time()
    alive = sum(1 for e in _store.values() if now < e["exp"])
    return {"total": len(_store), "alive": alive}
