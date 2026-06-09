import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import PostbackEvent
from linebot.v3.messaging import TextMessage
from dotenv import load_dotenv

from morning_check import time_check_message
from notion_client_helper import get_today_subjects
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

    if data.startswith("energy=") and "&" not in data:
        energy = data.split("=")[1]
        send_reply(reply_token, time_check_message(energy))

    elif "energy=" in data and "time=" in data:
        params = dict(p.split("=") for p in data.split("&"))
        subjects, today_label = get_today_subjects()
        text = generate_tasks(
            subjects, today_label,
            energy=params.get("energy", "mid"),
            time=params.get("time", "mid"),
        )
        send_reply(reply_token, TextMessage(text=text))


if __name__ == "__main__":
    app.run(port=5000, debug=True)
