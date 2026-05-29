import os
import re
from dotenv import load_dotenv  
import speech_recognition as sr
from openai import OpenAI

# 프로그램 시작 시 .env 파일의 API 키를 메모리에 로드
load_dotenv() 

# =====================================================================
# 1. SpeechRecognition 라이브러리 사용 (구글 무료 버전)
# =====================================================================
def convert_speech_to_text_google(audio_path):
    """
    [SpeechRecognition + Google 무료 버전]
    API 키 없이 구글 웹 음성 인식 엔진을 사용하여 텍스트로 변환합니다.
    """
    if not audio_path or not os.path.exists(audio_path): 
        return "오디오 파일이 유효하지 않거나 존재하지 않습니다."

    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio = r.record(source)
            
        text = r.recognize_google(audio, language="ko-KR")
        return text.strip()
    except sr.UnknownValueError:
        return "❌ 소리를 인식하지 못했습니다. (무음 또는 배경 소음)"
    except sr.RequestError as e:
        return f"❌ 구글 웹 서비스 에러: {e}"


# =====================================================================
# 2. OpenAI Whisper API 사용 (유료 고성능 버전)
# =====================================================================
def convert_speech_to_text_whisper(audio_path, api_key=None):
    """
    [OpenAI Whisper API 버전]
    오디오 파일 경로를 받아 Whisper-1 모델을 통해 텍스트로 변환합니다.
    """
    if not audio_path or not os.path.exists(audio_path): 
        return "오디오 파일이 유효하지 않거나 존재하지 않습니다."
        
    final_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not final_api_key:
        return "❌ OpenAI API Key가 설정되지 않았습니다. .env 파일을 확인해 주세요."

    try:
        client = OpenAI(api_key=final_api_key)
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                language="ko",
                prompt="공모주, 청약, 등록, 일정, 회의 관련 명령입니다." 
            )
        return transcript.text.strip()
    except Exception as e:
        return f"❌ Whisper STT 에러: {e}"


# --- 단독 실행 및 테스트 구문 ---
if __name__ == "__main__":
    test_file = "test.wav" 
    
    print("=== 1. 구글 무료 SpeechRecognition 단독 테스트 ===")
    if os.path.exists(test_file):
        print(f"🔄 [{test_file}] 파일 변환 중...")
        print(f"👉 결과: \"{convert_speech_to_text_google(test_file)}\"\n")
    else:
        print(f"ℹ️ 테스트할 [{test_file}] 파일이 없습니다.\n")
        
    print("=== 2. OpenAI Whisper STT 단독 테스트 ===")
    if os.path.exists(test_file):
        print(f"🔄 [{test_file}] 파일 변환 중...")
        print(f"👉 결과: \"{convert_speech_to_text_whisper(test_file)}\"")
    else:
        print(f"ℹ️ 테스트할 [{test_file}] 파일이 없습니다.")