import edge_tts
import asyncio
import os

# 한국어 여성 목소리 (자연스러운 한국어)
VOICE = "ko-KR-SunHiNeural"

async def _speak_async(text: str, output_file: str = "response.mp3"):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def speak(text: str):
    # 음성 파일 생성
    asyncio.run(_speak_async(text))
    
    # 음성 재생
    os.system("start response.mp3")  # Windows

# 테스트
if __name__ == "__main__":
    speak("안녕하세요, 저는 AI 비서 콜비입니다.")
    speak("이번 주 공모주 일정을 알려드리겠습니다.")