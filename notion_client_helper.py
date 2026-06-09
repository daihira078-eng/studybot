import os
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]


def _detect_props(db_props):
    """Notionのプロパティ定義から各列の名前を型で推定する"""
    title_key = None
    checkbox_key = None
    multi_select_key = None
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
        "multi_select_options": multi_select_options if multi_select_key else [],
        "selects": select_keys,
        "rich_text": rich_text_key,
    }


WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def get_today_subjects():
    db = notion.databases.retrieve(database_id=DATABASE_ID)
    keys = _detect_props(db["properties"])

    weekday_idx = datetime.now().weekday()
    today_label = WEEKDAY_JP[weekday_idx]

    print("today:", today_label, "| keys:", keys)

    all_pages = notion.databases.query(database_id=DATABASE_ID)

    subjects = []
    for page in all_pages["results"]:
        props = page["properties"]

        # Activeチェック
        if keys["checkbox"]:
            if not props[keys["checkbox"]]["checkbox"]:
                continue

        # 曜日チェック
        if keys["multi_select"]:
            options_today = [o["name"] for o in props[keys["multi_select"]]["multi_select"]]
            if today_label not in options_today:
                continue

        # 各プロパティ取得
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

        # selects順は['難易度', 'カテゴリ']なのでインデックスに注意
        subjects.append({
            "name": name,
            "category": selects[1] if len(selects) > 1 else "",
            "difficulty": selects[0] if len(selects) > 0 else "",
            "memo": memo,
        })

    return subjects, today_label
