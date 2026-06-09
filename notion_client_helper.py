import os
from datetime import datetime, date
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
LOG_DATABASE_ID = os.environ.get("NOTION_LOG_DATABASE_ID", "")

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


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
        })

    return subjects, today_label


# ── StudyLog ─────────────────────────────────────────

ENERGY_TO_JP = {"great": "頑張れた！", "ok": "まあまあ", "bad": "イマイチ"}
PROGRESS_TO_JP = {
    "start": "始めた", "little": "少し進んだ",
    "half": "半分くらい", "almost": "ほぼ完了", "done": "完了！",
}


def create_draft_log(energy: str):
    notion.pages.create(
        parent={"database_id": LOG_DATABASE_ID},
        properties={
            "日付":        {"title": [{"text": {"content": str(date.today())}}]},
            "頑張り度合い": {"select": {"name": ENERGY_TO_JP.get(energy, energy)}},
            "状態":        {"select": {"name": "記録中"}},
        },
    )


def update_log_time(time_text: str) -> bool:
    results = notion.databases.query(
        database_id=LOG_DATABASE_ID,
        filter={"property": "状態", "select": {"equals": "記録中"}},
    )
    if not results["results"]:
        return False
    page_id = results["results"][0]["id"]
    notion.pages.update(
        page_id=page_id,
        properties={
            "勉強時間": {"rich_text": [{"text": {"content": time_text}}]},
            "状態":     {"select": {"name": "時間記録済み"}},
        },
    )
    return True


def finalize_log(progress: str):
    results = notion.databases.query(
        database_id=LOG_DATABASE_ID,
        filter={"property": "状態", "select": {"equals": "時間記録済み"}},
    )
    if not results["results"]:
        return None, None
    page = results["results"][0]
    page_id = page["id"]
    props = page["properties"]
    energy_jp = props["頑張り度合い"]["select"]["name"] if props["頑張り度合い"]["select"] else ""
    time_text = props["勉強時間"]["rich_text"][0]["plain_text"] if props["勉強時間"]["rich_text"] else ""
    notion.pages.update(
        page_id=page_id,
        properties={
            "進行度": {"select": {"name": PROGRESS_TO_JP.get(progress, progress)}},
            "状態":   {"select": {"name": "完了"}},
        },
    )
    return energy_jp, time_text
