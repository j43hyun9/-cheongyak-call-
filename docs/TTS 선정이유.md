# TTS 엔진 선정 이유

## 1. gTTS 선택 이유 (1·2차)

- API 키 없이 무료 사용 가능
- `pip install gtts` 한 줄 설치
- 비전공자도 있는 팀 특성상 진입장벽 낮은 라이브러리 필요
- `lang='ko'` 설정만으로 한국어 즉시 지원

```python
from gtts import gTTS
import playsound

tts = gTTS(text="안녕하세요 콜비입니다", lang='ko')
tts.save("output.mp3")
playsound.playsound("output.mp3")
```

---

## 2. Edge-TTS로 고도화 (3차)

- gTTS 대비 훨씬 자연스러운 한국어 음성 (`ko-KR-SunHiNeural`)
- FastAPI `async/await` 구조와 호환
- 마찬가지로 무료 — 비용 부담 없음
- AI Human 콜비 캐릭터 특성상 자연스러운 음성이 중요

```python
async def _generate_audio(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural")
    audio_bytes = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
    return bytes(audio_bytes)

@app.post("/tts", tags=["tts"])
async def tts_endpoint(request: TTSRequest):
    audio_bytes = await _generate_audio(request.text)
    return Response(content=audio_bytes, media_type="audio/mpeg")
```

---

## 3. 구현 중 해결한 이슈

**동시성 문제** → 파일을 아예 저장하지 않는 메모리 스트리밍 방식으로 근본 해결
- 기존: `communicate.save(output_file)`로 파일 저장 후 `FileResponse` 반환
- 최종: `stream()`으로 청크 단위 수신, 파일 I/O 없이 바이트로 직접 반환

```python
# 기존 방식 (파일 저장, 동시성 문제 있음)
output_file = f"tts_{uuid.uuid4().hex}.mp3"
await communicate.save(output_file)
return FileResponse(output_file, media_type="audio/mpeg")

# 최종 방식 (파일 저장 없음, 동시성 문제 근본 해결)
audio_bytes = await _generate_audio(request.text)
return Response(content=audio_bytes, media_type="audio/mpeg")
```

**응답 형식** → PM 확정으로 바이너리 직접 반환 채택

```python
return Response(content=audio_bytes, media_type="audio/mpeg")
```
