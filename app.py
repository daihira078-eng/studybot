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
    ask_continue_message,
    ENCOURAGEMENTS,
)
from notion_client_helper import (
    get_today_subjects,
    get_yesterday_skips,
    get_recorded_subjects,
    get_current_subject,
    create_draft_log,
    start_subject_record,
    update_log_time,
    save_subject_progress,
    finalize_log_no_study,
    finalize_evening_log,
    save_morning_result,
)
from task_generator import generate_tasks, generate_tasks_structured, MAX_SUBJECTS
from flex_builder import build_task_flex
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
        header, tasks_data, tone = generate_tasks_structured(subjects, today_label, energy=energy, time=time)

        skips = get_yesterday_skips()
        header_text = header
        if skips:
            header_text += "\n\n昨日スキップ: " + "・".join(skips) + " → 今日こそ！"

        msgs = [TextMessage(text=header_text)]
        if tasks_data:
            flex = build_task_flex(tasks_data)
            if flex:
                msgs.append(flex)
            msgs.append(TextMessage(text=tone))
        else:
            msgs.append(TextMessage(text=tone))

        send_reply(reply_token, msgs)

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
        recorded = get_recorded_subjects()
        send_reply(reply_token, subject_select_message(subjects, recorded))

    elif keys == {"recap_subject"}:
        subject = params["recap_subject"]
        start_subject_record(subject)
        send_reply(reply_token, ask_study_time_message(subject))

    elif keys == {"recap_no_study"}:
        finalize_log_no_study()
        send_reply(reply_token, TextMessage(text="今日はゆっくり休んで！\n明日また頑張ろう。"))

    elif keys == {"recap_progress"}:
        save_subject_progress(params["recap_progress"])
        send_reply(reply_token, ask_continue_message())

    elif keys == {"recap_continue"}:
        subjects, _ = get_today_subjects()
        recorded = get_recorded_subjects()
        available = [s for s in subjects if s["name"] not in recorded]
        if not available:
            records, total_min = finalize_evening_log()
            send_reply(reply_token, TextMessage(text=_build_summary(records, total_min)))
        else:
            send_reply(reply_token, subject_select_message(subjects, recorded))

    elif keys == {"recap_done"}:
        records, total_min = finalize_evening_log()
        send_reply(reply_token, TextMessage(text=_build_summary(records, total_min)))


def _build_summary(records: list, total_min: int) -> str:
    lines = ["今日の記録を保存したよ！\n"]
    for r in records:
        lines.append(f"■ {r['subject']}: {r['time']} / {r['progress']}")
    h, m = divmod(total_min, 60)
    if h and m:
        total_str = f"{h}時間{m}分"
    elif h:
        total_str = f"{h}時間"
    else:
        total_str = f"{m}分" if m else "記録なし"
    lines.append(f"\n総勉強時間: {total_str}")
    if total_min >= 120:
        lines.append("今日はたくさん頑張った！お疲れ様！")
    elif total_min >= 30:
        lines.append("よく頑張った！お疲れ様！")
    else:
        lines.append("お疲れ様！また明日！")
    return "\n".join(lines)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    reply_token = event.reply_token
    text = event.message.text.strip()
    updated = update_log_time(text)
    if updated:
        subject = get_current_subject()
        send_reply(reply_token, recap_progress_message(subject))


if __name__ == "__main__":
    app.run(port=5000, debug=True)
