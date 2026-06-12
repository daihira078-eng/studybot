import os
import random
from datetime import datetime, timedelta, timezone
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import PostbackEvent, MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    TextMessage, FlexMessage, FlexBubble, FlexBox, FlexText, FlexSeparator, FlexButton,
    PostbackAction,
)
from dotenv import load_dotenv

from morning_check import morning_check_message, time_check_message
from evening_recap import (
    evening_check_message,
    subject_select_message,
    ask_study_time_message,
    recap_progress_message,
    ask_continue_message,
)
from notion_client_helper import (
    get_today_subjects,
    get_all_subjects,
    get_yesterday_skips,
    get_yesterday_understanding,
    get_today_log,
    ensure_active_log,
    reset_active_log,
    get_streak,
    get_recorded_subjects,
    get_current_subject,
    create_draft_log,
    start_subject_record,
    update_log_time,
    save_subject_progress,
    finalize_log_no_study,
    finalize_evening_log,
    save_morning_result,
    get_subject_by_name,
)
from task_generator import generate_tasks_structured, generate_free_tasks, generate_study_guide
from flex_builder import build_task_flex
from line_sender import send_reply
from weekly_report import build_report

load_dotenv()

JST = timezone(timedelta(hours=9))
app = Flask(__name__)
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])


# ── ヘルパー関数 ──────────────────────────────────────────

def _build_today_log_flex(log: dict) -> FlexMessage:
    now = datetime.now(JST)
    today = f"{now.month}/{now.day}"
    body = []

    if log["morning"]:
        body.append(FlexText(text="朝の課題", size="xs", color="#888888", weight="bold"))
        for r in log["morning"]:
            body.append(FlexText(text=r, size="sm", color="#333333", margin="xs"))

    if log["evening"]:
        if body:
            body.append(FlexSeparator(margin="md"))
        body.append(FlexText(text="今日の勉強", size="xs", color="#888888", weight="bold", margin="md"))
        for r in log["evening"]:
            body.append(FlexText(
                text=f"{r['subject']}  {r['time']}  {r['understanding']}",
                size="sm", color="#333333", margin="xs", wrap=True,
            ))
        h, m = divmod(log["total_minutes"], 60)
        total_str = (f"{h}時間{m}分" if h and m else f"{h}時間" if h else f"{m}分") if log["total_minutes"] else "0分"
        body.append(FlexSeparator(margin="md"))
        body.append(FlexText(text=f"合計  {total_str}", size="sm", color="#333333", weight="bold", margin="sm"))

    if not body:
        body.append(FlexText(text="まだ今日の記録はないよ", size="sm", color="#888888"))

    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#4A90D9",
            padding_all="md",
            contents=[FlexText(text=f"📋 {today}の記録", weight="bold", size="lg", color="#FFFFFF")],
        ),
        body=FlexBox(layout="vertical", spacing="xs", padding_all="lg", contents=body),
    )
    return FlexMessage(alt_text="今日の記録", contents=bubble)


def _build_today_summary_flex(log: dict) -> FlexMessage:
    now = datetime.now(JST)
    today = f"{now.month}/{now.day}"
    body = [FlexText(text="今日の記録を保存したよ！", size="sm", color="#4CAF50", weight="bold")]

    if log["morning"]:
        body.append(FlexSeparator(margin="md"))
        body.append(FlexText(text="朝の課題", size="xs", color="#888888", weight="bold", margin="md"))
        for r in log["morning"]:
            body.append(FlexText(text=r, size="sm", color="#333333", margin="xs"))

    if log["evening"]:
        body.append(FlexSeparator(margin="md"))
        body.append(FlexText(text="勉強記録", size="xs", color="#888888", weight="bold", margin="md"))
        for r in log["evening"]:
            body.append(FlexText(
                text=f"{r['subject']}  {r['time']}  {r['understanding']}",
                size="sm", color="#333333", margin="xs", wrap=True,
            ))
        h, m = divmod(log["total_minutes"], 60)
        total_str = (f"{h}時間{m}分" if h and m else f"{h}時間" if h else f"{m}分") if log["total_minutes"] else "0分"
        body.append(FlexSeparator(margin="md"))
        body.append(FlexText(text=f"合計  {total_str}", size="sm", color="#333333", weight="bold", margin="sm"))

    if len(body) == 1:
        body.append(FlexText(text="今日は勉強なしで記録したよ", size="sm", color="#888888", margin="sm"))

    mins = log["total_minutes"]
    if mins >= 120:
        cheer = "今日はたくさん頑張った！お疲れ様！"
    elif mins >= 30:
        cheer = "よく頑張った！お疲れ様！"
    else:
        cheer = "お疲れ様！また明日！"
    body.append(FlexText(text=cheer, size="xs", color="#888888", margin="md", wrap=True))

    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#3F51B5",
            padding_all="md",
            contents=[FlexText(text=f"🌙 {today}のまとめ", weight="bold", size="lg", color="#FFFFFF")],
        ),
        body=FlexBox(layout="vertical", spacing="xs", padding_all="lg", contents=body),
    )
    return FlexMessage(alt_text="今日のまとめ", contents=bubble)


def _build_no_study_flex() -> FlexMessage:
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
                FlexText(text="お疲れ様！", size="xl", weight="bold", color="#333333", align="center"),
                FlexText(text=title, size="md", color="#555555", align="center", margin="md", wrap=True),
                FlexText(text=sub, size="sm", color="#888888", align="center", margin="sm", wrap=True),
            ],
        ),
    )
    return FlexMessage(alt_text="今日はゆっくり休んで", contents=bubble)


def _build_study_guide_flex(subject_name: str, theme: str, guide: dict) -> FlexMessage:
    steps = [
        ("📖 インプット", guide.get("input",    "教科書・資料で概念を理解する")),
        ("✏️ 演習",       guide.get("practice", "例題・練習問題を解く")),
        ("✅ 確認",       guide.get("review",   "解いた問題を見直し、理解を確認する")),
    ]
    body_contents = []
    for i, (label, text) in enumerate(steps):
        if i > 0:
            body_contents.append(FlexSeparator(margin="md"))
        body_contents.append(FlexText(text=label, size="sm", color="#7B68EE", weight="bold", margin="md"))
        body_contents.append(FlexText(text=text, size="sm", color="#333333", margin="xs", wrap=True))

    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#7B68EE",
            padding_all="md",
            contents=[
                FlexText(text=subject_name, size="sm", color="#DDDDFF", weight="bold"),
                FlexText(text=theme, size="md", color="#FFFFFF", weight="bold", margin="xs", wrap=True),
            ],
        ),
        body=FlexBox(layout="vertical", spacing="xs", padding_all="lg", contents=body_contents),
    )
    return FlexMessage(alt_text=f"{theme}の進め方", contents=bubble)


def _free_task_subject_flex(subjects: list) -> FlexMessage:
    cat_order = ["大学", "資格"]
    groups: dict = {}
    for s in subjects:
        cat = s.get("category") or "その他"
        groups.setdefault(cat, []).append(s["name"])

    sorted_cats = sorted(groups.keys(), key=lambda c: cat_order.index(c) if c in cat_order else 99)

    body_contents = []
    for cat in sorted_cats:
        if body_contents:
            body_contents.append(FlexSeparator(margin="md"))
        body_contents.append(FlexText(text=cat, size="xs", color="#888888", weight="bold", margin="md"))
        for name in groups[cat]:
            body_contents.append(FlexButton(
                action=PostbackAction(
                    label=name,
                    data=f"free_subject={name}",
                    display_text=f"{name}の課題を出して",
                ),
                style="secondary",
                height="sm",
                margin="xs",
            ))

    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#7B68EE",
            padding_all="md",
            contents=[FlexText(text="どの科目の課題を出す？", weight="bold", size="lg", color="#FFFFFF")],
        ),
        body=FlexBox(layout="vertical", spacing="xs", padding_all="lg", contents=body_contents),
    )
    return FlexMessage(alt_text="科目を選んでください", contents=bubble)


def _free_task_count_flex(subject_name: str) -> FlexMessage:
    counts = [
        ("少なめ (1個)", "1", "#4CAF50"),
        ("普通 (2個)",   "2", "#2196F3"),
        ("多め (3個)",   "3", "#FF9800"),
    ]
    buttons = [
        FlexButton(
            action=PostbackAction(
                label=label,
                data=f"free_subject={subject_name}&free_count={n}",
                display_text=f"{label}で",
            ),
            style="primary",
            color=color,
            height="sm",
        )
        for label, n, color in counts
    ]
    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#7B68EE",
            padding_all="md",
            contents=[
                FlexText(text=subject_name, weight="bold", size="lg", color="#FFFFFF"),
                FlexText(text="どれくらい課題を出す？", size="sm", color="#DDDDFF", margin="xs"),
            ],
        ),
        body=FlexBox(layout="vertical", spacing="sm", padding_all="lg", contents=buttons),
    )
    return FlexMessage(alt_text="課題の量を選んでください", contents=bubble)


def _build_summary(records: list, total_min: int) -> str:
    lines = ["今日の記録を保存したよ！\n"]
    for r in records:
        lines.append(f"■ {r['subject']}: {r['time']} / {r['progress']}")
    h, m = divmod(total_min, 60)
    total_str = f"{h}時間{m}分" if h and m else f"{h}時間" if h else f"{m}分" if m else "記録なし"
    lines.append(f"\n総勉強時間: {total_str}")
    if total_min >= 120:
        lines.append("今日はたくさん頑張った！お疲れ様！")
    elif total_min >= 30:
        lines.append("よく頑張った！お疲れ様！")
    else:
        lines.append("お疲れ様！また明日！")
    return "\n".join(lines)


# ── Webhook ────────────────────────────────────────────────

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
            subjects, today_label = get_today_subjects()
            understanding = get_yesterday_understanding()
            header, tasks_data, tone = generate_tasks_structured(
                subjects, today_label, energy="mid", time="mid", understanding=understanding
            )
            msgs = [TextMessage(text=header)]
            if tasks_data:
                flex = build_task_flex(tasks_data)
                if flex:
                    msgs.append(flex)
            msgs.append(TextMessage(text=tone))
            send_reply(reply_token, msgs)
        elif action == "record":
            ensure_active_log()
            today_subjects, _ = get_today_subjects()
            all_subjects = get_all_subjects()
            recorded = get_recorded_subjects()
            send_reply(reply_token, subject_select_message(today_subjects, all_subjects, recorded))
        elif action == "free_task":
            all_subjects = get_all_subjects()
            send_reply(reply_token, _free_task_subject_flex(all_subjects))
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

    # ── 朝のチェックフロー ──────────────────────────────
    elif keys == {"energy"}:
        send_reply(reply_token, time_check_message(params["energy"]))

    elif keys == {"energy", "time"}:
        energy, time = params["energy"], params["time"]
        subjects, today_label = get_today_subjects()
        understanding = get_yesterday_understanding()
        header, tasks_data, tone = generate_tasks_structured(
            subjects, today_label, energy=energy, time=time, understanding=understanding
        )
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
        send_reply(reply_token, msgs)

    # ── 朝の完了・スキップ ────────────────────────────
    elif keys == {"action", "subject"}:
        action = params["action"]
        subject = params["subject"]
        save_morning_result(subject, action)
        msg = f"{subject} 完了！記録したよ💪" if action == "complete" else f"{subject} スキップ。また次回！"
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
            finalize_evening_log()
            log = get_today_log()
            send_reply(reply_token, _build_today_summary_flex(log))
        else:
            send_reply(reply_token, subject_select_message(today_subjects, all_subjects, recorded))

    elif keys == {"recap_done"}:
        finalize_evening_log()
        log = get_today_log()
        send_reply(reply_token, _build_today_summary_flex(log))

    # ── 自由課題フロー ──────────────────────────────────
    elif keys == {"free_subject"}:
        subject = get_subject_by_name(params["free_subject"])
        parsed = generate_free_tasks(subject, 3)
        flex = build_task_flex(parsed, show_footer=False, show_study_guide=True)
        if flex:
            send_reply(reply_token, flex)
        else:
            send_reply(reply_token, TextMessage(text=f"{params['free_subject']}の課題を生成できませんでした。"))

    elif keys == {"study_subject", "study_theme"}:
        guide = generate_study_guide(params["study_subject"], params["study_theme"])
        send_reply(reply_token, _build_study_guide_flex(params["study_subject"], params["study_theme"], guide))


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
