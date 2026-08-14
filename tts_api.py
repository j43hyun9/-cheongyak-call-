from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import edge_tts
import asyncio
import uuid
import os

app = FastAPI()

VOICE = "ko-KR-SunHiNeural"

class TTSRequest(BaseModel):
    text: str

async def _generate_audio(text: str, output_file: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

@app.post("/tts")
async def tts_endpoint(request: TTSRequest):
    # 요청마다 고유한 파일명 생성
    output_file = f"tts_{uuid.uuid4().hex}.mp3"
    await _generate_audio(request.text, output_file)
    
    return FileResponse(
        output_file,
        media_type="audio/mpeg",
        filename="response.mp3",
        background=None
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)