import os
import re
from datetime import date, timedelta
from collections import defaultdict
from notion_client import Client
from dotenv import load_dotenv
from line_sender import send_broadcast
from linebot.v3.messaging import TextMessage

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])
LOG_DATABASE_ID = os.environ["NOTION_LOG_DATABASE_ID"]


def _parse_minutes(text: str) -> int:
    total = 0.0
    h = re.search(r'(\d+(?:\.\d+)?)\s*時間', text)
    m = re.search(r'(\d+)\s*分', text)
    half = re.search(r'半', text)
    if h:
        total += float(h.group(1)) * 60
    if m:
        total += int(m.group(1))
    elif half:
        total += 30
    if not h and not m and not half:
        h2 = re.search(r'(\d+(?:\.\d+)?)\s*h', text)
        if h2:
            total += float(h2.group(1)) * 60
    return int(total)


def _format_minutes(total: int) -> str:
    if total == 0:
        return "記録なし"
    h, m = divmod(total, 60)
    if h == 0:
        return f"{m}分"
    return f"{h}時間{m}分" if m else f"{h}時間"


def _build_report() -> str:
    today = date.today()
    week_start = today - timedelta(days=7)

    results = notion.databases.query(
        database_id=LOG_DATABASE_ID,
        filter={"property": "記録日", "date": {"on_or_after": str(week_start)}},
    )["results"]

    study_days = set()
    subject_count = defaultdict(int)
    complete_count = 0
    skip_count = 0
    total_minutes = 0

    for page in results:
        props = page["properties"]

        date_val = props.get("記録日", {}).get("date")
        if date_val:
            study_days.add(date_val["start"])

        subjects_rt = props.get("科目記録", {}).get("rich_text", [])
        subjects_text = subjects_rt[0]["plain_text"] if subjects_rt else ""

        if subjects_text.startswith("✅"):
            complete_count += 1
            name = subjects_text[2:].strip()
            subject_count[name] += 1
        elif subjects_text.startswith("⏭"):
            skip_count += 1
        elif subjects_text:
            for s in subjects_text.split("、"):
                s = s.strip()
                if s:
                    subject_count[s] += 1

        time_rt = props.get("勉強時間", {}).get("rich_text", [])
        time_text = time_rt[0]["plain_text"] if time_rt else ""
        if time_text:
            total_minutes += _parse_minutes(time_text)

    days_studied = len(study_days)
    period = f"{week_start.month}/{week_start.day}〜{today.month}/{today.day}"

    lines = [
        f"今週の勉強まとめ（{period}）",
        f"勉強した日: {days_studied}日 / 7日",
        f"総勉強時間: {_format_minutes(total_minutes)}",
        "────────────",
    ]

    if subject_count:
        for name, count in sorted(subject_count.items(), key=lambda x: -x[1]):
            lines.append(f"{name}: {count}回")
    else:
        lines.append("記録なし")

    lines.append("────────────")
    lines.append(f"完了✅: {complete_count}件  スキップ⏭: {skip_count}件")

    if days_studied >= 6:
        lines.append("\n今週は最高！来週もこの調子で！")
    elif days_studied >= 4:
        lines.append("\n今週もよく頑張った！")
    elif days_studied >= 2:
        lines.append("\n来週はもう少し頑張ってみよう！")
    else:
        lines.append("\n来週は毎日少しでもやってみよう！")

    return "\n".join(lines)


if __name__ == "__main__":
    report = _build_report()
    send_broadcast(TextMessage(text=report))
    print("週報送信完了")
