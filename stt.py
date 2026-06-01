import os
from openai import OpenAI
from dotenv import load_dotenv  

# 프로그램 시작 시 .env 파일의 API 키를 메모리에 로드
load_dotenv() 

def convert_speech_to_text_whisper(audio_path, api_key=None):
    """
    [OpenAI Whisper API 버전]
    오디오 파일 경로를 받아 Whisper-1 모델을 통해 텍스트로 변환합니다.
    """
    # ─── [피드백 반영] 에러 발생 시 다운스트림 오해 방지를 위해 빈 문자열("") 반환 ───
    if not audio_path or not os.path.exists(audio_path): 
        print("⚠️ 오디오 파일이 유효하지 않거나 존재하지 않습니다.")
        return ""
        
    final_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not final_api_key:
        print("❌ OpenAI API Key가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
        return ""

    try:
        client = OpenAI(api_key=final_api_key)
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                language="ko",
                # 기획서 시나리오 맞춤형 힌트 단어 (소음 환각 방지)
                prompt="공모주, 청약, 등록, 일정, 회의 관련 명령입니다." 
            )
        return transcript.text.strip()
    except Exception as e:
        print(f"❌ Whisper STT 에러 발생: {e}")
        return ""


# ─── [피드백 반영] 기획자 요청 별칭(Alias) 함수 추가 ───
def transcribe(audio_path) -> str:
    """
    STT 모듈의 통합용 메인 함수 인터페이스입니다.
    Gradio UI 및 타 모듈에서 import 할 때 이 함수를 호출합니다.
    """
    return convert_speech_to_text_whisper(audio_path)


# --- 단독 실행 및 테스트 구문 ---
if __name__ == "__main__":
    # 테스트할 파일명을 적어주세요 (Gradio 결합 시에는 이 구문이 실행되지 않습니다)
    test_file = "test1.wav" 
    
    print("=== OpenAI Whisper STT 단독 테스트 (transcribe 호출) ===")
    if os.path.exists(test_file):
        print(f"🔄 [{test_file}] 파일 변환 중...")
        result = transcribe(test_file)
        print(f"👉 결과: \"{result}\"")
    else:
        print(f"ℹ️ 테스트할 [{test_file}] 파일이 로컬에 없습니다. 파일명을 확인해 주세요.")
