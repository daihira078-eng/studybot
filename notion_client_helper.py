import os
import re
from datetime import datetime, date, timedelta
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
LOG_DATABASE_ID = os.environ.get("NOTION_LOG_DATABASE_ID", "")

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

ENERGY_TO_JP = {"great": "頑張れた！", "ok": "まあまあ", "bad": "イマイチ"}
PROGRESS_TO_JP = {
    "start": "始めた", "little": "少し進んだ",
    "half": "半分くらい", "almost": "ほぼ完了", "done": "完了！",
}


def _detect_props(db_props):
    title_key = None
    checkbox_key = None
    multi_select_key = None
    multi_select_options = []
    select_keys = []
    rich_text_key = None

    for name, info in db_props.items():
        t = info["type"]
        if t == "title":
            title_key = name
        elif t == "checkbox":
            checkbox_key = name
        elif t == "multi_select":
            multi_select_key = name
            multi_select_options = [o["name"] for o in info["multi_select"]["options"]]
        elif t == "select":
            select_keys.append(name)
        elif t == "rich_text":
            rich_text_key = name

    return {
        "title": title_key,
        "checkbox": checkbox_key,
        "multi_select": multi_select_key,
        "multi_select_options": multi_select_options,
        "selects": select_keys,
        "rich_text": rich_text_key,
    }


def _get_page_detail(page_id: str) -> str:
    try:
        blocks = notion.blocks.children.list(block_id=page_id)
        lines = []
        for block in blocks["results"]:
            btype = block["type"]
            if btype in ("paragraph", "heading_1", "heading_2", "heading_3",
                         "bulleted_list_item", "numbered_list_item"):
                rt = block[btype].get("rich_text", [])
                text = "".join(t["plain_text"] for t in rt)
                if text:
                    lines.append(text)
        return "\n".join(lines)[:600]
    except Exception:
        return ""


def get_today_subjects():
    db = notion.databases.retrieve(database_id=DATABASE_ID)
    keys = _detect_props(db["properties"])

    weekday_idx = datetime.now().weekday()
    today_label = WEEKDAY_JP[weekday_idx]

    all_pages = notion.databases.query(database_id=DATABASE_ID)

    subjects = []
    for page in all_pages["results"]:
        props = page["properties"]

        if keys["checkbox"] and not props[keys["checkbox"]]["checkbox"]:
            continue

        if keys["multi_select"]:
            options_today = [o["name"] for o in props[keys["multi_select"]]["multi_select"]]
            if today_label not in options_today:
                continue

        name = ""
        if keys["title"]:
            title_list = props[keys["title"]]["title"]
            name = title_list[0]["plain_text"] if title_list else ""

        selects = []
        for sk in keys["selects"]:
            val = props[sk]["select"]
            selects.append(val["name"] if val else "")

        memo = ""
        if keys["rich_text"]:
            rt = props[keys["rich_text"]]["rich_text"]
            memo = rt[0]["plain_text"] if rt else ""

        subjects.append({
            "name": name,
            "category": selects[1] if len(selects) > 1 else "",
            "difficulty": selects[0] if len(selects) > 0 else "",
            "memo": memo,
            "detail": _get_page_detail(page["id"]),
        })

    return subjects, today_label


# ── ストリーク・スキップ繰り越し・試験日 ──────────────────

def get_streak() -> int:
    check = date.today() - timedelta(days=1)
    streak = 0
    for _ in range(60):
        res = notion.databases.query(
            database_id=LOG_DATABASE_ID,
            filter={"property": "記録日", "date": {"equals": str(check)}},
        )["results"]
        if not res:
            break
        streak += 1
        check -= timedelta(days=1)
    return streak


def get_yesterday_skips() -> list:
    yesterday = str(date.today() - timedelta(days=1))
    res = notion.databases.query(
        database_id=LOG_DATABASE_ID,
        filter={"property": "記録日", "date": {"equals": yesterday}},
    )["results"]
    skips = []
    for page in res:
        rt = page["properties"].get("科目記録", {}).get("rich_text", [])
        text = rt[0]["plain_text"] if rt else ""
        if text.startswith("⏭"):
            skips.append(text[2:].strip())
    return skips


def get_upcoming_exams() -> list:
    today = str(date.today())
    res = notion.databases.query(
        database_id=DATABASE_ID,
        filter={"property": "試験日", "date": {"on_or_after": today}},
    )["results"]
    exams = []
    for page in res:
        exam_date = page["properties"].get("試験日", {}).get("date")
        if not exam_date:
            continue
        from datetime import datetime as dt
        exam_dt = dt.strptime(exam_date["start"], "%Y-%m-%d").date()
        days_left = (exam_dt - date.today()).days
        title_prop = next(
            (p for p in page["properties"].values() if p["type"] == "title"), None
        )
        name = title_prop["title"][0]["plain_text"] if title_prop and title_prop["title"] else ""
        if name:
            exams.append({"name": name, "days_left": days_left})
    return sorted(exams, key=lambda x: x["days_left"])


# ── StudyLog ─────────────────────────────────────────

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


def _get_log_entry(status: str):
    results = notion.databases.query(
        database_id=LOG_DATABASE_ID,
        filter={"property": "状態", "select": {"equals": status}},
    )
    return results["results"][0] if results["results"] else None


def _get_current_draft():
    for status in ["記録中", "科目選択中"]:
        entry = _get_log_entry(status)
        if entry:
            return entry
    return None


def create_draft_log(energy: str):
    notion.pages.create(
        parent={"database_id": LOG_DATABASE_ID},
        properties={
            "日付":        {"title": [{"text": {"content": str(date.today())}}]},
            "記録日":      {"date": {"start": str(date.today())}},
            "頑張り度合い": {"select": {"name": ENERGY_TO_JP.get(energy, energy)}},
            "状態":        {"select": {"name": "記録中"}},
        },
    )


def add_subject_to_log(subject: str) -> list:
    entry = _get_current_draft()
    if not entry:
        return [subject]
    page_id = entry["id"]
    rt = entry["properties"]["科目記録"]["rich_text"]
    current = rt[0]["plain_text"] if rt else ""
    new_text = f"{current}、{subject}" if current else subject
    notion.pages.update(
        page_id=page_id,
        properties={
            "科目記録": {"rich_text": [{"text": {"content": new_text}}]},
            "状態":     {"select": {"name": "科目選択中"}},
        },
    )
    return [s for s in new_text.split("、") if s]


def complete_subject_selection():
    entry = _get_current_draft()
    if not entry:
        return
    notion.pages.update(
        page_id=entry["id"],
        properties={"状態": {"select": {"name": "時間待ち"}}},
    )


def finalize_log_no_study():
    entry = _get_current_draft()
    if not entry:
        return
    notion.pages.update(
        page_id=entry["id"],
        properties={"状態": {"select": {"name": "完了"}}},
    )


def update_log_time(time_text: str) -> bool:
    entry = _get_log_entry("時間待ち")
    if not entry:
        return False
    minutes = _parse_minutes(time_text)
    props = {
        "勉強時間": {"rich_text": [{"text": {"content": time_text}}]},
        "状態":     {"select": {"name": "進行度待ち"}},
    }
    if minutes > 0:
        props["勉強時間(分)"] = {"number": minutes}
    notion.pages.update(page_id=entry["id"], properties=props)
    return True


def save_morning_result(subject: str, action: str):
    prefix = "✅" if action == "complete" else "⏭"
    notion.pages.create(
        parent={"database_id": LOG_DATABASE_ID},
        properties={
            "日付":    {"title": [{"text": {"content": str(date.today())}}]},
            "記録日":  {"date": {"start": str(date.today())}},
            "科目記録": {"rich_text": [{"text": {"content": f"{prefix} {subject}"}}]},
            "状態":    {"select": {"name": "完了"}},
        },
    )


def finalize_log(progress: str):
    entry = _get_log_entry("進行度待ち")
    if not entry:
        return None, None, None
    props = entry["properties"]
    energy_jp   = props["頑張り度合い"]["select"]["name"] if props["頑張り度合い"]["select"] else ""
    time_text   = props["勉強時間"]["rich_text"][0]["plain_text"] if props["勉強時間"]["rich_text"] else ""
    subjects    = props["科目記録"]["rich_text"][0]["plain_text"] if props["科目記録"]["rich_text"] else ""
    notion.pages.update(
        page_id=entry["id"],
        properties={
            "進行度": {"select": {"name": PROGRESS_TO_JP.get(progress, progress)}},
            "状態":   {"select": {"name": "完了"}},
        },
    )
    return energy_jp, time_text, subjects
