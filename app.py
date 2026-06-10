import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import PostbackEvent, MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage, QuickReply, QuickReplyItem, PostbackAction
from dotenv import load_dotenv

from morning_check import morning_check_message, time_check_message
from evening_recap import (
    evening_check_message,
    subject_select_message,
    ask_study_time_message,
    recap_progress_message,
    ask_continue_message,
    ENCOURAGEMENTS,
)
from notion_client_helper import (
    get_today_subjects,
    get_all_subjects,
    get_yesterday_skips,
    get_yesterday_understanding,
    get_today_log,
    reset_active_log,
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
from weekly_report import build_report
from notion_client_helper import get_streak

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

    # ── リッチメニュー ──────────────────────────────────
    if keys == {"menu"}:
        action = params["menu"]
        if action == "morning":
            send_reply(reply_token, morning_check_message())
        elif action == "evening":
            send_reply(reply_token, evening_check_message())
        elif action == "weekly":
            send_reply(reply_token, TextMessage(text=build_report()))
        elif action == "streak":
            streak = get_streak()
            if streak == 0:
                msg = "まだ連続記録がないよ。今日から始めよう！"
            elif streak == 1:
                msg = "連続1日！今日も続けよう🔥"
            else:
                msg = f"🔥 {streak}日連続勉強中！この調子で！"
            send_reply(reply_token, TextMessage(text=msg))
        elif action == "today_log":
            log = get_today_log()
            send_reply(reply_token, _build_today_log_flex(log))
        elif action == "reset":
            count = reset_active_log()
            if count:
                msg = "途中データをリセットしたよ。夜の振り返りをやり直せます。"
            else:
                msg = "リセットするデータはなかったよ。"
            send_reply(reply_token, TextMessage(text=msg))

    # ── 朝のチェックフロー ──────────────────────────────
    elif keys == {"energy"}:
        send_reply(reply_token, time_check_message(params["energy"]))

    elif keys == {"energy", "time"}:
        energy, time = params["energy"], params["time"]
        subjects, today_label = get_today_subjects()
        understanding = get_yesterday_understanding()
        header, tasks_data, tone = generate_tasks_structured(subjects, today_label, energy=energy, time=time, understanding=understanding)

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
        today_subjects, _ = get_today_subjects()
        all_subjects = get_all_subjects()
        recorded = get_recorded_subjects()
        send_reply(reply_token, subject_select_message(today_subjects, all_subjects, recorded))

    elif keys == {"recap_subject"}:
        subject = params["recap_subject"]
        start_subject_record(subject)
        send_reply(reply_token, ask_study_time_message(subject))

    elif keys == {"recap_no_study"}:
        finalize_log_no_study()
        send_reply(reply_token, _build_no_study_flex())

    elif keys == {"recap_progress"}:
        save_subject_progress(params["recap_progress"])
        send_reply(reply_token, ask_continue_message())

    elif keys == {"recap_continue"}:
        today_subjects, _ = get_today_subjects()
        all_subjects = get_all_subjects()
        recorded = get_recorded_subjects()
        available = [s for s in all_subjects if s["name"] not in recorded]
        if not available:
            records, total_min = finalize_evening_log()
            send_reply(reply_token, TextMessage(text=_build_summary(records, total_min)))
        else:
            send_reply(reply_token, subject_select_message(today_subjects, all_subjects, recorded))

    elif keys == {"recap_done"}:
        records, total_min = finalize_evening_log()
        send_reply(reply_token, TextMessage(text=_build_summary(records, total_min)))


def _build_today_log_flex(log: dict):
    from linebot.v3.messaging import FlexMessage, FlexBubble, FlexBox, FlexText, FlexSeparator
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%-m/%-d") if False else \
        f"{datetime.now(timezone(timedelta(hours=9))).month}/{datetime.now(timezone(timedelta(hours=9))).day}"
    body = []
    if log["morning"]:
        body.append(FlexText(text="朝の課題", size="xs", color="#888888", weight="bold"))
        for r in log["morning"]:
            body.append(FlexText(text=r, size="sm", color="#333333", margin="xs"))
    if log["evening"]:
        if body:
            body.append(FlexSeparator(margin="md"))
        body.append(FlexText(text="今日の勉強", size="xs", color="#888888", weight="bold", margin="md" if not body else "none"))
        for r in log["evening"]:
            body.append(FlexText(
                text=f"{r['subject']}  {r['time']}  {r['understanding']}",
                size="sm", color="#333333", margin="xs", wrap=True,
            ))
        h, m = divmod(log["total_minutes"], 60)
        total_str = f"{h}時間{m}分" if h and m else f"{h}時間" if h else f"{m}分" if m else "0分"
        body.append(FlexSeparator(margin="md"))
        body.append(FlexText(text=f"合計  {total_str}", size="sm", color="#333333", weight="bold", margin="sm"))
    if not body:
        body.append(FlexText(text="まだ今日の記録はないよ", size="sm", color="#888888"))
    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(layout="vertical", background_color="#4A90D9", padding_all="md",
                       contents=[FlexText(text=f"📋 {today}の記録", weight="bold", size="lg", color="#FFFFFF")]),
        body=FlexBox(layout="vertical", spacing="xs", padding_all="lg", contents=body),
    )
    return FlexMessage(alt_text="今日の記録", contents=bubble)


def _build_no_study_flex():
    from linebot.v3.messaging import FlexMessage, FlexBubble, FlexBox, FlexText
    import random
    messages = [
        ("休息も大事な勉強だよ", "明日また頑張ろう💪"),
        ("今日は無理せずでOK", "小さな一歩でも積み重なる"),
        ("ゆっくり休んでね", "明日の自分に期待！"),
    ]
    title, sub = random.choice(messages)
    bubble = FlexBubble(
        size="kilo",
        body=FlexBox(
            layout="vertical",
            spacing="sm",
            padding_all="xl",
            contents=[
                FlexText(text="🌙", size="xxl", align="center"),
                FlexText(text=title, size="lg", weight="bold", color="#333333", align="center", margin="md"),
                FlexText(text=sub, size="sm", color="#888888", align="center", margin="sm"),
            ],
        ),
    )
    return FlexMessage(alt_text="今日はゆっくり休んで", contents=bubble)


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
