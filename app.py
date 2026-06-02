import gradio as gr
from datetime import datetime
from tts import synthesize
from schedule import save_schedule, load_schedule


# --- TTS ---

def tts_handler(text: str):
    if not text.strip():
        return None
    path = synthesize(text)
    return path


# --- 일정 저장 ---

def add_schedule_handler(title: str, date_str: str, time_str: str):
    if not title.strip() or not date_str or not time_str:
        return "제목, 날짜, 시간을 모두 입력해 주세요."
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "날짜/시간 형식을 확인해 주세요. (날짜: YYYY-MM-DD, 시간: HH:MM)"
    entry = save_schedule(title, dt)
    return f"저장됨: {entry['title']} @ {entry['datetime']}"


# --- 일정 조회 ---

def view_schedule_handler(date_str: str):
    if not date_str:
        return "날짜를 입력해 주세요."
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "날짜 형식을 확인해 주세요. (YYYY-MM-DD)"
    items = load_schedule(dt)
    if not items:
        return "해당 날짜에 일정이 없습니다."
    return "\n".join(f"- {i['title']}  ({i['datetime'][11:16]})" for i in items)


# --- UI ---

with gr.Blocks(title="청약콜") as demo:
    gr.Markdown("# 청약콜")

    with gr.Tab("TTS"):
        gr.Markdown("### 텍스트 → 음성 변환")
        tts_input = gr.Textbox(label="텍스트 입력", placeholder="읽어줄 내용을 입력하세요")
        tts_btn = gr.Button("변환")
        tts_audio = gr.Audio(label="음성 출력", type="filepath")
        tts_btn.click(fn=tts_handler, inputs=tts_input, outputs=tts_audio)

    with gr.Tab("일정 관리"):
        gr.Markdown("### 일정 추가")
        with gr.Row():
            sch_title = gr.Textbox(label="제목")
            sch_date = gr.Textbox(label="날짜 (YYYY-MM-DD)", placeholder="2026-06-05")
            sch_time = gr.Textbox(label="시간 (HH:MM)", placeholder="09:00")
        add_btn = gr.Button("저장")
        add_result = gr.Textbox(label="결과", interactive=False)
        add_btn.click(fn=add_schedule_handler, inputs=[sch_title, sch_date, sch_time], outputs=add_result)

        gr.Markdown("### 일정 조회")
        view_date = gr.Textbox(label="날짜 (YYYY-MM-DD)", placeholder="2026-06-05")
        view_btn = gr.Button("조회")
        view_result = gr.Textbox(label="결과", interactive=False, lines=5)
        view_btn.click(fn=view_schedule_handler, inputs=view_date, outputs=view_result)


if __name__ == "__main__":
    demo.launch()
