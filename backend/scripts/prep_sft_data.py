"""
콜비 어투 SFT 데이터 전처리 — QLoRA 학습용 train/val 분리
입력: data/colbi_sft*.jsonl (train/val 산출물 파일 자체는 제외)
출력: data/colbi_sft_train.jsonl, data/colbi_sft_val.jsonl

절차: 포맷 검증 → dedup(질문 기준) → eval/evalset.csv 30문항 held-out 제외 → train/val 분리

실행: python -m backend.scripts.prep_sft_data
"""
import argparse
import csv
import json
import random
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_NAMES = {"colbi_sft_train.jsonl", "colbi_sft_val.jsonl"}


def normalize(text: str) -> str:
    """공백·구두점 차이를 무시하고 비교하기 위한 정규화 키."""
    return re.sub(r"[^\w]", "", text)


def load_eval_questions(eval_csv: Path) -> set[str]:
    if not eval_csv.exists():
        return set()
    with eval_csv.open(encoding="utf-8-sig", newline="") as f:
        return {normalize(row["question"]) for row in csv.DictReader(f) if row.get("question")}


def find_question(messages: list[dict]) -> str | None:
    """마지막 assistant 답변 바로 앞의 user 메시지를 '질문'으로 간주."""
    last_assistant = None
    for i, m in enumerate(messages):
        if m.get("role") == "assistant":
            last_assistant = i
    if last_assistant is None:
        return None
    for m in reversed(messages[:last_assistant]):
        if m.get("role") == "user":
            return m.get("content")
    return None


def validate(obj: dict) -> tuple[bool, str]:
    messages = obj.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return False, "messages 누락 또는 2개 미만"
    for m in messages:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            return False, "role은 user/assistant만 허용"
        if not isinstance(m.get("content"), str) or not m["content"].strip():
            return False, "content가 비어 있음"
    if messages[-1]["role"] != "assistant":
        return False, "마지막 메시지가 assistant가 아님"
    if find_question(messages) is None:
        return False, "직전 user 메시지를 찾을 수 없음"
    return True, ""


def load_examples(input_glob: str) -> list[dict]:
    examples = []
    for path in sorted(REPO_ROOT.glob(input_glob)):
        if path.name in OUTPUT_NAMES:
            continue
        with path.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  [스킵] {path.name}:{lineno} JSON 파싱 실패 — {e}")
                    continue
                obj["_source"] = path.name
                obj["_lineno"] = lineno
                examples.append(obj)
    return examples


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="data/colbi_sft*.jsonl", help="입력 JSONL glob 패턴 (repo 루트 기준)")
    ap.add_argument("--eval-csv", default="eval/evalset.csv", help="held-out 평가셋 CSV 경로 (repo 루트 기준)")
    ap.add_argument("--out-dir", default="data", help="출력 디렉토리 (repo 루트 기준)")
    ap.add_argument("--val-ratio", type=float, default=0.1, help="검증셋 비율 (기본 0.1)")
    ap.add_argument("--seed", type=int, default=42, help="train/val 분리용 셔플 시드")
    args = ap.parse_args()

    raw = load_examples(args.input)
    print(f"읽은 원본 예제: {len(raw)}건")

    valid, invalid = [], 0
    for obj in raw:
        ok, reason = validate(obj)
        if not ok:
            invalid += 1
            print(f"  [무효] {obj['_source']}:{obj['_lineno']} — {reason}")
            continue
        valid.append(obj)
    print(f"포맷 검증 통과: {len(valid)}건 (무효 {invalid}건 제외)")

    seen: set[str] = set()
    deduped = []
    dup_count = 0
    for obj in valid:
        key = normalize(find_question(obj["messages"]))
        if key in seen:
            dup_count += 1
            continue
        seen.add(key)
        deduped.append(obj)
    print(f"dedup 후: {len(deduped)}건 (중복 {dup_count}건 제외)")

    eval_questions = load_eval_questions(REPO_ROOT / args.eval_csv)
    kept = []
    heldout_count = 0
    for obj in deduped:
        key = normalize(find_question(obj["messages"]))
        if key in eval_questions:
            heldout_count += 1
            continue
        kept.append(obj)
    print(f"held-out 평가셋({len(eval_questions)}문항) 제외 후: {len(kept)}건 (제외 {heldout_count}건)")

    rng = random.Random(args.seed)
    shuffled = kept[:]
    rng.shuffle(shuffled)
    val_size = round(len(shuffled) * args.val_ratio)
    val_set = shuffled[:val_size]
    train_set = shuffled[val_size:]

    out_dir = REPO_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "colbi_sft_train.jsonl"
    val_path = out_dir / "colbi_sft_val.jsonl"

    for path, dataset in ((train_path, train_set), (val_path, val_set)):
        with path.open("w", encoding="utf-8") as f:
            for obj in dataset:
                clean = {"messages": obj["messages"]}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    print(f"\n최종: train {len(train_set)}건 → {train_path.relative_to(REPO_ROOT)}")
    print(f"      val   {len(val_set)}건 → {val_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
