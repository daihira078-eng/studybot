import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import PostbackEvent, MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage, QuickReply, QuickReplyItem, PostbackAction
from dotenv import load_dotenv

from morning_check import time_check_message
from evening_recap import (
    subject_select_message,
    ask_study_time_message,
    recap_progress_message,
    ENCOURAGEMENTS,
)
from notion_client_helper import (
    get_today_subjects,
    get_yesterday_skips,
    create_draft_log,
    add_subject_to_log,
    complete_subject_selection,
    finalize_log_no_study,
    update_log_time,
    finalize_log,
    save_morning_result,
)
from task_generator import generate_tasks, MAX_SUBJECTS
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
    params = dict(p.split("=", 1) for p in data.split("&"))
    keys = set(params.keys())

    # ── 朝のチェックフロー ──────────────────────────────
    if keys == {"energy"}:
        send_reply(reply_token, time_check_message(params["energy"]))

    elif keys == {"energy", "time"}:
        energy, time = params["energy"], params["time"]
        subjects, today_label = get_today_subjects()
        text = generate_tasks(subjects, today_label, energy=energy, time=time)
        limit = MAX_SUBJECTS.get((energy, time), len(subjects))
        limited = subjects[:limit]
        qr_items = []
        for s in limited:
            name = s["name"]
            qr_items.append(QuickReplyItem(action=PostbackAction(
                label=f"✅ {name[:10]}", data=f"action=complete&subject={name}", display_text=f"✅ {name}"
            )))
            qr_items.append(QuickReplyItem(action=PostbackAction(
                label=f"⏭ {name[:10]}", data=f"action=skip&subject={name}", display_text=f"⏭ {name}"
            )))
        skips = get_yesterday_skips()
        if skips:
            skip_line = "昨日スキップ: " + "・".join(skips)
            text = text + f"\n\n{skip_line} → 今日こそ！"
        task_msg = TextMessage(text=text)
        if qr_items:
            check_msg = TextMessage(
                text="終わった科目があったら報告してね！",
                quick_reply=QuickReply(items=qr_items),
            )
            send_reply(reply_token, [task_msg, check_msg])
        else:
            send_reply(reply_token, task_msg)

    # ── 朝の完了・スキップ ────────────────────────────
    elif keys == {"action", "subject"}:
        action = params["action"]
        subject = params["subject"]
        save_morning_result(subject, action)
        if action == "complete":
            msg = f"{subject} 完了！記録したよ💪"
        else:
            msg = f"{subject} スキップ。また次回！"
        send_reply(reply_token, TextMessage(text=msg))

    # ── 夜の振り返りフロー ──────────────────────────────
    elif keys == {"recap_energy"}:
        create_draft_log(params["recap_energy"])
        subjects, _ = get_today_subjects()
        send_reply(reply_token, subject_select_message(subjects, []))

    elif "recap_subject" in keys and "recap_subjects_done" not in keys:
        selected = add_subject_to_log(params["recap_subject"])
        subjects, _ = get_today_subjects()
        send_reply(reply_token, subject_select_message(subjects, selected))

    elif "recap_subjects_done" in keys:
        if params.get("recap_subject") == "no_study":
            finalize_log_no_study()
            send_reply(reply_token, TextMessage(text="今日はゆっくり休んで！\n明日また頑張ろう。"))
        else:
            complete_subject_selection()
            send_reply(reply_token, ask_study_time_message())

    elif keys == {"recap_progress"}:
        energy_jp, time_text, subjects = finalize_log(params["recap_progress"])
        if energy_jp:
            enc_key = next((k for k, v in {"great": "頑張れた！", "ok": "まあまあ", "bad": "イマイチ"}.items() if v == energy_jp), "ok")
            enc = ENCOURAGEMENTS.get(enc_key, "お疲れ様！")
            progress_jp = {"start": "始めた", "little": "少し進んだ", "half": "半分くらい", "almost": "ほぼ完了", "done": "完了！"}.get(params["recap_progress"], "")
            text = f"今日の記録を保存したよ！\n科目:{subjects}\n時間:{time_text}\n進行度:{progress_jp}\n\n{enc}"
        else:
            text = "記録完了！お疲れ様でした。"
        send_reply(reply_token, TextMessage(text=text))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    reply_token = event.reply_token
    text = event.message.text.strip()
    updated = update_log_time(text)
    if updated:
        send_reply(reply_token, recap_progress_message())


if __name__ == "__main__":
    app.run(port=5000, debug=True)
