from gtts import gTTS
import playsound
import os


def speak(text):
    tts = gTTS(text=text, lang='ko')
    tts.save("response.mp3")
    playsound.playsound("response.mp3")
    os.remove("response.mp3")


if __name__ == "__main__":
    speak("안녕하세요, AI 투자 일정 비서입니다.")
    speak("공모주 청약 일정을 알려드리겠습니다.")
