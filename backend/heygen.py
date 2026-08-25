"""
HeyGen Audio to Video 연동 모듈
이미지 1장 + TTS 오디오 → 립싱크 영상(.mp4) 생성
"""
import asyncio
import base64
import uuid
from pathlib import Path

import httpx

from backend.config import settings

HEYGEN_BASE = "https://api.heygen.com"

COLBY_IMAGE_SRC = (
    Path(__file__).parent.parent / "frontend" / "src" / "assets" / "colby" / "colby-idle.png"
)
PUBLIC_OUT = Path(__file__).parent.parent / "frontend" / "public" / "sadtalker_output"
PUBLIC_OUT.mkdir(parents=True, exist_ok=True)


def _auth_header() -> dict:
    return {"X-Api-Key": settings.heygen_api_key}


def _image_b64() -> str:
    with open(COLBY_IMAGE_SRC, "rb") as f:
        return base64.b64encode(f.read()).decode()


async def _upload_audio(client: httpx.AsyncClient, audio_bytes: bytes, run_id: str) -> str:
    """오디오를 HeyGen /v3/assets 에 업로드하고 asset_id 반환"""
    resp = await client.post(
        f"{HEYGEN_BASE}/v3/assets",
        headers=_auth_header(),
        files={"file": (f"audio_{run_id}.mp3", audio_bytes, "audio/mpeg")},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    asset_id = data.get("data", {}).get("asset_id") or data.get("asset_id")
    if not asset_id:
        raise ValueError(f"asset_id 없음: {data}")
    return asset_id


async def generate_lipsync(audio_bytes: bytes) -> str | None:
    """
    audio_bytes: mp3 바이너리 (edge-tts 출력)
    returns: /sadtalker_output/heygen_xxx.mp4 또는 None(실패)
    """
    if not settings.heygen_api_key:
        print("[HeyGen] HEYGEN_API_KEY 미설정")
        return None

    run_id = str(uuid.uuid4())[:8]

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            # 1. 오디오 업로드
            audio_asset_id = await _upload_audio(client, audio_bytes, run_id)
            print(f"[HeyGen] 오디오 업로드 완료: {audio_asset_id}")

            # 2. 영상 생성 요청
            resp = await client.post(
                f"{HEYGEN_BASE}/v3/videos",
                headers={**_auth_header(), "Content-Type": "application/json"},
                json={
                    "type": "image",
                    "image": {
                        "type": "base64",
                        "data": _image_b64(),
                        "media_type": "image/png",
                    },
                    "audio_asset_id": audio_asset_id,
                    "expressiveness": "high",
                    "aspect_ratio": "9:16",
                },
                timeout=30,
            )
            resp.raise_for_status()
            video_id = resp.json()["data"]["video_id"]
            print(f"[HeyGen] 영상 생성 요청: {video_id}")

        except httpx.HTTPStatusError as e:
            print(f"[HeyGen] API 오류: {e.response.status_code} {e.response.text}")
            return None
        except Exception as e:
            print(f"[HeyGen] 요청 실패: {e}")
            return None

        # 3. 폴링 (최대 120초, 5초 간격)
        for _ in range(24):
            await asyncio.sleep(5)
            try:
                poll = await client.get(
                    f"{HEYGEN_BASE}/v3/videos/{video_id}",
                    headers=_auth_header(),
                    timeout=15,
                )
                poll.raise_for_status()
                data = poll.json().get("data", {})
                status = data.get("status")
                print(f"[HeyGen] 상태: {status}")
                if status == "completed":
                    video_url = data.get("video_url")
                    break
                elif status == "failed":
                    print(f"[HeyGen] 실패: {data}")
                    return None
            except Exception as e:
                print(f"[HeyGen] 폴링 오류: {e}")
        else:
            print("[HeyGen] 타임아웃")
            return None

        # 4. 결과 mp4 다운로드
        try:
            dl = await client.get(video_url, timeout=60)
            dl.raise_for_status()
            dest_name = f"heygen_{run_id}.mp4"
            dest = PUBLIC_OUT / dest_name
            dest.write_bytes(dl.content)
            print(f"[HeyGen] 저장 완료: {dest}")
            return f"/sadtalker_output/{dest_name}"
        except Exception as e:
            print(f"[HeyGen] 다운로드 실패: {e}")
            return None
