import json
import os
from datetime import datetime

SCHEDULE_FILE = "schedules.json"


def _load_all() -> list:
    if not os.path.exists(SCHEDULE_FILE):
        return []
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: list) -> None:
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_schedule(title: str, dt: datetime) -> dict:
    data = _load_all()
    entry = {"title": title, "datetime": dt.isoformat()}
    data.append(entry)
    _save_all(data)
    return entry


def load_schedule(target_date: datetime) -> list:
    data = _load_all()
    target_str = target_date.date().isoformat()
    return [
        item for item in data
        if item["datetime"].startswith(target_str)
    ]


if __name__ == "__main__":
    from datetime import datetime

    save_schedule("청약 신청 마감", datetime(2026, 6, 5, 18, 0))
    save_schedule("서류 제출", datetime(2026, 6, 5, 9, 0))

    results = load_schedule(datetime(2026, 6, 5))
    for r in results:
        print(r)
