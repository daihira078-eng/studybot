import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import PostbackEvent, MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage
from dotenv import load_dotenv

from morning_check import time_check_message
from evening_recap import (
    ask_study_time_message,
    recap_progress_message,
    recap_summary,
)
from notion_client_helper import (
    get_today_subjects,
    create_draft_log,
    update_log_time,
    finalize_log,
)
from task_generator import generate_tasks
from line_sender import send_reply

load_dotenv()

app = Flask(__name__)
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    reply_token = event.reply_token
    params = dict(p.split("=") for p in data.split("&"))

    # --- 朝のチェックフロー ---
    if "energy" in params and "time" not in params:
        send_reply(reply_token, time_check_message(params["energy"]))

    elif "energy" in params and "time" in params:
        subjects, today_label = get_today_subjects()
        text = generate_tasks(subjects, today_label, energy=params["energy"], time=params["time"])
        send_reply(reply_token, TextMessage(text=text))

    # --- 夜の振り返りフロー ---
    elif "recap_energy" in params:
        create_draft_log(params["recap_energy"])
        send_reply(reply_token, ask_study_time_message())

    elif "recap_progress" in params:
        energy_jp, time_text = finalize_log(params["recap_progress"])
        progress_jp = {"start": "始めた", "little": "少し進んだ", "half": "半分くらい", "almost": "ほぼ完了", "done": "完了！"}.get(params["recap_progress"], "")
        enc = {"great": "素晴らしい！その調子で明日も！", "ok": "十分だよ。積み上げが大事！", "bad": "今日は休んで明日また頑張ろう。"}
        energy_key = next((k for k, v in {"great": "頑張れた！", "ok": "まあまあ", "bad": "イマイチ"}.items() if v == energy_jp), "ok")
        text = f"今日の記録を保存したよ！\n頑張り:{energy_jp} / 時間:{time_text} / 進行度:{progress_jp}\n\n{enc.get(energy_key, 'お疲れ様！')}"
        send_reply(reply_token, TextMessage(text=text))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    reply_token = event.reply_token
    text = event.message.text.strip()

    # 勉強時間のテキストを受け取る
    updated = update_log_time(text)
    if updated:
        send_reply(reply_token, recap_progress_message())


if __name__ == "__main__":
    app.run(port=5000, debug=True)
