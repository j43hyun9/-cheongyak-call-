"""
HeyGen으로 speaking 프레임 재생성 — idle과 동일 위치/크기로 처리
실행: python tools/regen_speaking_frames.py
"""
import asyncio
import base64
import io
import os
import uuid
from pathlib import Path

import cv2
import httpx
import numpy as np
from PIL import Image
from rembg import remove
from dotenv import load_dotenv

load_dotenv()

# ── 경로 ──────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
ASSETS = ROOT / "frontend" / "src" / "assets" / "colby"
IDLE   = ASSETS / "colby-idle.png"
TMP    = ROOT / "tools" / "_tmp_heygen"
TMP.mkdir(exist_ok=True)

HEYGEN_BASE = "https://api.heygen.com"
HEYGEN_KEY  = os.getenv("HEYGEN_API_KEY", "")

# ── 처리 설정 ──────────────────────────────────────────────────────
# HeyGen 출력 설정: 1:1+720p → 720×720, 입력 idle과 동일 비율
HEYGEN_ASPECT   = "1:1"
HEYGEN_RESOLUTION = "720p"
# 프레임 샘플: 영상 전체에서 이 개수만 균등 추출 → rembg 처리 최소화
SAMPLE_FRAMES   = 25

# ── idle 캐릭터 정확한 bounds (측정값) ────────────────────────────
IDLE_CHAR = dict(x=105, y=0, w=523, h=719)
CANVAS    = 720

# ── 9개 phoneme 출력 파일명 ────────────────────────────────────────
PHONEME_FILES = {
    "closed":  "colby-speaking-closed.png",
    "open":    "colby-speaking-open.png",
    "wide":    "colby-speaking-wide.png",
    "ae":      "colby-speaking-ae.png",
    "eo":      "colby-speaking-eo.png",
    "eu":      "colby-speaking-eu.png",
    "half":    "colby-speaking-half.png",
    "round":   "colby-speaking-round.png",
    "pucker":  "colby-speaking-pucker.png",
}

# ── TTS 음성 생성 ─────────────────────────────────────────────────
async def make_audio() -> bytes:
    import edge_tts
    # 한국어 모든 모음을 포함하는 문장
    text = (
        "안녕하세요. 저는 공모주 전문 AI 비서 콜비입니다. "
        "투자 전 꼭 공시 서류를 확인해 주세요. "
        "궁금한 점이 있으면 편하게 물어보세요."
    )
    communicate = edge_tts.Communicate(text, "ko-KR-HyunsuMultilingualNeural", pitch="+20Hz")
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    audio_bytes = buf.getvalue()
    print(f"[TTS] 오디오 생성: {len(audio_bytes):,} bytes")
    return audio_bytes


# ── HeyGen API ────────────────────────────────────────────────────
async def heygen_generate(audio_bytes: bytes) -> bytes:
    if not HEYGEN_KEY:
        raise RuntimeError("HEYGEN_API_KEY 환경변수 미설정")

    headers = {"X-Api-Key": HEYGEN_KEY}
    run_id  = str(uuid.uuid4())[:8]

    async with httpx.AsyncClient(timeout=90) as client:
        # 1. 오디오 업로드
        resp = await client.post(
            f"{HEYGEN_BASE}/v3/assets",
            headers=headers,
            files={"file": (f"colby_{run_id}.mp3", audio_bytes, "audio/mpeg")},
        )
        resp.raise_for_status()
        audio_id = resp.json()["data"]["asset_id"]
        print(f"[HeyGen] 오디오 업로드 완료: {audio_id}")

        # 2. 영상 생성 요청
        img_b64 = base64.b64encode(IDLE.read_bytes()).decode()
        resp = await client.post(
            f"{HEYGEN_BASE}/v3/videos",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "type": "image",
                "image": {"type": "base64", "data": img_b64, "media_type": "image/png"},
                "audio_asset_id": audio_id,
                "expressiveness": "high",
                "aspect_ratio": HEYGEN_ASPECT,
                "resolution": HEYGEN_RESOLUTION,
            },
        )
        resp.raise_for_status()
        video_id = resp.json()["data"]["video_id"]
        print(f"[HeyGen] 생성 요청: {video_id}")

        # 3. 폴링
        video_url = None
        for i in range(36):
            await asyncio.sleep(5)
            poll = await client.get(f"{HEYGEN_BASE}/v3/videos/{video_id}", headers=headers)
            data   = poll.json().get("data", {})
            status = data.get("status")
            print(f"[HeyGen] 폴링 {i+1}/36: {status}")
            if status == "completed":
                video_url = data["video_url"]
                break
            elif status == "failed":
                raise RuntimeError(f"HeyGen 실패: {data}")
        else:
            raise RuntimeError("HeyGen 타임아웃 (3분)")

        # 4. mp4 다운로드
        dl = await client.get(video_url, timeout=120)
        dl.raise_for_status()
        video_bytes = dl.content
        print(f"[HeyGen] 다운로드 완료: {len(video_bytes):,} bytes")
        return video_bytes


# ── 프레임 처리 ───────────────────────────────────────────────────
def process_frame(frame_bgr: np.ndarray) -> Image.Image | None:
    """
    1. rembg 배경 제거
    2. 캐릭터 bounds 찾기
    3. idle 캐릭터 영역(523×719)에 맞게 리사이즈
    4. 720×720 캔버스 (105, 0)에 paste
    """
    # BGR → RGBA PIL
    img_rgba = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA))
    img_rembg: Image.Image = remove(img_rgba)

    arr   = np.array(img_rembg)
    alpha = arr[:, :, 3]
    rows  = np.any(alpha > 10, axis=1)
    cols  = np.any(alpha > 10, axis=0)
    if not rows.any():
        return None

    y_top = int(np.argmax(rows))
    y_bot = int(len(rows) - np.argmax(rows[::-1]) - 1)
    x_l   = int(np.argmax(cols))
    x_r   = int(len(cols) - np.argmax(cols[::-1]) - 1)

    # 캐릭터 영역 crop
    char_crop = img_rembg.crop((x_l, y_top, x_r + 1, y_bot + 1))

    # idle 사이즈(523×719)로 리사이즈 — 가로/세로 모두 idle 기준
    char_resized = char_crop.resize(
        (IDLE_CHAR["w"], IDLE_CHAR["h"]),
        Image.LANCZOS,
    )

    # 720×720 투명 캔버스에 (105, 0) 배치
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(char_resized, (IDLE_CHAR["x"], IDLE_CHAR["y"]))
    return canvas


# ── 9개 대표 프레임 자동 선택 ─────────────────────────────────────
def auto_select_frames(processed: list[tuple[int, Image.Image]]) -> dict[str, int]:
    """
    프레임별 '입 열림 정도'를 분석해 9가지 phoneme에 대표 프레임 할당.
    방법: 각 프레임에서 캐릭터 y=50%~75% 영역(입 위치 추정)의 밝기 변동 측정.
    """
    scores = []
    for idx, (frame_no, pil) in enumerate(processed):
        arr = np.array(pil.convert("L"))
        h   = arr.shape[0]
        # 캐릭터 높이 기준 50~75% 구간 (입 영역 추정)
        mouth_region = arr[int(h * 0.50): int(h * 0.75), :]
        scores.append((idx, float(np.std(mouth_region))))

    scores.sort(key=lambda x: x[1])  # 낮을수록 닫힘

    n      = len(scores)
    step   = max(1, n // 9)
    chosen = [scores[min(i * step, n - 1)][0] for i in range(9)]

    keys = list(PHONEME_FILES.keys())
    return {keys[i]: processed[chosen[i]][0] for i in range(9)}


# ── 메인 ─────────────────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("speaking 프레임 재생성 (idle 사이즈 기준)")
    print("=" * 60)

    # 1. TTS 오디오
    audio_bytes = await make_audio()
    audio_path  = TMP / "colby_tts.mp3"
    audio_path.write_bytes(audio_bytes)

    # 2. HeyGen 영상 생성
    video_bytes = await heygen_generate(audio_bytes)
    video_path  = TMP / "heygen_output.mp4"
    video_path.write_bytes(video_bytes)
    print(f"[저장] {video_path}")

    # 3. 프레임 추출
    cap   = cv2.VideoCapture(str(video_path))
    fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[영상] {fps:.1f}fps × {total}프레임 ({total/fps:.1f}초)")

    # 4. 균등 샘플 추출 후 처리 (rembg CPU 처리 최소화)
    # 첫 10%와 마지막 10% 제외 (정지/페이드 구간 회피), 중간 구간에서 균등 샘플
    start_f = max(0, int(total * 0.08))
    end_f   = min(total - 1, int(total * 0.90))
    sample_indices = [
        int(start_f + (end_f - start_f) * i / (SAMPLE_FRAMES - 1))
        for i in range(SAMPLE_FRAMES)
    ]
    print(f"[샘플] {len(sample_indices)}개 프레임 처리 (frame {sample_indices[0]}~{sample_indices[-1]})")

    processed: list[tuple[int, Image.Image]] = []
    for i, target in enumerate(sample_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        ret, frame = cap.read()
        if not ret:
            continue
        print(f"  rembg 처리 중: {i+1}/{len(sample_indices)} (frame {target})")
        result = process_frame(frame)
        if result:
            processed.append((target, result))
    cap.release()
    print(f"[처리 완료] {len(processed)}개 프레임")

    if len(processed) < 9:
        raise RuntimeError(f"유효 프레임이 너무 적음: {len(processed)}")

    # 5. 모든 처리된 프레임 tmp 저장 (검토용)
    frames_dir = TMP / "frames"
    frames_dir.mkdir(exist_ok=True)
    for frame_no, pil in processed:
        pil.save(frames_dir / f"frame_{frame_no:04d}.png")
    print(f"[검토용] {frames_dir} 에 {len(processed)}개 저장")

    # 6. 9개 대표 프레임 자동 선택
    selection = auto_select_frames(processed)
    print("\n[자동 선택]")
    for phoneme, fno in selection.items():
        print(f"  {phoneme:10s} ← frame {fno:04d}")

    # 7. 에셋 폴더에 저장
    print("\n[에셋 저장]")
    for phoneme, fno in selection.items():
        out_name = PHONEME_FILES[phoneme]
        out_path = ASSETS / out_name
        # processed 중 fno에 해당하는 이미지 찾기
        pil = next(p for n, p in processed if n == fno)
        pil.save(out_path, "PNG")

        # 검증
        arr   = np.array(pil.convert("RGBA"))[:, :, 3]
        rows  = np.any(arr > 10, axis=1)
        cols  = np.any(arr > 10, axis=0)
        y_bot = int(len(rows) - np.argmax(rows[::-1]) - 1)
        x_r   = int(len(cols) - np.argmax(cols[::-1]) - 1)
        x_l   = int(np.argmax(cols))
        print(f"  {out_name}: char x={x_l}~{x_r}({x_r-x_l}px) y=0~{y_bot}({y_bot}px) [idle: x=105~628(523) y=0~719(719)]")

    print("\n완료! 브라우저에서 확인하세요.")


if __name__ == "__main__":
    asyncio.run(main())
